# Project Diary: Media Press

**Creation Date:** 2025-07-24  
**Version:** 1.0 (Release Candidate)  
**Author:** Ruslan Lypovskyi (techmavericklab@gmail.com)  
**Main Technologies:** `Python`, `Flask`, `PyWebView`, `Pillow`, `FFmpeg`, `sips`, `PyInstaller`

---

## 1. Project Goals Description

The initial goal was to modernize an existing Python script (`convert.py`) for batch media file processing. The script already performed basic tasks but had several shortcomings: hardcoded paths, sequential processing, lack of flexibility, and an unfriendly interface.

During development, the goal evolved into a much more ambitious one:  
**To create a full-fledged, standalone desktop application (`.app`) for macOS with a graphical user interface (GUI) for batch processing of images and videos.**

**Key objectives of the final product:**

- **Intuitive Interface:** Enable users without programming knowledge to easily select files and configure processing parameters through a user-friendly app window.
- **Flexibility:** Provide full control over output formats, sizes (including custom), compression quality, and Retina (`@2x`) versions creation.
- **Reliability:** Ensure stable handling of various formats, including Apple-specific ones (`.heic`, `.mov`), and correctly process corrupted files without interrupting the workflow.
- **Performance:** Utilize parallel processing to maximize speed on multi-core processors.
- **Distributability:** Package the entire project into a single `.app` file that can be easily shared with others without requiring manual installation of Python, `ffmpeg`, or other dependencies.

---

## 2. Initial Implementation Plan

1. **Analysis and Refactoring:** Review the existing script, move settings to a config file (`config.yml`), and improve project structure.
2. **GUI Creation:** Develop a basic graphical user interface for user interaction, using `Flask` for the backend and web technologies for the frontend.
3. **Logic Integration:** Migrate and adapt image processing (`Pillow`) and video processing (`ffmpeg`) logic into the new application.
4. **Adding Advanced Features:** Implement parallel processing, dynamic log updates, and parameter selection via the interface.
5. **Packaging:** Package the project into a standalone `.app` file using `PyInstaller`.

---

## 3. Completed Stages Description

### Stage 1: Analysis and Refactoring

- **Actions:** Analyzed the `convert.py` script. Created a new project structure `media_press` with clear separation of `source`, `output`, and `templates`. Developed `config.yml` structure.
- **Challenges:** None. Stage completed smoothly.

### Stage 2: GUI Creation

- **Actions:** Initialized a `Flask` app. Created a basic `index.html`. Integrated the `pywebview` library to run the `Flask` app inside a native desktop window.
- **Challenges:**
  - **Issue:** Failed attempt to install `pywebview` due to outdated Python version (3.8) that did not support `pyobjc-core` dependency.
  - **Solution:** Upgraded system `python3` to version **3.11** using `MacPorts`. Recreated the virtual environment (`venv`) based on the new version, enabling successful installation of all dependencies.

### Stage 3: Logic Integration

- **Actions:** Moved image and video processing logic into functions `process_image` and `process_video`. Implemented parallel processing using `ThreadPoolExecutor`.
- **Challenges:**
  - **Issue:** Files with non-Latin characters and spaces in filenames (e.g., `Тестовий запис.m4a`) failed to process.
  - **Solution:** Completely abandoned `secure_filename` in favor of keeping original file names.
  - **Issue:** `.webm` video processing failed due to incompatible audio codec `aac`.
  - **Solution:** Added logic to automatically select the correct audio codec (`libopus` for `.webm`, `aac` for `.mp4`).
  - **Issue:** Processing 4K videos caused `Cannot allocate memory` errors during poster creation.
  - **Solution:** Added the `-vf "scale=640:-1"` filter to the `ffmpeg` command to downscale frames safely before saving.

### Stage 4: Feature Expansion

- **Actions:** Enhanced the interface with checkboxes for size selection (`full_size`, `desktop`, etc.), a Retina toggle, dropdowns for format and quality selection, and a "Clear All" button.
- **Challenges:**
  - **Issue:** After adding flexible settings, an `Internal Server Error` occurred due to incorrect video parameter processing logic in `press.py`.
  - **Solution:** Completely rewrote the logic for retrieving and applying settings in the `process_video` and `start_processing_job` functions.

### Stage 5: Packaging and System Issue Resolution

- **Actions:** Created a `.spec` file for `PyInstaller`. Made multiple attempts to build the `.app` file.
- **Challenges:** **This was the most difficult stage.**
  - **Issue:** The packaged `.app` could not locate `ffmpeg` and `sips`, resulting in `No such file or directory` errors.
  - **Unsuccessful attempts:**
    1. Hardcoding paths in `press.py`.
    2. Copying `ffmpeg` into a local `bin` folder in the project.
    3. Removing macOS quarantine attribute with `xattr`.
  - **Final solution:** Discovered that `Automator` runs scripts in a highly isolated environment. The only reliable approach was to use the **"Run AppleScript"** action in Automator to instruct the **Terminal** app to execute our script. This guarantees the script always runs in a full user environment with the correct `PATH`.
  - **Issue:** Unreliable `.heic` conversion using `ffmpeg`.
  - **Solution:** Completely abandoned `ffmpeg` for this task. Instead, native macOS utility **`sips`** was used, ensuring 100% compatibility with Apple formats.
  - **Issue:** Closing the app window interrupted background processing, causing `Broken Pipe` errors.
  - **Solution:** Added graceful shutdown logic in `press.py` via `executor.shutdown(wait=True)`, forcing the program to wait for all tasks to complete before exiting.

---

## 4. Current Status

**The project is fully completed and meets all specified goals.**

- **[✓]** Desktop application `Media Press.app` created.
- **[✓]** Flexible GUI implemented with full control over processing parameters.
- **[✓]** Supports processing of images (JPG, PNG, **HEIC**), video, and audio.
- **[✓]** Stable operation ensured by reliable launch mechanism via AppleScript.
- **[✓]** Application is ready for packaging and distribution to other macOS users.

---

## 5. Changes in Logic and Plan

1. **GUI: `Flask` + `pywebview`:** The initial plan was vague regarding the GUI. The decision to use `pywebview` to "wrap" the web interface into a window proved highly effective.
2. **HEIC Processing: from `pillow-heif` to `sips`:** The plan to use the `pillow-heif` library failed due to insurmountable compilation issues in the user environment. An interim attempt to use `ffmpeg` was unreliable. **The current approach** is to rely on the native `sips` utility, which is the most stable solution on macOS.
3. **App Launch: from shell script to AppleScript:** The plan to package the app to run with a simple shell script was unfeasible due to Automator’s environment isolation. **The current approach** is to use AppleScript to run `press.py` in a full Terminal window, the only guaranteed method to access system tools.

**Conclusions:** The development process was iterative, requiring deep analysis and adaptation to macOS-specific challenges. The final architecture reflects not only the initial plan but also numerous experiments and solutions to unforeseen difficulties.
