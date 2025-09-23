# VidCompress

VidCompress scans a folder and standardizes your video files for reliable playback and smaller size. It transcodes when needed, remuxes when possible, picks the preferred audio track, and can send a completion notification.

## What You Get

- Flexible video codecs: H.265 (HEVC), H.264, or VP9
- Output containers: MP4 or MKV
- Smart remux: copy streams when codecs already match
- Standardized audio: AAC stereo (2 channels)
- MP4 faststart: web‑optimized MP4 when targeting MP4
- macOS hardware acceleration: uses VideoToolbox if available

## Requirements

- Python 3.11+ recommended
- FFmpeg and FFprobe available in `PATH`
- Optional for notifications: `curl` and an ntfy server/topic

Install FFmpeg/FFprobe:
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt update && sudo apt install -y ffmpeg`
- Windows (PowerShell admin): `choco install ffmpeg -y` (or download from ffmpeg.org and add `bin` to `PATH`)

## Install

Clone and (optionally) use a virtual environment. The script uses only the Python standard library.

```bash
git clone https://github.com/your-user/VidCompress.git
cd VidCompress

# Optional but recommended
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -V  # should be 3.11+
```

## Quick Start

Run against a folder containing videos:

```bash
python vidcompress.py "/path/to/your/video/folder"
```

Defaults:
- `--video-codec`: `h.265`
- `--container`: `mp4`
- Original files are deleted after a successful process unless `--keep-original` is set
- Notifications: by default sends to `http://localhost:1030/vidcompress` if reachable

## Command Line Options

```bash
python vidcompress.py FOLDER \
  [--video-codec {h.265,h.264,vp9}] \
  [--container {mkv,mp4}] \
  [--keep-original] \
  [--notify-url URL] \
  [--notify-title TITLE] \
  [--debug]
```

- `FOLDER`: Path to the folder to process (recurses into subfolders).
- `--video-codec`: Target video codec. Chooses VideoToolbox on macOS when available.
- `--container`: Target container (`mp4` or `mkv`). When `mp4` and codecs already match, VidCompress ensures MP4 is faststart‑optimized.
- `--keep-original`: Keep the original file after a successful transcode/remux.
- `--notify-url`: ntfy endpoint, e.g. `http://localhost:1030/vidcompress`. To disable notifications, pass an empty value: `--notify-url ''`.
- `--notify-title`: Notification title (default: `VidCompress`).
- `--debug`: Verbose debug output to stdout.

Environment variables (optional):
- `NTFY_URL`: Default notification URL if `--notify-url` is not provided.
- `NTFY_TITLE`: Default notification title.

## Examples

Transcode to H.265 in MP4, deleting originals (default):
```bash
python vidcompress.py "/media/Movies"
```

Use H.264 in MKV and keep originals:
```bash
python vidcompress.py "/media/Movies" --video-codec h.264 --container mkv --keep-original
```

Use VP9 in MKV and send a notification to ntfy:
```bash
python vidcompress.py "/media/Movies" --video-codec vp9 --container mkv \
  --notify-url http://ntfy.local:1030/vidcompress --notify-title "Library Compress"
```

Disable notifications explicitly:
```bash
python vidcompress.py "/media/Movies" --notify-url ''
```

## Notes for Users

- Audio track selection prefers Japanese, then English, then Vietnamese; otherwise the first audio track.
- If codecs already match but only the container differs, VidCompress performs a fast remux (no quality loss).
- On macOS, if FFmpeg exposes `h264_videotoolbox`/`hevc_videotoolbox`, hardware encoding is used automatically.
- Targeting MP4 ensures faststart optimization so playback can begin sooner when streaming.

## Troubleshooting

- FFmpeg/FFprobe not found: Ensure they are installed and available in your `PATH`.
- Permission errors moving files: Run from a folder where you have write access.
- `curl` not found (for notifications): Install `curl` or disable notifications with `--notify-url ''`.

## License

This project is open-source and available under the [MIT License](LICENSE).
