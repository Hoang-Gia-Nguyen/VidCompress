import pytest
import os
import tempfile
import shutil
import subprocess
import json
from pathlib import Path
from vidcompress import main

@pytest.fixture
def temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

def safe_remove(path):
    """Safely remove a file if it exists"""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def safe_rename(src, dst):
    """Safely rename a file, removing destination if it exists"""
    try:
        if os.path.exists(dst):
            os.remove(dst)
        os.rename(src, dst)
    except Exception as e:
        print(f"Error during rename: {e}")
        # If rename fails, try copy and delete
        try:
            shutil.copy2(src, dst)
            os.remove(src)
        except Exception as e:
            print(f"Error during copy fallback: {e}")
            raise

def clean_temp_files(path):
    """Clean up any temporary files from failed tests"""
    # Clean both temp and final files to ensure clean state
    temp_path = os.path.splitext(path)[0] + '.temp.mkv'
    mkv_path = os.path.splitext(path)[0] + '.mkv'
    safe_remove(temp_path)
    safe_remove(mkv_path)

def create_test_video(temp_dir, filename, video_codec, audio_codec, container):
    """Helper function to create test videos with different codecs"""
    import subprocess
    video_path = os.path.join(temp_dir, f'test_{filename}.{container}')
    # Clean any existing files first
    clean_temp_files(video_path)
    safe_remove(video_path)
    
    subprocess.run([
        'ffmpeg', '-y',
        '-f', 'lavfi',
        '-i', 'testsrc=duration=1:size=320x240:rate=30',
        '-f', 'lavfi',
        '-i', 'sine=frequency=440:duration=1',
        '-c:v', video_codec,
        '-c:a', audio_codec,
        '-ac', '2',  # 2 audio channels
        video_path
    ], check=True, capture_output=True)
    return video_path

@pytest.fixture
def sample_videos(temp_dir):
    """Create multiple test videos with different codecs"""
    videos = {}
    
    # Create single-audio videos
    for config in [
        ('h264_aac', 'libx264', 'aac', 'mp4'),
        ('vp8_vorbis', 'libvpx', 'libvorbis', 'webm'),
        ('mpeg4_mp3', 'mpeg4', 'libmp3lame', 'avi')
    ]:
        name, vcodec, acodec, container = config
        videos[name] = create_test_video(temp_dir, name, vcodec, acodec, container)
    
    return videos

def test_main_empty_folder(temp_dir):
    main(temp_dir, True)
    assert len(os.listdir(temp_dir)) == 0

def test_main_with_non_video_file(temp_dir):
    # Create a non-video file
    text_file = os.path.join(temp_dir, 'test.txt')
    with open(text_file, 'w') as f:
        f.write('test content')
    
    main(temp_dir, True)
    assert os.path.exists(text_file)

def setup_test_video(temp_dir, video_path):
    """Set up a clean test directory with a single video"""
    # Create a clean test directory
    test_dir = os.path.join(temp_dir, 'test_video')
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # Create a clean copy of the test video
    test_video = os.path.join(test_dir, os.path.basename(video_path))
    shutil.copy2(video_path, test_video)
    
    # Clean any potential temporary files
    temp_mkv = os.path.splitext(test_video)[0] + '.temp.mkv'
    output_mkv = os.path.splitext(test_video)[0] + '.mkv'
    for path in [temp_mkv, output_mkv]:
        if os.path.exists(path):
            os.remove(path)
            
    return test_dir, test_video

def test_transcode_h264(temp_dir, sample_videos):
    # Set up isolated test environment
    test_dir, video_path = setup_test_video(temp_dir, sample_videos['h264_aac'])
    
    main(test_dir, True)
    # Check that original file exists (keep_original=True)
    assert os.path.exists(video_path)
    # Check that output file is created with .mkv extension
    output_path = os.path.splitext(video_path)[0] + '.mkv'
    assert os.path.exists(output_path)

def test_transcode_webm(temp_dir, sample_videos):
    # Set up isolated test environment
    test_dir, video_path = setup_test_video(temp_dir, sample_videos['vp8_vorbis'])
    
    main(test_dir, False)
    # Original file should be deleted (keep_original=False)
    assert not os.path.exists(video_path)
    # Check that output file is created with .mkv extension
    output_path = os.path.splitext(video_path)[0] + '.mkv'
    assert os.path.exists(output_path)

def test_transcode_avi(temp_dir, sample_videos):
    # Set up isolated test environment
    test_dir, video_path = setup_test_video(temp_dir, sample_videos['mpeg4_mp3'])
    
    main(test_dir, False)
    # Check conversion from AVI (MPEG4+MP3) to MKV (HEVC+AAC)
    assert not os.path.exists(video_path)  # Original deleted
    output_path = os.path.splitext(video_path)[0] + '.mkv'
    assert os.path.exists(output_path)

def test_main_nested_folders(temp_dir, sample_videos):
    # Create test directory with nested structure
    test_dir = os.path.join(temp_dir, 'nested_test')
    nested_dir = os.path.join(test_dir, 'nested', 'folders')
    os.makedirs(nested_dir, exist_ok=True)
    
    # Copy a test video to nested folder
    nested_video = os.path.join(nested_dir, 'test.mp4')
    shutil.copy2(sample_videos['h264_aac'], nested_video)
    
    main(test_dir, True)
    assert os.path.exists(nested_video)
