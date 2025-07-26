import os
import yaml
import shutil
import traceback
import subprocess
import uuid
import sys
import threading
import contextlib
import time
import signal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
from typing import Optional

import webview

from flask import Flask, render_template, request, jsonify, url_for, send_from_directory, make_response

from PIL import Image, UnidentifiedImageError


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS')
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


APP_DATA_FOLDER_NAME = "Media Press Files"
SETTINGS_FILE = Path.home() / '.media_press_settings.json'
SOURCE_DIR = None
OUTPUT_DIR = None


CONFIG_PATH = resource_path("config.yml")
STATIC_DIR = resource_path("static")
FFMPEG_CMD = resource_path("bin/ffmpeg")
FFPROBE_CMD = resource_path("bin/ffprobe")
SIPS_CMD = "sips"
SERVER_PORT = 5000


SUPPORTED_IMAGE_FORMATS = ['.webp', '.jpg', '.jpeg', '.png', '.tiff', '.heic']
SUPPORTED_AV_FORMATS = ['.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v', '.m4a', '.mp3', '.aac', '.wav', '.flac']
FORMAT_MAPPING = {'webp': 'WEBP', 'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG'}
VIDEO_CODECS = {'mp4': 'libx264', 'webm': 'libvpx-vp9'}
AUDIO_CODECS = {'mp3': 'libmp3lame', 'aac': 'aac', 'opus': 'libopus'}


app = Flask(__name__, template_folder=resource_path('templates'))
app.config['SECRET_KEY'] = 'a-very-secret-key'
executor = ThreadPoolExecutor(max_workers=os.cpu_count() or 1)
config, processing_log, active_futures = {}, [], {}

def load_settings():
    global SOURCE_DIR, OUTPUT_DIR
    print(f"Checking the settings file: {SETTINGS_FILE}")
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            
            base_dir = Path(settings['base_directory'])
            work_dir = base_dir / APP_DATA_FOLDER_NAME
            
            if not work_dir.is_dir():
                print(f"Warning: Working folder '{work_dir}' not found. Reconfiguration required.")
                SETTINGS_FILE.unlink(missing_ok=True)
                return False

            app.config['WORK_DIR'] = work_dir
            app.config['SOURCE_DIR'] = work_dir / 'source'
            app.config['OUTPUT_DIR'] = work_dir / 'output'

            SOURCE_DIR = app.config['SOURCE_DIR']
            OUTPUT_DIR = app.config['OUTPUT_DIR']
            
            SOURCE_DIR.mkdir(exist_ok=True)
            OUTPUT_DIR.mkdir(exist_ok=True)
            
            print(f"✅ Settings successfully loaded. Working folder: {work_dir}")
            return True
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading settings: {e}. Deleting a corrupted file.")
            SETTINGS_FILE.unlink(missing_ok=True)
            return False
    
    print("Configuration file not found. Initial configuration required.")
    return False

def save_settings(base_directory_path):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump({'base_directory': str(base_directory_path)}, f, indent=4)
    print(f"Settings saved to file: {SETTINGS_FILE}")
    load_settings()

class Api:
    window: Optional[webview.Window]

    def __init__(self, window: Optional[webview.Window], is_configured_at_start: bool):
        self.window = window
        self._is_configured = is_configured_at_start

    def is_configured(self) -> bool:
        print(f"JS requested the configuration status. Returning: {self._is_configured}")
        return self._is_configured

    def select_work_directory(self):
        if self.window is None:
            print("Error: The window object was not bound to the API.")
            return None
        
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG, allow_multiple=False)
        if result and result[0]:
            base_dir = Path(result[0])
            save_settings(base_dir)
            self._is_configured = True
            return str(base_dir / APP_DATA_FOLDER_NAME)
        return None



    def get_work_directory(self) -> Optional[str]:
        return str(app.config.get('WORK_DIR')) if 'WORK_DIR' in app.config else None

    def show_in_finder(self, dirname: str):
        output_dir = app.config.get('OUTPUT_DIR')
        if not output_dir: return

        target_dir = (output_dir / dirname).resolve()
        if not target_dir.is_dir() or output_dir.resolve() not in target_dir.parents:
            return
        try:
            if sys.platform == "win32": subprocess.run(["explorer", str(target_dir)])
            elif sys.platform == "darwin": subprocess.run(["open", str(target_dir)])
            else: subprocess.run(["xdg-open", str(target_dir)])
        except FileNotFoundError:
            print("Could not open file manager.")

