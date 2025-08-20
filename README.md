# VidCompress

This Python script transcodes and remuxes video files within a specified folder to a standardized format. It's designed to optimize your media library for storage and playback compatibility, offering flexibility in video codecs and container formats. This script is ideal for use with automation tools like `cron` to automatically process media folders.

## Features

- **Flexible Transcoding**: Supports transcoding to H.265 (HEVC), H.264, or VP9 video codecs.
- **Container Choice**: Output files can be in MKV or MP4 containers.
- **Automated Remuxing**: If video and audio codecs already match the target, the script will perform a fast remux (container change only) instead of a full re-encode.
- **Standardized Audio**: Always converts audio to AAC (2-channel).
- **Hardware Acceleration**: Automatically utilizes Apple's VideoToolbox for HEVC/H.264 encoding on macOS, if available, for faster processing.
- **Skipping**: Skips files that are already in the target format and container.
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
    cd ./VidCompress
    ```

2.  **Run the script**:
    Provide the absolute path to the folder containing your video files as an argument. You can customize the video codec and container, and also use the `--keep-original` flag to prevent the deletion of original files after successful processing.

    ```bash
    python vidcompress.py /path/to/your/video/folder \
        [--video-codec {h.265,h.264,vp9}] \
        [--container {mkv,mp4}] \
        [--keep-original]
    ```
    
    **Default Options**: If no `--video-codec` or `--container` is specified, the script defaults to `h.265` video codec and `mp4` container.

    Replace `/path/to/your/video/folder` with the actual path to the directory you want to process.

    **Examples**:
    ```bash
    # Process with default H.265 video and MP4 container
    python vidcompress.py "/Users/YourUser/Videos/Movies to Process"

    # Process with H.264 video and MKV container, keeping original files
    python vidcompress.py "/Users/YourUser/Videos/Movies to Process" --video-codec h.264 --container mkv --keep-original

    # Process with VP9 video and WebM container (note: WebM is a subset of MKV for VP9)
    python vidcompress.py "/Users/YourUser/Videos/Movies to Process" --video-codec vp9 --container mkv
    ```

## How it Works

The script performs the following steps:

1.  **Checks for VideoToolbox**: Determines if macOS hardware acceleration for HEVC/H.264 is available.
2.  **Scans Folder**: Iterates through all files in the specified folder and its subfolders.
3.  **Identifies Video Files**: Processes files with common video extensions, including `.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, and `.m2ts`.
4.  **Analyzes Media Info**: Uses `ffprobe` to get detailed information about each video file (container, video codec, audio codec, channels).
5.  **Conditional Processing**: 
    - If a file is already in the target video codec, audio codec, and container, it's skipped.
    - If video and audio codecs match the target but the container is different, it performs a fast **remux** (container change only).
    - Otherwise, it performs a full **transcode** to the specified video codec (using hardware acceleration if available) and AAC 2-channel audio.
6.  **Cleans Up**: Upon successful processing (transcoding or remuxing), the original video file is deleted by default. You can prevent this by using the `--keep-original` flag.

## License

This project is open-source and available under the [MIT License](LICENSE).
