import pytest
import os
import tempfile
import shutil
import subprocess
import json
import sys
import time
from pathlib import Path
import allure
import allure

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vidcompress import main, get_media_info

# Fixtures from conftest.py are automatically available

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

@allure.feature("General Functionality")
@allure.story("Process Empty Folder")
@pytest.mark.integration
@pytest.mark.functional
@pytest.mark.use_case_testing
def test_main_empty_folder(temp_dir):
    main(temp_dir, True, 'h.265', 'mkv')
    assert len(os.listdir(temp_dir)) == 0

@allure.feature("General Functionality")
@allure.story("Process Folder with Non-Video Files")
@pytest.mark.integration
@pytest.mark.functional
@pytest.mark.use_case_testing
def test_main_with_non_video_file(temp_dir):
    # Create a non-video file
    text_file = os.path.join(temp_dir, 'test.txt')
    with open(text_file, 'w') as f:
        f.write('test content')

    main(temp_dir, True, 'h.265', 'mkv')
    assert os.path.exists(text_file)

@pytest.mark.integration
@pytest.mark.functional
@pytest.mark.FR_TRANSCODE_001
@pytest.mark.use_case_testing
def test_transcode_h264_to_h265(setup_test_video):
    # Set up isolated test environment with h264_sample.mp4
    test_dir, original_video_path = setup_test_video('h264_sample.mp4')
    
    main(test_dir, True, 'h.265', 'mp4') # Transcode to h.265, keep original, output mp4
    
    # Check that original file exists (keep_original=True)
    assert original_video_path.exists()
    
    # Check that output file is created with _re-encoded suffix
    output_path = original_video_path.parent / f"{original_video_path.stem}_re-encoded.mp4"
    assert output_path.exists()
    
    # Verify output video codec and container
    media_info = get_media_info(str(output_path))
    assert media_info is not None
    video_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'video'), None)
    audio_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'audio'), None)
    
    assert video_stream['codec_name'] == 'hevc'
    assert audio_stream['codec_name'] == 'aac'
    assert audio_stream['channels'] == 2
    assert 'mp4' in media_info['format']['format_name']

@allure.feature("FR-REMUX-001")
@allure.story("Remux MKV to MP4 (same codecs)")
@allure.testcase("FR-REMUX-001", "Requirement FR-REMUX-001")
@pytest.mark.integration
@pytest.mark.functional
@pytest.mark.FR_REMUX_001
@pytest.mark.use_case_testing
def test_remux_mkv_to_mp4(setup_test_video): 
    # Set up isolated test environment with h264_mkv_sample.mkv
    test_dir, original_video_path = setup_test_video('h264_mkv_sample.mkv')
    
    main(test_dir, True, 'h.264', 'mp4') # Remux to mp4, keep original, video codec h.264 (compatible)
    
    # Check that original file exists (keep_original=True)
    assert original_video_path.exists()
    
    # Check that output file is created with _remuxed suffix
    output_path = original_video_path.parent / f"{original_video_path.stem}_remuxed.mp4"
    assert output_path.exists()
    
    # Verify output container and codecs (should be same as original)
    media_info = get_media_info(str(output_path))
    assert media_info is not None
    video_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'video'), None)
    audio_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'audio'), None)
    
    assert video_stream['codec_name'] == 'h264'
    assert audio_stream['codec_name'] == 'aac'
    assert audio_stream['channels'] == 2
    assert 'mp4' in media_info['format']['format_name']
    os.remove(output_path)

@allure.feature("Transcoding")
@allure.story("Transcode VP9 to H.265")
@pytest.mark.integration
@pytest.mark.functional
@pytest.mark.use_case_testing
def test_transcode_vp9_to_h265(setup_test_video):
    # Set up isolated test environment with vp9_sample.webm
    test_dir, original_video_path = setup_test_video('vp9_sample.webm')
    
    main(test_dir, False, 'h.265', 'mp4') # Transcode to h.265, delete original, output mp4
    
    # Original file should NOT exist
    assert not original_video_path.exists()
    
    # Output file should exist at original path (since keep_original=False)
    output_path = original_video_path.parent / f"{original_video_path.stem}.mp4"
    assert output_path.exists()
    
    # Verify output video codec and container
    media_info = get_media_info(str(output_path))
    assert media_info is not None
    video_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'video'), None)
    audio_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'audio'), None)
    
    assert video_stream['codec_name'] == 'hevc'
    assert audio_stream['codec_name'] == 'aac'
    assert audio_stream['channels'] == 2
    assert 'mp4' in media_info['format']['format_name']