def log_message(message, level='info'):
    if level == 'info': print(message); processing_log.append(message)
    elif level == 'debug': print(message)

def run_command(command, log_prefix=""):
    try:
        if command[0] == FFMPEG_CMD: command = command[:1] + ['-loglevel', 'error'] + command[1:]
        process = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        log_message(f"{log_prefix} ✓ Completed")
        log_message(f"[DEBUG] Command: {' '.join(command)}\nOutput:\n{process.stderr.strip()}", level='debug')
        return process.stdout
    except FileNotFoundError:
        error_msg = f"🚨 CRITICAL ERROR: Not found `{command[0]}`."; log_message(error_msg); raise
    except subprocess.CalledProcessError as e:
        error_message = f"{log_prefix} 🚨 ERROR: {e.stderr.strip().splitlines()[-1] if e.stderr else 'Unknown error'}"
        log_message(error_message); log_message(f"[DEBUG_ERROR] Command: {' '.join(command)}\nFull Error:\n{e.stderr}", level='debug'); raise

@contextlib.contextmanager
def prepare_image_path(original_path):
    if original_path.suffix.lower() == '.heic' and sys.platform == "darwin":
        temp_png_path = original_path.with_suffix('.temp.png')
        log_message(f"  > Conversion HEIC -> PNG (via sips): {original_path.name}")
        try:
            command = [SIPS_CMD, '-s', 'format', 'png', str(original_path), '--out', str(temp_png_path)]
            run_command(command, "    "); yield temp_png_path
        finally:
            if temp_png_path.exists(): temp_png_path.unlink()
    else: yield original_path

def has_video_stream(file_path):
    cmd = [FFPROBE_CMD, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "json", str(file_path)]
    try: output = run_command(cmd, "  🕵️ Checking the video stream:"); return "video" in output
    except Exception: return False
    
def process_audio_only(file_path, settings):
    output_dir = app.config.get('OUTPUT_DIR')
    try:
        target_format, base_name = "mp3", file_path.stem
        log_message(f"🎵 Audio processing: {file_path.name}")
        file_output_folder = output_dir / base_name; file_output_folder.mkdir(exist_ok=True)
        cmd = [FFMPEG_CMD, "-i", str(file_path), "-c:a", AUDIO_CODECS[target_format], "-q:a", "2", str(file_output_folder / f"{base_name}.{target_format}"), "-y"]
        run_command(cmd, f"  ✓ Conversion to {target_format}:")
        log_message(f"✅ Audio {file_path.name} completed.")
    except Exception as e: log_message(f"🚨 Audio processing error {file_path.name}: {e}"); log_message(traceback.format_exc(), level='debug')

def start_processing_job(file_path, user_settings):
    ext = file_path.suffix.lower()
    if ext in SUPPORTED_IMAGE_FORMATS:
        process_image(file_path, config.get('image_profiles', {}).get('default', {}), user_settings)
    elif ext in SUPPORTED_AV_FORMATS:
        if has_video_stream(file_path):
            video_profile = config.get('video_profiles', {}).get('default', {})
            process_video(file_path, video_profile, user_settings)
        else:
            process_audio_only(file_path, user_settings)
    else:
        log_message(f"🤔 Skipping an unsupported file: {file_path.name}")


