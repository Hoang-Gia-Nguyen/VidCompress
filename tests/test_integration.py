import pytest
import os
import tempfile
import shutil
from pathlib import Path
from vidcompress import main

@pytest.fixture
def temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_video(temp_dir):
    # Create a valid test video file using FFmpeg
    video_path = os.path.join(temp_dir, 'test.mp4')
    import subprocess
    # Create a 1-second test video
    subprocess.run([
        'ffmpeg', '-y',
        '-f', 'lavfi',
        '-i', 'testsrc=duration=1:size=320x240:rate=30',
        '-c:v', 'libx264',
        video_path
    ], check=True, capture_output=True)
    return video_path

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

def test_main_keep_original(temp_dir, sample_video):
    main(temp_dir, True)
    assert os.path.exists(sample_video)

def test_main_delete_original(temp_dir, sample_video):
    # Note: This test might fail if the video can't be transcoded
    # due to the dummy content
    main(temp_dir, False)
    assert not os.path.exists(sample_video)

def test_main_nested_folders(temp_dir):
    # Create nested directory structure
    nested_dir = os.path.join(temp_dir, 'nested', 'folders')
    os.makedirs(nested_dir)
    
    video_path = os.path.join(nested_dir, 'test.mp4')
    with open(video_path, 'wb') as f:
        f.write(b'dummy video content')
    
    main(temp_dir, True)
    assert os.path.exists(video_path)
