# VidCompress

This Python script transcodes video files within a specified folder to a standardized HEVC/AAC (2-channel) format within an MKV container. It's designed to optimize your media library for storage and playback compatibility. This script is ideal for use with automation tools like `cron` to automatically process media folders.

## Features

- **Automated Transcoding**: Converts various video formats to HEVC video and AAC (2-channel) audio in an MKV container.
- **Hardware Acceleration**: Automatically utilizes Apple's VideoToolbox for HEVC encoding on macOS, if available, for faster transcoding.
- **Skipping**: Skips files that are already in the target HEVC/AAC MKV format.
- **Supported Formats**: Processes files with common video extensions, including `.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, and `.m2ts`.

## Prerequisites

Before running the script, ensure you have the following installed and accessible in your system's PATH:

- **Python 3.x**: Download from [python.org](https://www.python.org/downloads/).
- **FFmpeg and FFprobe**: These command-line tools are essential for media processing. 
    - **macOS**: Install via Homebrew: `brew install ffmpeg`
    - **Linux (Debian/Ubuntu)**: Install via apt: `sudo apt update && sudo apt install ffmpeg`
    - **Windows**: Download static builds from the [official FFmpeg website](https://ffmpeg.org/download.html) and add the `bin` directory to your system's PATH environment variable.

## Usage

1.  **Navigate to the script directory**:
    ```bash
    cd /Volumes/KINGSTON/Workspace/transcode-app
    ```

2.  **Run the script**:
    Provide the absolute path to the folder containing your video files as an argument. You can also use the `--keep-original` flag to prevent the deletion of original files after successful transcoding.
    ```bash
    python vidcompress.py /path/to/your/video/folder [--keep-original]
    ```
    Replace `/path/to/your/video/folder` with the actual path to the directory you want to process.

    **Examples:**
    ```bash
    python vidcompress.py "/Users/YourUser/Videos/Movies to Transcode"
    python vidcompress.py "/Users/YourUser/Videos/Movies to Transcode" --keep-original
    ```

## How it Works

The script performs the following steps:

1.  **Checks for VideoToolbox**: Determines if macOS hardware acceleration for HEVC is available.
2.  **Scans Folder**: Iterates through all files in the specified folder and its subfolders.
3.  **Identifies Video Files**: Processes files with common video extensions, including `.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, and `.m2ts`.
4.  **Analyzes Media Info**: Uses `ffprobe` to get detailed information about each video file (container, video codec, audio codec, channels).
5.  **Conditional Transcoding**: 
    - If a file is already in MKV container with HEVC video and AAC 2-channel audio, it's skipped.
    - Otherwise, it transcodes the file using `ffmpeg`.
        - On macOS, `hevc_videotoolbox` is used if available; otherwise, `libx265` is used.
        - For audio, `aac` codec with 2 channels is always used.
6.  **Cleans Up**: Upon successful transcoding, the original video file is deleted. You can avoid this by '--keep-origin'.

## License

This project is open-source and available under the [MIT License](LICENSE).