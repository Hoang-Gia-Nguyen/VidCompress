
import os
import subprocess
import sys
import time
import json
import argparse
import socket
import shutil

# Global debug flag
DEBUG = False

def dprint(message: str):
    if DEBUG:
        print(message)

# This comment is to trigger the GitHub Actions workflow on the development branch.

def get_ffmpeg_path():
    """
    Returns the path to the ffmpeg executable.
    """
    return 'ffmpeg'

def get_ffprobe_path():
    """
    Returns the path to the ffprobe executable.
    """
    return 'ffprobe'

def get_media_info(file_path):
    """
    Returns a dictionary containing the media information of the file.
    """
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
    """
    Returns the 0-based index among audio streams (for ffmpeg mapping 0:a:<idx>)
    using the preference order: Japanese > English > Vietnamese > first audio.
    If no audio streams exist, returns None.
    """
    streams = media_info.get('streams', [])
    audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
    if not audio_streams:
        return None

    # Normalize and inspect language tags
    def lang_of(stream):
        tags = stream.get('tags') or {}
        # Common tag keys (case-insensitive)
        for key in ('language', 'LANGUAGE', 'Language'): 
            if key in tags and isinstance(tags[key], str):
                return tags[key].strip().lower()
        return ''

    prefs = [
        {'jpn', 'ja', 'japanese'},
        {'eng', 'en', 'english'},
        {'vie', 'vi', 'vietnamese'},
    ]

    langs = [lang_of(s) for s in audio_streams]

    # Exact or contains match per preference tier
    for tier in prefs:
        for i, lang in enumerate(langs):
            if not lang:
                continue
            # direct match
            if lang in tier:
                return i
            # contains match for variants like 'ja-jp', 'en-US', etc.
            if any(code in lang for code in tier):
                return i

    # Fallback: first audio
    return 0

def is_mp4_faststart(file_path):
    """
    Heuristically checks if an MP4 file is web-optimized (faststart), i.e.,
    the 'moov' atom appears before the 'mdat' atom at the start of the file.
    Returns True if optimized, False if clearly not. If detection fails,
    returns True (avoid unnecessary remux on uncertainty).
    """
    try:
        filesize = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            offset = 0
            moov_pos = None
            mdat_pos = None
            # Iterate top-level boxes
            while offset + 8 <= filesize and (moov_pos is None or mdat_pos is None):
                f.seek(offset)
                header = f.read(8)
                if len(header) < 8:
                    break
                size = int.from_bytes(header[0:4], 'big')
                box_type = header[4:8].decode('latin-1', errors='ignore')
                header_size = 8
                if size == 1:
                    # 64-bit extended size
                    ext = f.read(8)
                    if len(ext) < 8:
                        break
                    size = int.from_bytes(ext, 'big')
                    header_size = 16
                elif size == 0:
                    # box extends to EOF
                    size = filesize - offset

                if box_type == 'moov' and moov_pos is None:
                    moov_pos = offset
                elif box_type == 'mdat' and mdat_pos is None:
                    mdat_pos = offset

                if size < header_size:
                    # Corrupt; bail out
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
    """
    Sends a notification to an ntfy server via curl.
    Example: curl -H "Title: ..." -d "..." http://host:port/topic
    """
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
    """
    Returns the duration of the video in seconds.
    """
    return float(media_info.get('format', {}).get('duration', 0))