def process_image(file_path, profile, settings):
    output_dir = app.config.get('OUTPUT_DIR')
    if not output_dir:
        log_message("🚨 Critical ERROR: Working folder for results not set.")
        return
        
    try:
        target_format, compression_mode = settings.get('image_format', 'webp'), settings.get('compression_mode', 'standard')
        
        selected_sizes_keys = settings.get('sizes_to_process', [])
        
        sizes_to_process = {key: val for key, val in profile.get('sizes', {}).items() if key in selected_sizes_keys}

        custom_sizes = get_custom_sizes(settings.get('custom_sizes'))
        
        sizes_to_process.update(custom_sizes)
        
        log_message(f"  > Selected dimensions for processing: {list(sizes_to_process.keys())}")

        densities = [1, 2] if settings.get('include_retina') else [1]
        include_full_size = 'full_size' in selected_sizes_keys

        base_name, file_output_folder = file_path.stem, output_dir / file_path.stem
        
        log_message(f"🖼️ Image processing: {file_path.name}")
        with prepare_image_path(file_path) as image_to_process:
            try: img = Image.open(image_to_process).convert("RGBA" if target_format == "png" else "RGB")
            except UnidentifiedImageError: log_message(f"🚨 Error: Unable to recognize '{file_path.name}'."); return
            
            file_output_folder.mkdir(exist_ok=True)
            std_quality = config.get('compression_modes', {}).get('image', {}).get('standard', {}).get('quality', 85)
            
            if sizes_to_process:
                for size_label, base_width in sizes_to_process.items():
                    for density in densities:
                        new_width, new_height = base_width * density, int(img.height * (base_width * density / img.width))
                        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        new_file_name, save_params = f"{base_name}_{size_label}@{density}x.{target_format}", {'quality': std_quality}
                        if target_format == 'png': save_params = {'optimize': True}
                        resized_img.save(file_output_folder / new_file_name, FORMAT_MAPPING[target_format], **save_params)
                log_message("  ✓ Resized versions created")
            
            if include_full_size:
                full_size_name, save_params = f"{base_name}_full_size.{target_format}", {'quality': std_quality}
                if target_format == 'png': save_params = {'optimize': True}
                img.save(file_output_folder / full_size_name, FORMAT_MAPPING[target_format], **save_params)
                log_message(f"  ✓ Created: {full_size_name}")
            
            if compression_mode == 'max_compression':
                comp_quality = config.get('compression_modes', {}).get('image', {}).get('max_compression', {}).get('quality', 75)
                log_message(f"  ↳ Creating compressed versions (quality: {comp_quality})")
                if sizes_to_process:
                    for size_label, base_width in sizes_to_process.items():
                        for density in densities:
                            new_width, new_height = base_width * density, int(img.height * (base_width * density / img.width))
                            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            comp_file_name, save_params = f"{base_name}_{size_label}@{density}x_compressed.{target_format}", {'quality': comp_quality}
                            if target_format == 'png': save_params = {'optimize': True}
                            resized_img.save(file_output_folder / comp_file_name, FORMAT_MAPPING[target_format], **save_params)
                if include_full_size:
                    full_size_comp_name, save_params = f"{base_name}_full_size_compressed.{target_format}", {'quality': comp_quality}
                    if target_format == 'png': save_params = {'optimize': True}
                    img.save(file_output_folder / full_size_comp_name, FORMAT_MAPPING[target_format], **save_params)
                log_message("    ✓ Compressed versions created")

        log_message(f"✅ Done: {file_path.name}")
    except subprocess.CalledProcessError: log_message(f"🚨 Error: Failed to convert'{file_path.name}'."); return
    except Exception as e: log_message(f"🚨 Unknown processing error {file_path.name}: {e}"); log_message(traceback.format_exc(), level='debug')

