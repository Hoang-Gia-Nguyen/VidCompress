
import os
import subprocess
import sys
import time
import json
import argparse
import shutil

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

def transcode_file(input_path, output_path, video_codec_choice):
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
    
    command = [
        get_ffmpeg_path(),
        '-i', input_path,
        '-c:v', ffmpeg_video_codec,
        '-c:a', 'aac',
        '-ac', '2',
        '-y',
        output_path
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    process.wait()
    return process.returncode == 0


def remux_file(input_path, output_path):
    """
    Remuxes the input file to a new container without re-encoding.
    """
    command = [
        get_ffmpeg_path(),
        '-i', input_path,
        '-c', 'copy',
        '-y',
        output_path
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    process.wait()
    return process.returncode == 0


def main(folder_path, keep_original, video_codec_choice, container_choice):
    """
    Scans the folder for media files and converts them if necessary.
    """
    print(f"Selected video codec: {video_codec_choice}")
    print(f"Selected container: {container_choice}")

    VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m2ts']
    for root, _, files in os.walk(folder_path):
        for file in files:
            if not any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                continue

            input_path = os.path.join(root, file)
            print(f"[DEBUG] Processing file: {input_path}")
            media_info = get_media_info(input_path)

            if not media_info:
                print(f"Failed to get media info for {input_path}. Skipping.", file=sys.stderr)
                sys.stderr.flush()
                continue

            video_stream = next((stream for stream in media_info.get('streams', []) if stream.get('codec_type') == 'video'), None)
            
            if not video_stream:
                continue

            audio_stream = next((stream for stream in media_info.get('streams', []) if stream.get('codec_type') == 'audio'), None)

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


            if is_video_codec_match and is_audio_codec_match and is_container_match:
                print(f'Skipping {input_path} (already in the correct format and container)')
                continue

            # Determine if transcoding or remuxing is needed
            needs_transcoding = not (is_video_codec_match and is_audio_codec_match)
            needs_remuxing = not is_container_match

            if not needs_transcoding and not needs_remuxing:
                print(f'Skipping {input_path} (already in the correct format and container)')
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
                print(f"[DEBUG] temp_output_path for transcode: {temp_output_path}")
                success = transcode_file(input_path, temp_output_path, video_codec_choice)
            elif needs_remuxing: # Only remuxing is needed
                action_type = "remuxed"
                print(f'Remuxing {input_path} to {temp_output_path}...')
                print(f"[DEBUG] temp_output_path for remux: {temp_output_path}")
                success = remux_file(input_path, temp_output_path)
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

                    print(f"[DEBUG] final_path: {final_path}")
                    print(f"[DEBUG] os.path.exists(input_path) before move: {os.path.exists(input_path)}")
                    print(f"[DEBUG] os.path.exists(temp_output_path) before move: {os.path.exists(temp_output_path)}")

                    os.makedirs(target_dir, exist_ok=True)

                    # Handle existing original file if not keeping original
                    if not keep_original and os.path.exists(input_path) and input_path != final_path:
                        try:
                            print(f"[DEBUG] Attempting to remove original file: {input_path}")
                            os.remove(input_path)
                            time.sleep(0.1)
                            print(f"[DEBUG] Removed original file: {input_path}")
                        except OSError as e:
                            print(f"Error removing original file {input_path}: {e}", file=sys.stderr)
                            sys.stderr.flush()
                            continue # Skip to next file if we can't remove original

                    shutil.move(temp_output_path, final_path)
                    time.sleep(0.1)
                    print(f'Successfully {action_type} to {final_path}')
                    print(f"[DEBUG] os.path.exists(final_path) after move: {os.path.exists(final_path)}")

                    

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
                if os.path.exists(temp_output_path):
                    try:
                        os.remove(temp_output_path)
                    except OSError as e_remove:
                        print(f"Error removing temporary file {temp_output_path}: {e_remove}", file=sys.stderr)
                        sys.stderr.flush()
                        time.sleep(0.1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='VidCompress: Transcode video files to specified format.')
    parser.add_argument('folder_path', type=str, help='The path to the folder containing video files.')
    parser.add_argument('--keep-original', action='store_true', help='Do not delete the original file after successful transcoding.')
    parser.add_argument('--video-codec', type=str, default='h.265', choices=['h.265', 'h.264', 'vp9'],
                        help='Video codec to use for transcoding (default: h.265).')
    parser.add_argument('--container', type=str, default='mp4', choices=['mkv', 'mp4'],
                        help='Container format for the output file (default: mp4).')
    
    args = parser.parse_args()
    
    # Validate the input path
    if not os.path.exists(args.folder_path):
        print(f"Error: No such file or directory: '{args.folder_path}'", file=sys.stderr)
        sys.stderr.flush()
        sys.exit(1)
    
    main(args.folder_path, args.keep_original, args.video_codec, args.container)