def is_videotoolbox_available(codec_type):
    """
    Checks if VideoToolbox is available for the specified codec type.
    """
    try:
        result = subprocess.run([get_ffmpeg_path(), '-codecs'], capture_output=True, text=True, check=True)
        if codec_type == 'hevc':
            return 'hevc_videotoolbox' in result.stdout
        elif codec_type == 'h264':
            return 'h264_videotoolbox' in result.stdout
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def transcode_file(input_path, output_path, video_codec_choice, audio_map_index=None, web_optimize_mp4=False):
    """
    Transcodes the input file to the desired format.
    """
    ffmpeg_video_codec = ''
    if video_codec_choice == 'h.265':
        ffmpeg_video_codec = 'hevc_videotoolbox' if is_videotoolbox_available('hevc') else 'libx265'
    elif video_codec_choice == 'h.264':
        ffmpeg_video_codec = 'h264_videotoolbox' if is_videotoolbox_available('h264') else 'libx264'
    elif video_codec_choice == 'vp9':
        ffmpeg_video_codec = 'libvpx-vp9'
    
    command = [get_ffmpeg_path(), '-i', input_path]

    # Explicitly map the primary video, chosen audio, and all subtitle streams
    command += ['-map', '0:v:0']
    if audio_map_index is not None:
        command += ['-map', f'0:a:{audio_map_index}']
    command += ['-map', '0:s?']

    # Set codecs
    command += ['-c:v', ffmpeg_video_codec]
    if 'videotoolbox' in ffmpeg_video_codec:
        command += ['-q:v', '65', '-b:v', '3M']
    if audio_map_index is not None:
        command += ['-c:a', 'aac', '-ac', '2']
    # For subtitles, copy them to keep them, converting to a compatible format for mp4
    if '.mp4' in output_path:
        command += ['-c:s', 'mov_text']
    else:
        command += ['-c:s', 'copy']
    # Web optimize MP4 if requested
    if web_optimize_mp4:
        command += ['-movflags', '+faststart']
    command += ['-y', output_path]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    process.wait()
    return process.returncode == 0


def remux_file(input_path, output_path, audio_map_index=None, web_optimize_mp4=False):
    """
    Remuxes the input file to a new container without re-encoding.
    """
    command = [get_ffmpeg_path(), '-i', input_path]

    # Explicitly map the primary video, chosen audio, and all subtitle streams
    command += ['-map', '0:v:0']
    if audio_map_index is not None:
        command += ['-map', f'0:a:{audio_map_index}']
    command += ['-map', '0:s?']

    # Copy streams, but convert subtitles for MP4
    command += ['-c:v', 'copy']
    command += ['-c:a', 'copy']
    if '.mp4' in output_path:
        command += ['-c:s', 'mov_text']
    else:
        command += ['-c:s', 'copy']
    # Web optimize MP4 if requested
    if web_optimize_mp4:
        command += ['-movflags', '+faststart']
    command += ['-y', output_path]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    process.wait()
    return process.returncode == 0