def process_video(file_path, profile, settings):
    output_dir = app.config.get('OUTPUT_DIR')
    if not output_dir:
        log_message(f"🚨 Critical ERROR: Working folder for results not set.")
        return
    
    try:
        target_format, compression_mode = settings.get('video_format', 'mp4'), settings.get('compression_mode', 'standard')
        
        selected_sizes_keys = settings.get('sizes_to_process', [])
        heights_map = profile.get('heights_map', {})
        heights_to_process = {key: val for key, val in heights_map.items() if key in selected_sizes_keys}
        custom_sizes = get_custom_sizes(settings.get('custom_sizes'))
        heights_to_process.update(custom_sizes)
        
        log_message(f"  > Selected video sizes: {list(heights_to_process.keys())}")

        include_full_size = 'full_size' in settings.get('sizes_to_process', [])
        
        base_name, file_output_folder = file_path.stem, output_dir / file_path.stem
        file_output_folder.mkdir(exist_ok=True)
        video_codec, audio_codec = VIDEO_CODECS.get(target_format, 'libx264'), 'libopus' if target_format == 'webm' else 'aac'
        log_message(f"🎬 Video processing: {file_path.name}")
        
        poster_cmd = [FFMPEG_CMD, "-i", str(file_path), "-ss", "00:00:01", "-vframes", "1", "-vf", "scale=640:-1", "-q:v", "2", str(file_output_folder / f"{base_name}_poster.webp"), "-y"]
        run_command(poster_cmd, "  ✓ Creating a poster:")
        
        std_comp = config.get('compression_modes', {}).get('video', {}).get('standard', {})
        std_crf, std_preset = std_comp.get('crf', 23), std_comp.get('preset', 'medium')
        log_message(f"  ↳ Creating standard versions (crf={std_crf}, preset={std_preset})")
        
        if heights_to_process:
            for size_label, height in heights_to_process.items():
                cmd = [FFMPEG_CMD, "-i", str(file_path), "-vf", f"scale=-2:{height}", "-c:v", video_codec, "-preset", std_preset, "-crf", str(std_crf), "-c:a", audio_codec, "-b:a", "128k", str(file_output_folder / f"{base_name}_{size_label}.{target_format}"), "-y"]
                run_command(cmd, f"    ✓ Version created {height}p")
        
        if include_full_size:
            cmd = [FFMPEG_CMD, "-i", str(file_path), "-c:v", video_codec, "-preset", std_preset, "-crf", str(std_crf), "-c:a", audio_codec, "-b:a", "192k", str(file_output_folder / f"{base_name}_full_size.{target_format}"), "-y"]
            run_command(cmd, f"    ✓ Version created full_size")
            
        if compression_mode == 'max_compression':
            max_comp = config.get('compression_modes', {}).get('video', {}).get('max_compression', {})
            max_crf, max_preset = max_comp.get('crf', 28), max_comp.get('preset', 'slow')
            log_message(f"  ↳ Creating compressed versions (crf={max_crf}, preset={max_preset})")
            
            if heights_to_process:
                for size_label, height in heights_to_process.items():
                    cmd = [FFMPEG_CMD, "-i", str(file_path), "-vf", f"scale=-2:{height}", "-c:v", video_codec, "-preset", max_preset, "-crf", str(max_crf), "-c:a", audio_codec, "-b:a", "128k", str(file_output_folder / f"{base_name}_{size_label}_compressed.{target_format}"), "-y"]
                    run_command(cmd, f"      ✓ Compressed version created {height}p")
            
            if include_full_size:
                cmd = [FFMPEG_CMD, "-i", str(file_path), "-c:v", video_codec, "-preset", max_preset, "-crf", str(max_crf), "-c:a", audio_codec, "-b:a", "192k", str(file_output_folder / f"{base_name}_full_size_compressed.{target_format}"), "-y"]
                run_command(cmd, f"      ✓ Compressed version created full_size")
                
        log_message(f"✅ Video {file_path.name} processed.")
    except Exception as e:
        log_message(f"🚨 Video processing error {file_path.name}: {e}")
        log_message(traceback.format_exc(), level='debug')
        
def get_custom_sizes(custom_sizes_str):
    if custom_sizes_str:
        try: return { f"custom_{s.strip()}px": int(s.strip()) for s in custom_sizes_str.split(',') if s.strip().isdigit()}
        except ValueError: log_message("🚨 Error: Invalid custom size format."); return {}
    return {}
        

@app.route('/')
def index():
    setup_needed_str = request.args.get('setup_needed', 'true')
    setup_needed_bool = setup_needed_str.lower() == 'true'
    
    return render_template('index.html', setup_needed=setup_needed_bool)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/check_files', methods=['POST'])
