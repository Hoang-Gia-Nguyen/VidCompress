# Simple VidCompress

An automated media transcoding pipeline that intelligently converts videos to HEVC (H.265) with hardware acceleration support. It scans directories, extracts subtitles, and manages original files based on your backup preferences.

## Features

- **Intelligent Transcoding:** Automatically detects if a file needs transcoding (Target: HEVC/AAC).
- **Hardware Acceleration:** Supports VideoToolbox (macOS), NVENC (NVIDIA), QSV (Intel), and AMF (AMD) with automatic fallback to CPU (libx265).
- **Subtitle Extraction:** Automatically extracts all subtitle tracks to `.srt` files.
- **Job Management:** Uses an SQLite-backed repository to track progress, handle errors, and ensure idempotency.
- **Configurable Backups:** Archive, delete, or keep original files after successful transcoding.
- **Robust Configuration:** Powered by Pydantic for validation and environment management.
- **Centralized Logging:** Detailed logs for monitoring and debugging.

## Prerequisites

- Python 3.12+
- [FFmpeg](https://ffmpeg.org/) and `ffprobe` installed in your PATH.
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip`.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd transcode-app
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure the application:
   ```bash
   cp config.example.json config.json
   # Edit config.json with your settings
   ```

## Configuration

The `config.json` file supports the following fields:

- `MEDIA_DIRS`: List of directories to scan for media.
- `BACKUP_DIR`: Directory where original files are moved if `BACKUP_STRATEGY` is `ARCHIVE`.
- `EXTRACT_SUBTITLE`: Boolean to enable/disable subtitle extraction.
- `BACKUP_STRATEGY`: `ARCHIVE`, `DELETE`, or `DO_NOTHING`.
- `JOB_REPO_FILE`: Path to the SQLite database file (default: `jobs.db`).
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`).

## Usage

Run the main pipeline:
```bash
uv run python main.py
```

## Testing

Run unit and integration tests:
```bash
uv run pytest
```

## Architecture

- `app/pipeline.py`: Orchestrates the Scan -> Process -> Clean workflow.
- `app/transcoder.py`: Handles FFmpeg logic and hardware acceleration detection.
- `app/jobrepo.py`: Manages job state persistence via SQLite.
- `app/media_scanner.py`: Recursively discovers media files.
- `app/config.py`: Pydantic models for configuration validation.
- `app/logger.py`: Centralized logging setup.

## License

MIT
