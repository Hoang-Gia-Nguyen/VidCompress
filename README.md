# VidCompress

VidCompress scans a folder and standardizes your video files for reliable playback and smaller size. It transcodes when needed, remuxes when possible, preserves all audio and subtitle tracks, and can send a completion notification.

## What You Get

- Flexible video codecs: H.265 (HEVC), H.264, or VP9
- Output containers: MP4 or MKV
- Smart remux: copy streams when codecs already match
- Multi-audio preservation: keeps all audio tracks from source file
- Multi-subtitle preservation: keeps all subtitle tracks from source file
- Intelligent bitrate selection: automatically optimized based on resolution (4K→12Mbps, 1080p→6Mbps, etc.)
- Encoding presets: fast/medium/slow for quality/speed trade-off
- MP4 faststart: web‑optimized MP4 when targeting MP4
- macOS hardware acceleration: uses VideoToolbox if available
- Hardware-accelerated decoding: faster processing on Apple Silicon

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
- `--bitrate`: automatic (based on resolution)
- `--preset`: `medium`
- Original files are **kept by default** unless `--delete-original` is set
- Notifications: by default sends to `http://localhost:1030/vidcompress` if reachable

## Command Line Options

```bash
python vidcompress.py FOLDER \
  [--video-codec {h.265,h.264,vp9}] \
  [--container {mkv,mp4}] \
  [--bitrate BITRATE] \
  [--preset {fast,medium,slow}] \
  [--max-workers NUM] \
  [--delete-original] \
  [--notify-url URL] \
  [--notify-title TITLE] \
  [--debug]
```

- `FOLDER`: Path to the folder to process (recurses into subfolders).
- `--video-codec`: Target video codec. Chooses VideoToolbox on macOS when available.
- `--container`: Target container (`mp4` or `mkv`). When `mp4` and codecs already match, VidCompress ensures MP4 is faststart‑optimized.
- `--bitrate`: Video bitrate in kbps (e.g., `6000`). Default: automatic based on resolution:
  - 4K (2160p+): 12000 kbps
  - 2K (1440p+): 8000 kbps
  - 1080p: 6000 kbps (recommended for imperceptible quality loss)
  - 720p: 4000 kbps
  - SD (<720p): 2500 kbps
- `--preset`: Encoding preset for software encoders. Only applies to software-based codecs (not VideoToolbox):
  - `fast`: Lower quality, faster encoding (~30-40% faster)
  - `medium`: Balanced quality and speed (default)
  - `slow`: Higher quality, slower encoding (~30-40% slower)
- `--max-workers`: Maximum parallel transcoding workers (default: 2). Structure ready for future parallel processing.
- `--delete-original`: Delete the original file after successful transcode/remux. Default behavior keeps originals.
- `--notify-url`: ntfy endpoint, e.g. `http://localhost:1030/vidcompress`. To disable notifications, pass an empty value: `--notify-url ''`.
- `--notify-title`: Notification title (default: `VidCompress`).
- `--debug`: Verbose debug output to stdout.

Environment variables (optional):
- `NTFY_URL`: Default notification URL if `--notify-url` is not provided.
- `NTFY_TITLE`: Default notification title.

## Examples

Transcode to H.265 in MP4 with default 1080p bitrate (6Mbps), keeping originals:
```bash
python vidcompress.py "/media/Movies"
```

Use H.264 in MKV with custom bitrate and delete originals:
```bash
python vidcompress.py "/media/Movies" --video-codec h.264 --container mkv --bitrate 5000 --delete-original
```

Use VP9 in MKV with fast encoding preset:
```bash
python vidcompress.py "/media/Movies" --video-codec vp9 --container mkv --preset fast
```

Transcode with custom bitrate and notification:
```bash
python vidcompress.py "/media/Movies" --bitrate 4000 \
  --notify-url http://ntfy.local:1030/vidcompress --notify-title "Library Compress"
```

Disable notifications explicitly:
```bash
python vidcompress.py "/media/Movies" --notify-url ''
```

Use slow preset for higher quality (slower transcoding):
```bash
python vidcompress.py "/media/Movies" --preset slow --delete-original
```

## Notes for Users

- **All audio tracks preserved**: All audio streams from the source file are included in the output (not just the preferred one).
- **All subtitles preserved**: All subtitle streams from the source file are embedded in the output file (no separate SRT extraction).
- **Automatic bitrate selection**: When not specified, bitrate is chosen based on video resolution for optimal quality/size balance.
- **Audio/subtitle copy**: Audio and subtitle streams are copied as-is without re-encoding, preserving their original quality and format.
- **Language preferences**: While all audio tracks are preserved, the system still prefers Japanese, then English, then Vietnamese for metadata purposes (legacy functionality).
- **If codecs already match but only the container differs**, VidCompress performs a fast remux (no quality loss).
- **On macOS**, if FFmpeg exposes `h264_videotoolbox`/`hevc_videotoolbox`, hardware encoding is used automatically.
- **Hardware acceleration**: Supports GPU-accelerated decoding via VideoToolbox on Apple Silicon for faster processing (~220 fps on M4).
- **Targeting MP4** ensures faststart optimization so playback can begin sooner when streaming.
- **Preset only applies to software encoders** (libx265, libx264, libvpx-vp9); hardware encoders (VideoToolbox) ignore the preset parameter.

## Troubleshooting

- FFmpeg/FFprobe not found: Ensure they are installed and available in your `PATH`.
- Permission errors moving files: Run from a folder where you have write access.
- `curl` not found (for notifications): Install `curl` or disable notifications with `--notify-url ''`.

## License

This project is open-source and available under the [MIT License](LICENSE).
