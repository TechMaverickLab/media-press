# Media Press 🖼️✨🚀

[![Latest Release](https://img.shields.io/github/v/release/TechMaverickLab/media-press?label=Download&color=brightgreen)](https://github.com/TechMaverickLab/media-press/releases/latest)

**Media Press** is a powerful yet intuitive desktop application for macOS designed for batch processing of images and videos. It automates the routine tasks of preparing media files for the web, saving you valuable time and effort.

Easily convert, resize, and optimize dozens of files in just a few clicks!

![Media Press Screenshot](https://raw.githubusercontent.com/TechMaverickLab/media-press/master/assets/screenshot.png) <!-- Replace with the actual URL to your screenshot -->

## 🌟 Key Features

*   **Graphical User Interface:** No command line needed! All operations are performed in a user-friendly application window.
*   **Batch Processing:** Upload and process multiple files at once.
*   **Flexible Settings:**
    *   **Size Selection:** Generate versions for `desktop`, `tablet`, `mobile`, or specify your own custom dimensions.
    *   **Retina-Ready:** Automatically create `@2x` versions for high-density displays.
    *   **Quality Control:** Choose between standard and maximum compression for both images and videos.
    *   **Format Selection:** Convert images to `WebP`, `JPG`, `PNG` and videos to `MP4` or `WebM`.
*   **Wide Format Support:**
    *   **Images:** JPG, PNG, **HEIC**, WebP, TIFF.
    *   **Video & Audio:** MP4, MOV, WebM, M4A, and many more.
*   **Intelligent Processing:** Automatic video poster generation and proper handling of audio-only files.
*   **Convenient Results Viewer:** An integrated gallery allows you to preview processed files and open their location in Finder with a single click.

## 🛠️ Tech Stack

*   **Language:** Python 3.11+
*   **GUI Framework:** PyWebView (a lightweight wrapper around a Flask web server)
*   **Backend:** Flask
*   **Image Processing:** Pillow, `sips` (native macOS utility)
*   **Video/Audio Processing:** FFmpeg

## 🚀 Installation & Usage

**Media Press** is designed for maximum simplicity. No complex setup is required!

### For End-Users

1.  **Download:** Grab the latest release (`Media_Press_Installer.dmg`) from the [Releases page](https://github.com/TechMaverickLab/media-press/releases).
2.  **Mount:** Open the downloaded `.dmg` file.
3.  **Install:** Drag the `Media Press.app` icon into your "Applications" folder.
4.  **First Launch:**
    *   **Right-click** on the `Media Press.app` icon.
    *   Select **"Open"** from the context menu.
    *   In the dialog box that appears, click **"Open"** again.
    *   You only need to do this once! After that, the app will launch with a normal double-click.

### For Developers (Running from source)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/TechMaverickLab/media-press.git
    cd media-press
    ```
2.  **Prerequisites:** Make sure you have the following installed:
    *   Python 3.11+
    *   `ffmpeg` and `pkg-config` (recommended to install via [MacPorts](https://www.macports.org/) or [Homebrew](https://brew.sh/)).
    ```bash
    # Example using Homebrew
    brew install ffmpeg pkg-config
    ```

3.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Install dependencies:**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

5.  **Run the application:**
    ```bash
    python3 press.py
    ```

## ⚙️ Configuration

All main processing parameters (default sizes, compression quality) are located in the `config.yml` file. You can edit this file to customize the application's behavior to suit your needs.

## 📦 Building the `.app` Bundle

The project uses `PyInstaller` to create a standalone macOS application.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```

2.  **Prepare the icon:** Place your `icon.icns` file (1024x1024 recommended) in the project's root directory.

3.  **Run the build command:**
    ```bash
    pyinstaller "Media Press.spec"
    ```

4.  The final, distributable `Media Press.app` will be located in the `dist/` directory.

## 📄 License

This project is distributed under the MIT License. See the `LICENSE` file for more information.
