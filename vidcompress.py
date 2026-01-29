import os
import subprocess
import sys
import time
import json
import argparse
import socket
import shutil
import zipfile
import threading
from concurrent.futures import ThreadPoolExecutor

# Global debug flag
DEBUG = True

def dprint(message: str):
    if DEBUG:
        print(message)

def get_ffmpeg_path():
    return 'ffmpeg'

def get_ffprobe_path():
    return 'ffprobe'

def get_media_info(file_path):
    try:
        command = [
            get_ffprobe_path(),
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    except json.JSONDecodeError:
        return None

def get_preferred_audio_index(media_info):
    streams = media_info.get('streams', [])
    audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
    if not audio_streams:
        return None

    prefs = [
        {'jpn', 'ja', 'japanese'},
        {'eng', 'en', 'english'},
        {'vie', 'vi', 'vietnamese'},
    ]

    langs = [s.get('tags', {}).get('language', '').strip().lower() for s in audio_streams]

    for tier in prefs:
        for lang in langs:
            if lang in tier:
                return audio_streams.index(s)
    return 0

def get_video_resolution(media_info):
    streams = media_info.get('streams', [])
    video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
    if video_stream:
        return video_stream.get('height', 0)
    return 0

def get_bitrate_for_resolution(resolution, custom_bitrate=None):
    if custom_bitrate:
        return custom_bitrate

    # Bitrate recommendations for H.265
    if resolution >= 2160:  # 4K
        return 12000
    elif resolution >= 1440:  # 2K
        return 8000
    elif resolution >= 1080:  # 1080p
        return 6000
    elif resolution >= 720:   # 720p
        return 4000
    else:  # SD
        return 2500

def is_mp4_faststart(file_path):
    try:
        filesize = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            offset = 0
            moov_pos = None
            mdat_pos = None
            while offset + 8 <= filesize:
                f.seek(offset)
                header = f.read(8)
                if len(header) < 8:
                    break
                size = int.from_bytes(header[0:4], 'big')
                box_type = header[4:8].decode('latin-1', errors='ignore')
                header_size = 8
                if size == 1:
                    ext = f.read(8)
                    if len(ext) < 8:
                        break
                    size = int.from_bytes(ext, 'big')
                    header_size = 16
                elif size == 0:
                    size = filesize - offset

                if box_type == 'moov' and moov_pos is None:
                    moov_pos = offset
                elif box_type == 'mdat' and mdat_pos is None:
                    mdat_pos = offset

                if size < header_size:
                    break
                offset += size

            if moov_pos is None or mdat_pos is None:
                dprint(f"[DEBUG] Could not determine moov/mdat positions for {file_path}; assuming optimized.")
                return True
            return moov_pos < mdat_pos
    except Exception as e:
        dprint(f"[DEBUG] Faststart check failed for {file_path}: {e}")
        return True

def send_notification(url: str, title: str, message: str):
    if not url:
        return
    try:
        cmd = ['curl', '-H', f'Title: {title}', '-d', message, url]
        subprocess.run(cmd, check=False, capture_output=not DEBUG, text=True)
        dprint(f"[DEBUG] Sent notification to {url}")
    except FileNotFoundError:
        dprint("[DEBUG] curl not found; skipping notification")
    except Exception as e:
        dprint(f"[DEBUG] Failed to send notification: {e}")

def get_duration(media_info):
    return float(media_info.get('format', {}).get('duration', 0))

def is_videotoolbox_available(codec_type):
    try:
        result = subprocess.run([get_ffmpeg_path(), '-codecs'], capture_output=True, text=True, check=True)
        if codec_type == 'hevc':
            return 'hevc_videotoolbox' in result.stdout
        elif codec_type == 'h264':
            return 'h264_videotoolbox' in result.stdout
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def transcode_file(input_path, output_path, video_codec_choice, bitrate=None, preset='medium', audio_map_index=None, web_optimize_mp4=None, media_info=None):
    ffmpeg_video_codec = ''
    if video_codec_choice == 'h.265':
        ffmpeg_video_codec = 'hevc_videotoolbox' if is_videotoolbox_available('hevc') else 'libx265'
    elif video_codec_choice == 'h.264':
        ffmpeg_video_codec = 'h264_videotoolbox' if is_videotoolbox_available('h264') else 'libx264'
    elif video_codec_choice == 'vp9':
        ffmpeg_video_codec = 'libvpx-vp9'

    command = [get_ffmpeg_path()]

    command += ['-hwaccel', 'videotoolbox']
    command += ['-thread_queue_size', '512']
    command += ['-i', input_path]

    command += ['-map', '0:v:0']
    command += ['-map', '0:a']

    command += ['-c:v', ffmpeg_video_codec]

    if bitrate is None and media_info:
        resolution = get_video_resolution(media_info)
        bitrate = get_bitrate_for_resolution(resolution)
    elif bitrate is None:
        bitrate = 6000

    command += ['-b:v', f'{bitrate}k']

    if 'videotoolbox' not in ffmpeg_video_codec and preset:
        command += ['-preset', preset]

    command += ['-c:a', 'aac', '-b:a', '128k', '-ac', '2']

    if output_path.lower().endswith('.mp4'):
        command += ['-c:s', 'mov_text']
    else:
        command += ['-c:s', 'copy']

    if web_optimize_mp4:
        command += ['-movflags', '+faststart']
    command += ['-y', output_path]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    process.wait()
    return process.returncode == 0

def remux_file(input_path, output_path, audio_map_index=None, web_optimize_mp4=None):
    command = [get_ffmpeg_path(), '-i', input_path]

    command += ['-map', '0:v:0']
    command += ['-map', '0:a']

    command += ['-c:v', 'copy']
    command += ['-c:a', 'copy']

    if output_path.lower().endswith('.mp4'):
        command += ['-c:s', 'mov_text']
    else:
        command += ['-c:s', 'copy']

    if web_optimize_mp4:
        command += ['-movflags', '+faststart']
    command += ['-y', output_path]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    process.wait()
    return process.returncode == 0

# Remove the extract_subtitles function

def main(folder_path, keep_original, video_codec_choice, container_choice, bitrate=None, preset='medium', max_workers=2, notify_url=None, notify_title=None, extract_subtitles_flag=True, archive_folder=None):
    VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m2ts']

    total_processed = 0
    total_skipped = 0
    total_transcoded = 0
    total_remuxed = 0
    total_errors = 0

    for root, _, files in os.walk(folder_path):
        for file in files:
            if not any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                continue

            input_path = os.path.join(root, file)
            media_info = get_media_info(input_path)


            if not media_info:
                print(f"Failed to get media info for {input_path}. Skipping.", file=sys.stderr)
                sys.stderr.flush()
                total_errors += 1
                continue

            video_stream = next((stream for stream in media_info.get('streams', []) if stream.get('codec_type') == 'video'), None)

            if not video_stream:
                total_skipped += 1
                continue

            container = media_info.get('format', {}).get('format_name')
            video_codec = video_stream.get('codec_name')
            audio_codec = next((s.get('codec_name') for s in media_info.get('streams', []) if s.get('codec_type') == 'audio'), None)

            # Determine the expected container name based on the choice
            expected_container_name = ''
            if container_choice == 'mp4':
                expected_container_name = 'mov,mp4,m4a,3gp,3g2,mj2'
            elif container_choice == 'mkv':
                expected_container_name = 'matroska,webm'

            # Determine the expected video codec name based on the choice
            expected_video_codec = ''
            if video_codec_choice == 'h.265':
                expected_video_codec = 'hevc'
            elif video_codec_choice == 'h.264':
                expected_video_codec = 'h264'
            elif video_codec_choice == 'vp9':
                expected_video_codec = 'vp9'

            is_video_codec_match = video_codec == expected_video_codec
            is_audio_codec_match = audio_codec == 'aac'

            def is_subtitle_codec_match(output_container, media_info):
                streams = media_info.get('streams', [])
                subtitle_streams = [s for s in streams if s.get('codec_type') == 'subtitle']
                if not subtitle_streams:
                    return True

                for subtitle_stream in subtitle_streams:
                    subtitle_codec = subtitle_stream.get('codec_name')
                    if output_container.lower().endswith('.mp4'):
                        if subtitle_codec != 'mov_text':
                            return False
                    else:
                        if subtitle_codec != 'copy':
                            return False
                return True

            is_container_match = container in expected_container_name.split(',')
            is_subtitle_codec_match = is_subtitle_codec_match(container_choice, media_info)

            needs_transcoding = False
            needs_remuxing = False

            if video_codec != expected_video_codec:
                needs_transcoding = True
                dprint(f"[DEBUG] Video codec mismatch: {video_codec} vs {expected_video_codec}")

            if not is_subtitle_codec_match:
                needs_transcoding = True
                dprint(f"[DEBUG] Subtitle codec mismatch")

            if container not in expected_container_name.split(','):
                needs_remuxing = True
                dprint(f"[DEBUG] Container mismatch: {container} vs {expected_container_name}")

            if container_choice == 'mp4' and container == 'mp4':
                faststart_ok = is_mp4_faststart(input_path)
                dprint(f"[DEBUG] Faststart status for {input_path}: {faststart_ok}")
                if not faststart_ok:
                    needs_remuxing = True

            if keep_original and (
                os.path.exists(os.path.join(root, f"{os.path.splitext(file)[0]}_re-encoded.{container_choice}")) or
                os.path.exists(os.path.join(root, f"{os.path.splitext(file)[0]}_remuxed.{container_choice}"))
            ):
                print(f'Skipping {input_path} (output already exists)')
                total_skipped += 1
                continue

            output_path_stem = os.path.splitext(input_path)[0]
            temp_output_path = f"{output_path_stem}.temp.{container_choice}"
            final_output_name_suffix = ""

            if needs_transcoding:
                action_type = "re-encoded"
                print(f'Transcoding {input_path} to {temp_output_path}...')
                dprint(f"[DEBUG] temp_output_path for transcode: {temp_output_path}")
                success = transcode_file(
                    input_path,
                    temp_output_path,
                    video_codec_choice,
                    bitrate=bitrate,
                    preset=preset,
                    media_info=media_info
                )
            elif needs_remuxing:
                action_type = "remuxed"
                print(f'Remuxing {input_path} to {temp_output_path}...')
                dprint(f"[DEBUG] temp_output_path for remux: {temp_output_path}")
                success = remux_file(
                    input_path,
                    temp_output_path
                )
            else:
                print(f"Warning: Unexpected state for {input_path}. Skipping.", file=sys.stderr)
                sys.stderr.flush()
                continue

            if success:
                try:
                    target_dir = os.path.dirname(input_path)
                    base_name = os.path.splitext(os.path.basename(input_path))[0]

                    if keep_original:
                        final_path = os.path.join(target_dir, f"{base_name}_{action_type}.{container_choice}")
                    else:
                        final_path = os.path.join(target_dir, f"{base_name}.{container_choice}")

                    dprint(f"[DEBUG] final_path: {final_path}")
                    dprint(f"[DEBUG] os.path.exists(input_path) before move: {os.path.exists(input_path)}")
                    dprint(f"[DEBUG] os.path.exists(temp_output_path) before move: {os.path.exists(temp_output_path)}")

                    os.makedirs(target_dir, exist_ok=True)

                    if not keep_original and os.path.exists(input_path) and input_path != final_path:
                        try:
                            dprint(f"[DEBUG] Moving original file to archive: {input_path}")
                            try:
                                os.rename(input_path, os.path.join(archive_folder, os.path.basename(input_path)))
                            except FileNotFoundError:
                                pass
                            dprint(f"[DEBUG] Moved original file: {input_path}")
                        except (OSError, zipfile.BadZipFile) as e:
                            print(f"Error moving  file {input_path}: {e}", file=sys.stderr)
                            sys.stderr.flush()
                            continue

                    shutil.move(temp_output_path, final_path)
                    time.sleep(0.1)
                    print(f'Successfully {action_type}d to {final_path}')
                    if action_type == 're-encoded':
                        total_transcoded += 1
                    elif action_type == 'remuxed':
                        total_remuxed += 1
                    dprint(f"[DEBUG] os.path.exists(final_path) after move: {os.path.exists(final_path)}")

                except Exception as e:
                    print(f'Error during file operation: {e}', file=sys.stderr)
                    sys.stderr.flush()
                    if os.path.exists(temp_output_path):
                        try:
                            os.remove(temp_output_path)
                        except OSError as e_remove:
                            print(f"Error removing temporary file {temp_output_path}: {e_remove}", file=sys.stderr)
                            sys.stderr.flush()
                            time.sleep(0.1)
            else:
                print(f'Failed to {action_type} {input_path}', file=sys.stderr)
                sys.stderr.flush()
                total_errors += 1
                if os.path.exists(temp_output_path):
                    try:
                        os.remove(temp_output_path)
                    except OSError as e_remove:
                        print(f"Error removing temporary file {temp_output_path}: {e_remove}", file=sys.stderr)
                        sys.stderr.flush()
                        time.sleep(0.1)

    summary_lines = [
        f"Folder: {folder_path}",
        f"Video codec: {video_codec_choice}",
        f"Container: {container_choice}",
        f"Skipped: {total_skipped}",
        f"Transcoded: {total_transcoded}",
        f"Remuxed: {total_remuxed}",
    ]
    summary = "\n".join(summary_lines)
    print("Summary:\n" + summary)

    notify_url = notify_url or os.environ.get('NTFY_URL')
    notify_title = notify_title or os.environ.get('NTFY_TITLE') or "VidCompress"
    if notify_url:
        send_notification(notify_url, notify_title, summary)
    else:
        dprint("[DEBUG] Notification URL not configured; skipping ntfy send")

if __name__ == '__main__':

        parser = argparse.ArgumentParser(description='VidCompress: Transcode video files to specified format.')
        parser.add_argument('folder_path', type=str, help='The path to the folder containing video files.')
        parser.add_argument('--keep-original', action='store_true', help='Keep the original file after successful transcoding.')
        parser.add_argument('--video-codec', type=str, default='h.265', choices=['h.265', 'h.264', 'vp9'],
                            help='Video codec to use for transcoding (default: h.265).')
        parser.add_argument('--container', type=str, default='mp4', choices=['mkv', 'mp4'],
                            help='Container format for the output file (default: mp4).')
        parser.add_argument('--bitrate', type=int, default=None, help='Video bitrate in kbps (e.g., 6000).')
        parser.add_argument('--preset', type=str, default='medium', choices=['fast', 'medium', 'slow'],
                            help='Encoding preset: fast (lower quality, faster), medium (balanced), slow (higher quality, slower).')
        parser.add_argument('--max-workers', type=int, default=2, help='Maximum number of parallel transcoding workers.')
        parser.add_argument('--debug', action='store_true', help='Enable verbose debug output.')
        parser.add_argument('--notify-url', type=str, default='http://localhost:1030/vidcompress', help='ntfy target URL.')
        parser.add_argument('--notify-title', type=str, default='VidCompress', help='Notification title for ntfy.')
        parser.add_argument('--no-extract-subtitles', action='store_false', dest='extract_subtitles', help='Disable subtitle extraction.')
        parser.set_defaults(extract_subtitles=True)

        args = parser.parse_args()

        if not os.path.exists(args.folder_path):
            print(f"Error: No such file or directory: '{args.folder_path}'", file=sys.stderr)
            sys.stderr.flush()
            sys.exit(1)

        DEBUG = args.debug

        main(
            args.folder_path,
            args.keep_original,
            args.video_codec,
            args.container,
            bitrate=args.bitrate,
            preset=args.preset,
            max_workers=args.max_workers,
            notify_url=args.notify_url,
            notify_title=args.notify_title,
            extract_subtitles_flag=args.extract_subtitles
        )