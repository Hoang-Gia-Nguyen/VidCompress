
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
            media_info = get_media_info(input_path)

            if not media_info:
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
            is_container_match = container == expected_container_name

            if is_video_codec_match and is_audio_codec_match and is_container_match:
                print(f'Skipping {input_path} (already in the correct format and container)')
                continue

            output_path = os.path.splitext(input_path)[0] + '.' + container_choice
            temp_output_path = os.path.splitext(input_path)[0] + '.temp.' + container_choice

            # Check if only remuxing is needed
            if is_video_codec_match and is_audio_codec_match and not is_container_match:
                print(f'Remuxing {input_path} to {output_path} (codecs match, container different)...')
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                
                if remux_file(input_path, temp_output_path):
                    try:
                        target_dir = os.path.dirname(input_path)
                        base_name = os.path.splitext(os.path.basename(input_path))[0]
                        
                        if keep_original:
                            final_path = os.path.join(target_dir, f"{base_name}_remuxed.{container_choice}")
                        else:
                            final_path = input_path
                        
                        os.makedirs(target_dir, exist_ok=True)
                        
                        if not keep_original and os.path.exists(input_path):
                            os.remove(input_path)
                            
                        shutil.move(temp_output_path, final_path)
                        print(f'Successfully remuxed to {final_path}')
                    except Exception as e:
                        print(f'Error during file operation: {e}')
                        if os.path.exists(temp_output_path):
                            os.remove(temp_output_path)
                else:
                    print(f'Failed to remux {input_path}')
                    if os.path.exists(temp_output_path):
                        os.remove(temp_output_path)
                continue # Move to next file after remux attempt

            # Original transcoding logic for when re-encoding is needed
            if input_path.lower().endswith(f'.{container_choice}'):
                print(f'Re-encoding {input_path} to {temp_output_path}...')
                
                # Remove any existing temporary file
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                
                if transcode_file(input_path, temp_output_path, video_codec_choice):
                    try:
                        # Determine the final output path based on keep_original flag
                        target_dir = os.path.dirname(input_path)
                        base_name = os.path.splitext(os.path.basename(input_path))[0]
                        
                        if keep_original:
                            # Create a new filename with _re-encoded suffix
                            final_path = os.path.join(target_dir, f"{base_name}_re-encoded.{container_choice}")
                        else:
                            final_path = input_path
                        
                        # Ensure target directory exists
                        os.makedirs(target_dir, exist_ok=True)
                        
                        if not keep_original and os.path.exists(input_path):
                            # For non-keep-original case, remove input after successful re-encoding
                            os.remove(input_path)
                            
                        # Move temp file to final destination
                        shutil.move(temp_output_path, final_path)
                        print(f'Successfully re-encoded to {final_path}')
                    except Exception as e:
                        print(f'Error during file operation: {e}')
                        if os.path.exists(temp_output_path):
                            os.remove(temp_output_path)
                else:
                    print(f'Failed to re-encode {input_path}')
                    if os.path.exists(temp_output_path):
                        os.remove(temp_output_path)
            else:
                # If the input file is not already in the target container, always transcode/remux to a temp file first
                print(f'Processing {input_path} to {temp_output_path}...')
                
                # Remove any existing temporary file
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)

                success = False
                if is_video_codec_match and is_audio_codec_match:
                    success = remux_file(input_path, temp_output_path)
                    action_type = "remuxed"
                else:
                    success = transcode_file(input_path, temp_output_path, video_codec_choice)
                    action_type = "transcoded"

                if success:
                    try:
                        target_dir = os.path.dirname(input_path)
                        base_name = os.path.splitext(os.path.basename(input_path))[0]
                        
                        if keep_original:
                            final_path = os.path.join(target_dir, f"{base_name}_{action_type}.{container_choice}")
                        else:
                            final_path = input_path
                        
                        os.makedirs(target_dir, exist_ok=True)
                        
                        if not keep_original and os.path.exists(input_path):
                            os.remove(input_path)
                            
                        shutil.move(temp_output_path, final_path)
                        print(f'Successfully {action_type} to {final_path}')
                    except Exception as e:
                        print(f'Error during file operation: {e}')
                        if os.path.exists(temp_output_path):
                            os.remove(temp_output_path)
                else:
                    print(f'Failed to {action_type} {input_path}')
                    if os.path.exists(temp_output_path):
                        os.remove(temp_output_path)


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
        sys.exit(1)
    
    main(args.folder_path, args.keep_original, args.video_codec, args.container)
