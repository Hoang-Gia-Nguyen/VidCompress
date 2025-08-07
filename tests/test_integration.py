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

def clean_temp_files(path):
    """Clean up any temporary files from failed tests"""
    temp_path = os.path.splitext(path)[0] + '.temp.mkv'
    if os.path.exists(temp_path):
        os.remove(temp_path)

def create_test_video(temp_dir, filename, video_codec, audio_codec, container):
    """Helper function to create test videos with different codecs"""
    import subprocess
    video_path = os.path.join(temp_dir, f'test_{filename}.{container}')
    # Clean any existing temporary files first
    clean_temp_files(video_path)
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
    videos = {
        'h264_aac': create_test_video(temp_dir, 'h264_aac', 'libx264', 'aac', 'mp4'),
        'vp8_vorbis': create_test_video(temp_dir, 'vp8_vorbis', 'libvpx', 'libvorbis', 'webm'),
        'mpeg4_mp3': create_test_video(temp_dir, 'mpeg4_mp3', 'mpeg4', 'libmp3lame', 'avi'),
        'multi_audio': create_test_video(temp_dir, 'multi_audio', 'libx264', 'aac', 'mkv')  # will add multiple audio tracks
    }
    
    # Add a second audio track to the multi_audio test
    subprocess.run([
        'ffmpeg', '-y',
        '-i', videos['multi_audio'],
        '-f', 'lavfi',
        '-i', 'sine=frequency=880:duration=1',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-ac', '2',
        '-map', '0:v:0',
        '-map', '0:a:0',
        '-map', '1:a:0',
        os.path.join(temp_dir, 'temp.mkv')
    ], check=True, capture_output=True)
    
    import shutil
    shutil.move(os.path.join(temp_dir, 'temp.mkv'), videos['multi_audio'])
    
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

def test_transcode_h264(temp_dir, sample_videos):
    video_path = sample_videos['h264_aac']
    clean_temp_files(video_path)  # Clean any leftover temp files
    main(temp_dir, True)
    # Check that original file exists (keep_original=True)
    assert os.path.exists(video_path)
    # Check that output file is created with .mkv extension
    output_path = os.path.splitext(video_path)[0] + '.mkv'
    assert os.path.exists(output_path)

def test_transcode_webm(temp_dir, sample_videos):
    video_path = sample_videos['vp8_vorbis']
    clean_temp_files(video_path)  # Clean any leftover temp files
    main(temp_dir, False)
    # Original file should be deleted (keep_original=False)
    assert not os.path.exists(video_path)
    # Check that output file is created with .mkv extension
    output_path = os.path.splitext(video_path)[0] + '.mkv'
    assert os.path.exists(output_path)

def test_transcode_avi(temp_dir, sample_videos):
    video_path = sample_videos['mpeg4_mp3']
    clean_temp_files(video_path)  # Clean any leftover temp files
    main(temp_dir, False)
    # Check conversion from AVI (MPEG4+MP3) to MKV (HEVC+AAC)
    assert not os.path.exists(video_path)  # Original deleted
    output_path = os.path.splitext(video_path)[0] + '.mkv'
    assert os.path.exists(output_path)

def test_multi_audio_tracks(temp_dir, sample_videos):
    video_path = sample_videos['multi_audio']
    clean_temp_files(video_path)  # Clean any leftover temp files
    main(temp_dir, True)
    # Test handling of multiple audio tracks
    output_path = video_path  # Since input is already .mkv
    assert os.path.exists(output_path)
    
    # Verify the output has correct format using ffprobe
    import json
    result = subprocess.run([
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        output_path
    ], capture_output=True, text=True)
    
    info = json.loads(result.stdout)
    audio_streams = [s for s in info['streams'] if s['codec_type'] == 'audio']
    assert len(audio_streams) == 1  # Should be consolidated to one stereo track
    assert audio_streams[0]['codec_name'] == 'aac'
    assert audio_streams[0]['channels'] == 2

def test_main_nested_folders(temp_dir, sample_videos):
    # Create nested directory structure
    nested_dir = os.path.join(temp_dir, 'nested', 'folders')
    os.makedirs(nested_dir)
    
    # Copy a test video to nested folder
    import shutil
    nested_video = os.path.join(nested_dir, 'test.mp4')
    shutil.copy2(sample_videos['h264_aac'], nested_video)
    
    # Clean any leftover temp files
    clean_temp_files(nested_video)
    
    main(temp_dir, True)
    assert os.path.exists(nested_video)