@allure.feature("File System Handling")
@allure.story("Process Files in Nested Folders")
@pytest.mark.integration
@pytest.mark.functional
@pytest.mark.use_case_testing
def test_main_nested_folders(temp_dir, test_data_dir):
    # Create test directory with nested structure
    test_dir_root = temp_dir / 'nested_test'
    nested_dir = test_dir_root / 'nested' / 'folders'
    nested_dir.mkdir(parents=True, exist_ok=True)
    
    # Directly copy a test video to the nested folder
    source_video_path = test_data_dir / 'h264_sample.mp4'
    target_nested_video_path = nested_dir / 'h264_sample.mp4'
    shutil.copy2(source_video_path, target_nested_video_path)
    
    main(str(test_dir_root), True, 'h.265', 'mp4')
    
    # Original should still exist
    assert target_nested_video_path.exists()
    # Re-encoded should exist in the same nested folder
    re_encoded_path = nested_dir / f"{target_nested_video_path.stem}_re-encoded.mp4"
    assert re_encoded_path.exists()

@allure.feature("Decision Logic")
@allure.story("Decision Table Scenarios")
@pytest.mark.integration
@pytest.mark.functional
@pytest.mark.decision_table_testing
def test_main_decision_table_scenarios(temp_dir, setup_test_video):
    # Scenario 1: Codecs match, Container different -> Remux
    test_dir_remux, original_remux_path = setup_test_video('h265_sample.mkv')
    main(str(test_dir_remux), False, 'h.265', 'mp4') # Target: H.265, MP4
    assert not original_remux_path.exists() # Original deleted
    remuxed_path = test_dir_remux / f"{original_remux_path.stem}.mp4"
    assert remuxed_path.exists() # Remuxed file exists
    info = get_media_info(str(remuxed_path))
    assert info['streams'][0]['codec_name'] == 'hevc'
    assert 'mp4' in info['format']['format_name']
    os.remove(remuxed_path)

    # Scenario 2: Codecs different, Container same -> Transcode
    test_dir_transcode, original_transcode_path = setup_test_video('h264_sample.mp4')
    main(str(test_dir_transcode), False, 'vp9', 'mp4') # Target: VP9, MP4
    transcoded_path = test_dir_transcode / f"{original_transcode_path.stem}.mp4"
    assert transcoded_path.exists() # Transcoded file exists
    info = get_media_info(str(transcoded_path))
    assert info['streams'][0]['codec_name'] == 'vp9'
    assert 'mp4' in info['format']['format_name']
    os.remove(transcoded_path)

    # Scenario 3: Codecs different, Container different -> Transcode
    test_dir_full, original_full_path = setup_test_video('vp9_sample.webm')
    main(str(test_dir_full), False, 'h.264', 'mp4') # Target: H.264, MP4
    assert not original_full_path.exists() # Original deleted
    full_output_path = test_dir_full / f"{original_full_path.stem}.mp4"
    assert full_output_path.exists() # Transcoded file exists
    info = get_media_info(str(full_output_path))
    assert info['streams'][0]['codec_name'] == 'h264'
    assert 'mp4' in info['format']['format_name']
    os.remove(full_output_path)

    # Scenario 4: Already correct format -> Skip
    test_dir_skip, original_skip_path = setup_test_video('h265_sample.mkv')
    # Manually set it to be already in the target format for skipping
    # For this test, let's assume h265_sample.mkv is already h265/aac/mkv
    # and we target h265/aac/mkv
    main(str(test_dir_skip), True, 'h.265', 'mkv') # Target: H.265, MKV
    assert original_skip_path.exists() # Original still exists
    # No new file should be created, only the original should be there
    print(f"Contents of {test_dir_skip}: {[f.name for f in test_dir_skip.iterdir()]}")
    assert len(list(test_dir_skip.iterdir())) == 1