def check_files():
    _source_dir = app.config.get('SOURCE_DIR')
    _output_dir = app.config.get('OUTPUT_DIR')
    if not _source_dir or not _output_dir:
        return jsonify({"error": "Working folder not configured"}), 400
        
    files = request.files.getlist('files[]')
    existing_in_source = []
    existing_in_output = []
    
    for f in files:
        filename = f.filename
        if not filename:
            continue
        
        if (_source_dir / filename).exists():
            existing_in_source.append(filename)
        if (_output_dir / Path(filename).stem).exists():
            existing_in_output.append(filename)
            
    return jsonify({"existing_in_source": existing_in_source, "existing_in_output": existing_in_output})

@app.route('/upload', methods=['POST'])
def upload_files():
    _source_dir = app.config.get('SOURCE_DIR')
    if not _source_dir:
        return jsonify({"error": "Working folder not configured"}), 400
    
    user_settings = {
        'image_format': request.form.get('image_format', 'webp'),
        'video_format': request.form.get('video_format', 'mp4'),
        'compression_mode': request.form.get('compression_mode', 'standard'),
        'custom_sizes': request.form.get('custom_sizes', ''),
        'sizes_to_process': request.form.getlist('sizes_to_process'),
        'include_retina': request.form.get('include_retina') == 'true'
    }
    
    job_ids, files = [], request.files.getlist('files[]')
    
    for file in files:
        filename = file.filename
        if not filename:
            continue
            
        target_path = _source_dir / filename
        file.save(target_path)
        log_message(f"📥 Uploaded: {filename}")
        
        job_id = str(uuid.uuid4())
        future = executor.submit(start_processing_job, target_path, user_settings)
        job_ids.append(job_id)
        active_futures[job_id] = future
        
    return jsonify({"status": "success", "job_ids": job_ids})

@app.route('/processing_status')
def processing_status():
    completed_jobs = [job_id for job_id, future in active_futures.items() if future.done()]
    for job_id in completed_jobs:
        try: active_futures[job_id].result()
        except Exception as e: log_message(f"🚨 Task {job_id} ended with an error: {e}")
        del active_futures[job_id]
    return jsonify({"active_jobs": len(active_futures)})

@app.route('/status')
def status(): return jsonify({"log": processing_log})

@app.route('/clear_log', methods=['GET'])
def clear_log(): global processing_log; processing_log = ["--- New processing session ---"]; return jsonify({"status": "cleared"})

