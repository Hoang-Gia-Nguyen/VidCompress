
import os
import subprocess
import sys
import time
import json
import argparse

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

def is_videotoolbox_available():
    """
    Checks if VideoToolbox is available for HEVC encoding.
    """
    try:
        result = subprocess.run([get_ffmpeg_path(), '-codecs'], capture_output=True, text=True, check=True)
        return 'hevc_videotoolbox' in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def transcode_file(input_path, output_path, use_videotoolbox):
    """
    Transcodes the input file to the desired format.
    """
    video_codec = 'hevc_videotoolbox' if use_videotoolbox else 'libx265'
    
    command = [
        get_ffmpeg_path(),
        '-i', input_path,
        '-c:v', video_codec,
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


def main(folder_path, keep_original):
    """
    Scans the folder for media files and converts them if necessary.
    """
    use_videotoolbox = is_videotoolbox_available()
    if use_videotoolbox:
        print("VideoToolbox is available. Using hardware acceleration.")
    else:
        print("VideoToolbox is not available. Using software encoding.")

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

            is_correct_format = container == 'matroska,webm' and video_codec == 'hevc' and audio_codec == 'aac' and audio_channels == 2

            if is_correct_format:
                print(f'Skipping {input_path} (already in the correct format)')
                continue

            output_path = os.path.splitext(input_path)[0] + '.mkv'
            
            if input_path.lower().endswith('.mkv'):
                temp_output_path = os.path.splitext(input_path)[0] + '.temp.mkv'
                print(f'Re-encoding {input_path} to {temp_output_path}...')
                if transcode_file(input_path, temp_output_path, use_videotoolbox):
                    if not keep_original:
                        os.remove(input_path)
                    os.rename(temp_output_path, input_path)
                    print(f'
Successfully re-encoded {input_path}')
                else:
                    print(f'
Failed to re-encode {input_path}')
                    if os.path.exists(temp_output_path):
                        os.remove(temp_output_path)
            else:
                if os.path.exists(output_path):
                    print(f'Removing {input_path} since correctly formatted file already exists')
                    if not keep_original:
                        os.remove(input_path)
                    continue

                print(f'Transcoding {input_path} to {output_path}...')
                if transcode_file(input_path, output_path, use_videotoolbox):
                    print(f'
Successfully transcoded {input_path}')
                    if not keep_original:
                        os.remove(input_path)
                else:
                    print(f'
Failed to transcode {input_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='VidCompress: Transcode video files to HEVC/AAC MKV format.')
    parser.add_argument('folder_path', type=str, help='The path to the folder containing video files.')
    parser.add_argument('--keep-original', action='store_true', help='Do not delete the original file after successful transcoding.')
    
    args = parser.parse_args()
    
    main(args.folder_path, args.keep_original)