def extract_subtitles(file_path, output_dir):
    """
    Extracts all subtitle streams from a video file and saves them as SRT files.
    The SRT files are named based on the video filename and a 2-letter language code.
    """
    media_info = get_media_info(file_path)
    if not media_info:
        return

    subtitle_streams = [s for s in media_info.get('streams', []) if s.get('codec_type') == 'subtitle']
    if not subtitle_streams:
        return

    base_name = os.path.splitext(os.path.basename(file_path))[0]

    # ISO 639-2 to 639-1 mapping for common languages
    lang_map = {
        'eng': 'en', 'ara': 'ar', 'ger': 'de', 'spa': 'es', 'fre': 'fr',
        'ita': 'it', 'por': 'pt', 'rus': 'ru', 'jpn': 'ja', 'kor': 'ko',
        'chi': 'zh', 'hin': 'hi', 'dut': 'nl', 'swe': 'sv', 'nor': 'no',
        'dan': 'da', 'fin': 'fi', 'pol': 'pl', 'tur': 'tr', 'heb': 'he',
        'gre': 'el', 'vie': 'vi'
    }

    for i, stream in enumerate(subtitle_streams):
        original_lang_code = stream.get('tags', {}).get('language', f'sub{i}')
        
        # Use the 2-letter code if available, otherwise fallback to the original
        lang_code = lang_map.get(original_lang_code.lower(), original_lang_code)

        output_path = os.path.join(output_dir, f"{base_name}.{lang_code}.srt")
        
        command = [
            get_ffmpeg_path(),
            '-i', file_path,
            '-map', f'0:s:{i}',
            '-c:s', 'srt',
            '-y', output_path
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Extracted subtitle: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error extracting subtitle for stream {i}: {e.stderr}", file=sys.stderr)
            sys.stderr.flush()




def main(folder_path, keep_original, video_codec_choice, container_choice, notify_url=None, notify_title=None, extract_subtitles_only=False):
    """
    Scans the folder for media files and converts them if necessary.
    """
    if extract_subtitles_only:
        print("Mode: Extract subtitles only.")
    else:
        print(f"Selected video codec: {video_codec_choice}")
        print(f"Selected container: {container_choice}")

    VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m2ts']

    # Summary counters
    total_processed = 0
    total_skipped = 0
    total_transcoded = 0
    total_remuxed = 0
    total_errors = 0
    total_subtitle_extractions = 0
    for root, _, files in os.walk(folder_path):
        for file in files:
            if not any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                continue

            input_path = os.path.join(root, file)

            if extract_subtitles_only:
                print(f"Extracting subtitles from {input_path}...")
                target_dir = os.path.dirname(input_path)
                extract_subtitles(input_path, target_dir)
                total_subtitle_extractions += 1
                continue

            total_processed += 1
            dprint(f"[DEBUG] Processing file: {input_path}")
            media_info = get_media_info(input_path)

            if not media_info:
                print(f"Failed to get media info for {input_path}. Skipping.", file=sys.stderr)
                sys.stderr.flush()
                total_errors += 1
                continue
            
            # Extract subtitles from the original file before any processing
            extract_subtitles(input_path, os.path.dirname(input_path))

            video_stream = next((stream for stream in media_info.get('streams', []) if stream.get('codec_type') == 'video'), None)
            
            if not video_stream:
                total_skipped += 1
                continue

            # Collect streams and choose preferred audio stream index
            streams = media_info.get('streams', [])
            audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
            preferred_audio_index = get_preferred_audio_index(media_info)

            audio_stream = None
            if preferred_audio_index is not None and preferred_audio_index < len(audio_streams):
                audio_stream = audio_streams[preferred_audio_index]
            else:
                audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)

            container = media_info.get('format', {}).get('format_name')
            video_codec = video_stream.get('codec_name')
            audio_codec = audio_stream.get('codec_name') if audio_stream else ''
            audio_channels = audio_stream.get('channels') if audio_stream else 0

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
            is_audio_codec_match = audio_codec == 'aac' and audio_channels == 2
            is_container_match = container in expected_container_name.split(',') or container == expected_container_name

            # Determine if transcoding or remuxing is needed
            needs_transcoding = not (is_video_codec_match and is_audio_codec_match)
            needs_remuxing = not is_container_match

            # If targeting MP4 and everything matches, ensure it is web-optimized
            if (not needs_transcoding) and container_choice == 'mp4' and (
                is_container_match and ('mp4' in expected_container_name)
            ):
                faststart_ok = is_mp4_faststart(input_path)
                dprint(f"[DEBUG] Faststart status for {input_path}: {faststart_ok}")
                if not faststart_ok:
                    needs_remuxing = True

            if not needs_transcoding and not needs_remuxing:
                print(f'Skipping {input_path} (already in the correct format and container)')
                total_skipped += 1
                continue

            output_path_stem = os.path.splitext(input_path)[0]
            temp_output_path = f"{output_path_stem}.temp.{container_choice}"
            final_output_name_suffix = ""

            # Remove any existing temporary file before starting
            if os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except OSError as e:
                    print(f"Error removing existing temporary file {temp_output_path}: {e}", file=sys.stderr)
                    sys.stderr.flush()
                    continue # Skip to next file if we can't clean up

            success = False
            action_type = ""

            if needs_transcoding:
                action_type = "re-encoded"
                print(f'Transcoding {input_path} to {temp_output_path}...')
                dprint(f"[DEBUG] temp_output_path for transcode: {temp_output_path}")
                success = transcode_file(
                    input_path,
                    temp_output_path,
                    video_codec_choice,
                    preferred_audio_index,
                    web_optimize_mp4=(container_choice == 'mp4')
                )
            elif needs_remuxing: # Only remuxing is needed
                action_type = "remuxed"
                print(f'Remuxing {input_path} to {temp_output_path}...')
                dprint(f"[DEBUG] temp_output_path for remux: {temp_output_path}")
                success = remux_file(
                    input_path,
                    temp_output_path,
                    preferred_audio_index,
                    web_optimize_mp4=(container_choice == 'mp4')
                )
            else:
                # This case should ideally not be reached if the above logic is correct
                # It implies a file needs neither transcoding nor remuxing, but wasn't skipped.
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

                    # Handle existing original file if not keeping original
                    if not keep_original and os.path.exists(input_path) and input_path != final_path:
                        try:
                            dprint(f"[DEBUG] Attempting to remove original file: {input_path}")
                            os.remove(input_path)
                            time.sleep(0.1)
                            dprint(f"[DEBUG] Removed original file: {input_path}")
                        except OSError as e:
                            print(f"Error removing original file {input_path}: {e}", file=sys.stderr)
                            sys.stderr.flush()
                            continue # Skip to next file if we can't remove original

                    shutil.move(temp_output_path, final_path)
                    time.sleep(0.1)
                    print(f'Successfully {action_type} to {final_path}')
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

    # After processing all files, output summary and optionally notify
    hostname = socket.gethostname()
    if extract_subtitles_only:
        summary_lines = [
            f"Folder: {folder_path}",
            f"Operation: Extract Subtitles Only",
            f"Files processed for subtitles: {total_subtitle_extractions}",
        ]
    else:
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

    # Resolve notification settings (CLI args already have defaults)
    notify_url = notify_url or os.environ.get('NTFY_URL')
    notify_title = notify_title or os.environ.get('NTFY_TITLE') or "VidCompress"
    if notify_url:
        send_notification(notify_url, notify_title, summary)
    else:
        dprint("[DEBUG] Notification URL not configured; skipping ntfy send")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='VidCompress: Transcode video files to specified format.')
    parser.add_argument('folder_path', type=str, help='The path to the folder containing video files.')
    parser.add_argument('--keep-original', action='store_true', help='Do not delete the original file after successful transcoding.')
    parser.add_argument('--video-codec', type=str, default='h.265', choices=['h.265', 'h.264', 'vp9'],
                        help='Video codec to use for transcoding (default: h.265).')
    parser.add_argument('--container', type=str, default='mp4', choices=['mkv', 'mp4'],
                        help='Container format for the output file (default: mp4).')
    parser.add_argument('--debug', action='store_true', help='Enable verbose debug output.')
    parser.add_argument('--notify-url', type=str, default='http://localhost:1030/vidcompress', help='ntfy target URL, e.g., http://localhost:1030/vidcompress')
    parser.add_argument('--notify-title', type=str, default='VidCompress', help='Notification title for ntfy')
    parser.add_argument('--extract-subtitles-only', action='store_true', help='Only extract subtitles without any transcoding or remuxing.')
    
    args = parser.parse_args()
    
    # Validate the input path
    if not os.path.exists(args.folder_path):
        print(f"Error: No such file or directory: '{args.folder_path}'", file=sys.stderr)
        sys.stderr.flush()
        sys.exit(1)
    
    # Set global debug flag
    DEBUG = args.debug
    
    main(
        args.folder_path,
        args.keep_original,
        args.video_codec,
        args.container,
        notify_url=args.notify_url,
        notify_title=args.notify_title,
        extract_subtitles_only=args.extract_subtitles_only
    )
