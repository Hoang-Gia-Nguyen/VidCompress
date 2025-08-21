
import pytest
import os
import tempfile
import shutil
import subprocess
import json
import time # Added for time.sleep
from pathlib import Path

# Ensure the project root is on sys.path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vidcompress import get_media_info, get_ffmpeg_path, get_ffprobe_path

@pytest.fixture(scope="session")
def ffmpeg_path():
    """Fixture to get the ffmpeg path, ensuring it's available."""
    path = get_ffmpeg_path()
    try:
        subprocess.run([path, '-version'], check=True, capture_output=True)
        return path
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip(f"ffmpeg not found or not working at {path}")

@pytest.fixture(scope="session")
def ffprobe_path():
    """Fixture to get the ffprobe path, ensuring it's available."""
    path = get_ffprobe_path()
    try:
        subprocess.run([path, '-version'], check=True, capture_output=True)
        return path
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip(f"ffprobe not found or not working at {path}")

@pytest.fixture
def temp_dir():
    """Creates a temporary directory for test files within test_output."""
    temp_dir_path = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_output', 'temp_test_case_dir')))
    if temp_dir_path.exists():
        shutil.rmtree(temp_dir_path)
    temp_dir_path.mkdir(parents=True, exist_ok=True)
    yield temp_dir_path
    shutil.rmtree(temp_dir_path)

@pytest.fixture
def sample_media_info_data():
    """Returns a sample media info dictionary for mocking."""
    return {
        'format': {
            'duration': '60.123456',
            'format_name': 'matroska,webm'
        },
        'streams': [
            {
                'codec_type': 'video',
                'codec_name': 'h264'
            },
            {
                'codec_type': 'audio',
                'codec_name': 'aac',
                'channels': 2
            }
        ]
    }

def create_test_video_file(ffmpeg_path, temp_dir, filename, video_codec, audio_codec, container, duration=1):
    """Helper function to create test videos with different codecs."""
    video_path = os.path.join(temp_dir, f'{filename}.{container}')
    
    command = [
        ffmpeg_path, '-y',
        '-f', 'lavfi',
        '-i', f'testsrc=duration={duration}:size=320x240:rate=30',
        '-f', 'lavfi',
        '-i', f'sine=frequency=440:duration={duration}',
        '-c:v', video_codec,
        '-c:a', audio_codec,
        '-ac', '2',  # 2 audio channels
        video_path
    ]
    
    try:
        subprocess.run(command, check=True, capture_output=True)
        time.sleep(0.1)
    except subprocess.CalledProcessError as e:
        print(f"Error creating test video {filename}.{container}: {e.stderr.decode()}", file=sys.stderr)
        raise
    return video_path

@pytest.fixture(scope="session")
def test_data_dir(ffmpeg_path):
    """
    Creates a directory with various sample video files for testing.
    Uses a dedicated test_output directory within the project.
    """
    data_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_output', 'test_videos')))
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # H.264 MP4 (common format, needs transcoding to H.265)
    create_test_video_file(ffmpeg_path, data_dir, 'h264_sample', 'libx264', 'aac', 'mp4')
    
    # H.265 MKV (already target codec, needs remuxing to MP4 if container changes)
    create_test_video_file(ffmpeg_path, data_dir, 'h265_sample', 'libx265', 'aac', 'mkv')

    # VP9 WebM (different codec, needs transcoding)
    create_test_video_file(ffmpeg_path, data_dir, 'vp9_sample', 'libvpx-vp9', 'libopus', 'webm')

    # H.264 MKV (needs remuxing to MP4 if container changes, codecs are compatible)
    create_test_video_file(ffmpeg_path, data_dir, 'h264_mkv_sample', 'libx264', 'aac', 'mkv')

    # Corrupted/Invalid file (create a dummy file that's not a valid video)
    corrupted_file_path = data_dir / "corrupted_video.mp4"
    corrupted_file_path.write_text("This is not a valid video file content.")

    yield data_dir

@pytest.fixture
def setup_test_video(temp_dir, test_data_dir):
    """
    Fixture to set up an isolated test environment with a copy of a test video.
    Returns the path to the temporary test directory and the copied video path.
    """
    def _setup(video_filename):
        source_video_path = test_data_dir / video_filename
        if not source_video_path.exists():
            pytest.fail(f"Test video file not found: {source_video_path}")

        test_case_dir = Path(temp_dir) / Path(video_filename).stem
        test_case_dir.mkdir(parents=True, exist_ok=True)
        
        copied_video_path = test_case_dir / video_filename
        shutil.copy2(source_video_path, copied_video_path)
        time.sleep(0.1)
        
        return test_case_dir, copied_video_path
    return _setup

@pytest.fixture
def run_vidcompress_cli():
    """
    Fixture to run the vidcompress.py script as a subprocess.
    Returns a function that takes arguments for the script.
    """
    def _run_cli(folder_path, keep_original=False, video_codec='h.265', container='mp4'):
        cmd = [
            sys.executable,
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vidcompress.py')),
            str(folder_path)
        ]
        if keep_original:
            cmd.append('--keep-original')
        cmd.extend(['--video-codec', video_codec])
        cmd.extend(['--container', container])
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        return process
    return _run_cli