@app.route('/clear_all', methods=['POST'])
def clear_all_folders():
    _source_dir = app.config.get('SOURCE_DIR')
    _output_dir = app.config.get('OUTPUT_DIR')
    if not _source_dir or not _output_dir: return jsonify({"error": "Working folder not configured"}), 400
    
    try:
        log_message("🧹 Cleaning the source and output folders...")
        for dir_to_clear in [_source_dir, _output_dir]:
            if dir_to_clear.exists():
                for item in dir_to_clear.iterdir():
                    if item.is_dir(): shutil.rmtree(item)
                    else: item.unlink()
        log_message("✅ Folders successfully cleaned.")
        return jsonify({'status': 'success'})
    except Exception as e:
        log_message(f"🚨 Folders successfully cleaned: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_results')
def get_results():
    _output_dir = app.config.get('OUTPUT_DIR')
    if not _output_dir or not _output_dir.exists(): return jsonify({"results": []})
    
    results = []
    for item_dir in sorted(_output_dir.iterdir()):
        if item_dir.is_dir():
            files_in_dir = list(item_dir.glob('*'))
            if not files_in_dir: continue
            poster_url, is_audio = None, any(f.suffix.lower() in ['.mp3', '.aac'] for f in files_in_dir)
            if is_audio: poster_url = url_for('serve_static_file', filename='audio_icon.svg')
            else:
                poster_path = next((f for f in files_in_dir if 'poster' in f.name), None)
                if poster_path: poster_url = url_for('serve_output_file', filename=f"{item_dir.name}/{poster_path.name}")
                else:
                    first_img = next((f for f in files_in_dir if f.suffix.lower() in SUPPORTED_IMAGE_FORMATS), None)
                    if first_img: poster_url = url_for('serve_output_file', filename=f"{item_dir.name}/{first_img.name}")
            results.append({"name": item_dir.name, "poster": poster_url, "files": [{"name": f.name, "url": url_for('serve_output_file', filename=f"{item_dir.name}/{f.name}")} for f in sorted(files_in_dir)]})
    return jsonify({"results": sorted(results, key=lambda x: x['name'], reverse=True)})

@app.route('/static/<path:filename>')
def serve_static_file(filename): return send_from_directory(STATIC_DIR, filename)

@app.route('/output/<path:filename>')
def serve_output_file(filename):
    _output_dir = app.config.get('OUTPUT_DIR')
    return send_from_directory(_output_dir, filename) if _output_dir else ("", 404)


def run_app(): app.run(host='127.0.0.1', port=SERVER_PORT, debug=False, use_reloader=False)

def check_tools_availability():
    ffmpeg_ok = os.path.exists(FFMPEG_CMD) and os.access(FFMPEG_CMD, os.X_OK)
    ffprobe_ok = os.path.exists(FFPROBE_CMD) and os.access(FFPROBE_CMD, os.X_OK)
    if not ffmpeg_ok: print(f"🚨 Not found or no execution rights: {FFMPEG_CMD}")
    if not ffprobe_ok: print(f"🚨 Not found or no execution rights: {FFPROBE_CMD}")
    if sys.platform == "darwin":
        sips_ok = shutil.which(SIPS_CMD) is not None
        if not sips_ok: print(f"🚨 SIPS system utility not found.")
        return ffmpeg_ok and ffprobe_ok and sips_ok
    else:
        return ffmpeg_ok and ffprobe_ok
    
def free_up_port(port):
    print(f"🔬 Port check {port}...")
    try:
        if sys.platform == "darwin":
            result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
            pids = result.stdout.strip().split('\n')
            for pid_str in pids:
                if pid_str:
                    pid = int(pid_str); print(f"  > Port {port} busy with PID process: {pid}. Stopping..."); os.kill(pid, signal.SIGKILL); time.sleep(1); print(f"  > Процес {pid} зупинено.")
        print(f"✅ Port {port} is free.")
    except (FileNotFoundError, ValueError, PermissionError) as e: print(f"  > Failed to automatically release port: {e}.")

if __name__ == '__main__':
    is_configured_on_startup = load_settings()
    
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f: config = yaml.safe_load(f)
    except Exception as e: print(f"🚨 ERROR: Not found {CONFIG_PATH}: {e}")
    
    free_up_port(SERVER_PORT)
    

    print("🔬 Checking the availability of tools...")
    if not check_tools_availability():
        error_msg = "\n🚨 CRITICAL ERROR: FFmpeg or SIPS not found!"
        print(error_msg)
        html = f'<div style="padding: 2rem; font-family: sans-serif;"><h1>Configuration error</h1><pre>{error_msg}</pre></div>'

        webview.create_window('ERROR Media Press', html=html, width=800, height=300)
        webview.start()
        sys.exit(1)
    
    print("✅ All tools found. Launch Media Press...")
    
    flask_thread = threading.Thread(target=run_app)
    flask_thread.daemon = True
    flask_thread.start()

    initial_url = f'http://127.0.0.1:{SERVER_PORT}'
    print(f"Launching a window from a URL: {initial_url}")
    
    api = Api(None, is_configured_on_startup)
    
    window = webview.create_window(
        'Media Press', 
        initial_url, 
        width=1200, 
        height=800, 
        resizable=True, 
        js_api=api 
    )
    
    api.window = window

    webview.start()

    print("\n⏳ Window closed. Waiting for background tasks to complete...")
    executor.shutdown(wait=True)
    print("✅ All tasks completed. Media Press completed the work.")

