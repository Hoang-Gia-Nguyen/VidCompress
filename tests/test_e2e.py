import pytest
import os
import shutil
import time
from pathlib import Path

# Ensure the project root is on sys.path for imports
import allure
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vidcompress import get_media_info

@allure.feature("FR-TRANSCODE-001")
@allure.story("Transcode H.264 to H.265 (HEVC)")
@allure.testcase("FR-TRANSCODE-001", "Requirement FR-TRANSCODE-001")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.use_case_testing
@pytest.mark.FR_TRANSCODE_001
def test_e2e_transcode_h264_to_h265(setup_test_video, run_vidcompress_cli):
    """Given an H.264 MP4 file, When transcoded to H.265 MP4 (keep original), Then a new H.265 MP4 file is created and original is kept."""
    test_dir, original_video_path = setup_test_video('h264_sample.mp4')
    
    process = run_vidcompress_cli(test_dir, keep_original=True, video_codec='h.265', container='mp4')
    
    assert process.returncode == 0, f"CLI failed with errors: {process.stderr}"
    assert original_video_path.exists(), "Original file should be kept"
    
    output_path = original_video_path.parent / f"{original_video_path.stem}_re-encoded.mp4"
    assert output_path.exists(), "Re-encoded file should exist"
    
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
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.use_case_testing
@pytest.mark.FR_REMUX_001
def test_e2e_remux_mkv_to_mp4(setup_test_video, run_vidcompress_cli):
    """Given an H.264 MKV file, When remuxed to MP4 (keep original), Then a new H.264 MP4 file is created and original is kept."""
    test_dir, original_video_path = setup_test_video('h264_mkv_sample.mkv')
    
    process = run_vidcompress_cli(test_dir, keep_original=True, video_codec='h.264', container='mp4')
    
    assert process.returncode == 0, f"CLI failed with errors: {process.stderr}"
    assert original_video_path.exists(), "Original file should be kept"
    
    output_path = original_video_path.parent / f"{original_video_path.stem}_remuxed.mp4"
    assert output_path.exists(), "Remuxed file should exist"
    
    media_info = get_media_info(str(output_path))
    assert media_info is not None
    video_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'video'), None)
    audio_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'audio'), None)
    
    assert video_stream['codec_name'] == 'h264'
    assert audio_stream['codec_name'] == 'aac'
    assert audio_stream['channels'] == 2
    assert 'mp4' in media_info['format']['format_name']
    os.remove(output_path)

@allure.feature("FR-KEEP-ORIGINAL-001")
@allure.story("Keep Original File")
@allure.testcase("FR-KEEP-ORIGINAL-001", "Requirement FR-KEEP-ORIGINAL-001")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.use_case_testing
@pytest.mark.FR_KEEP_ORIGINAL_001
def test_e2e_keep_original_flag(setup_test_video, run_vidcompress_cli):
    """Given a video file, When transcoded with --keep-original, Then the original file remains and a new transcoded file is created."""
    test_dir, original_video_path = setup_test_video('h264_sample.mp4')
    
    process = run_vidcompress_cli(test_dir, keep_original=True, video_codec='h.265', container='mp4')
    
    assert process.returncode == 0, f"CLI failed with errors: {process.stderr}"
    assert original_video_path.exists(), "Original file should be kept"
    
    output_path = original_video_path.parent / f"{original_video_path.stem}_re-encoded.mp4"
    assert output_path.exists(), "Re-encoded file should exist"

@allure.feature("FR-ERROR-001")
@allure.story("Handle Invalid Input Path")
@allure.testcase("FR-ERROR-001", "Requirement FR-ERROR-001")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.use_case_testing
@pytest.mark.FR_ERROR_001
def test_e2e_invalid_input_path(run_vidcompress_cli):
    """Given an invalid folder path, When the script is run, Then it should exit with an error and a non-zero status."""
    invalid_path = "/this/path/does/not/exist/12345"
    process = run_vidcompress_cli(invalid_path)
    
    assert process.returncode != 0, "CLI should exit with a non-zero status for invalid path"
    assert "Error: No such file or directory" in process.stderr, "Error message should indicate invalid path"

@allure.feature("NFR-PERF-001")
@allure.story("Transcoding Performance")
@allure.testcase("NFR-PERF-001", "Requirement NFR-PERF-001")
@pytest.mark.e2e
@pytest.mark.non_functional
@pytest.mark.performance
@pytest.mark.NFR_PERF_001
def test_e2e_transcoding_performance(setup_test_video, run_vidcompress_cli):
    """Given a 1-minute H.264 video, When transcoded to H.265, Then it should complete within a specified time limit."""
    # Use a longer video for performance testing if available, or create one.
    # For now, using the 1-second sample, but note for real performance testing.
    test_dir, original_video_path = setup_test_video('h264_sample.mp4')
    
    start_time = time.time()
    process = run_vidcompress_cli(test_dir, keep_original=False, video_codec='h.265', container='mp4')
    end_time = time.time()
    
    assert process.returncode == 0, f"CLI failed with errors: {process.stderr}"
    
    duration = end_time - start_time
    # This threshold needs to be adjusted based on actual CI runner performance
    # For a 1-second video, 5 seconds is a very generous upper bound.
    # For a 1-minute video, 30 seconds (NFR-PERF-001) would be the target.
    expected_max_duration_seconds = 5 # Placeholder, adjust for actual 1-min video
    assert duration < expected_max_duration_seconds, f"Transcoding took too long: {duration:.2f}s (expected < {expected_max_duration_seconds}s)"
    
    # Verify output file exists and is transcoded
    output_path = original_video_path.parent / f"{original_video_path.stem}.mp4"
    assert output_path.exists()
    media_info = get_media_info(str(output_path))
    assert media_info['streams'][0]['codec_name'] == 'hevc'

@allure.feature("NFR-RELIABILITY-001")
@allure.story("Robustness to Corrupted Files")
@allure.testcase("NFR-RELIABILITY-001", "Requirement NFR-RELIABILITY-001")
@pytest.mark.e2e
@pytest.mark.non_functional
@pytest.mark.reliability
@pytest.mark.NFR_RELIABILITY_001
def test_e2e_corrupted_file_handling(setup_test_video, run_vidcompress_cli):
    """Given a corrupted video file, When the script processes it, Then it should skip the file and not crash."""
    test_dir, corrupted_file_path = setup_test_video('corrupted_video.mp4')
    
    process = run_vidcompress_cli(test_dir, keep_original=True, video_codec='h.265', container='mp4')
    
    assert process.returncode == 0, f"CLI should not crash, but exited with error: {process.stderr}"
    assert f"Failed to get media info for {corrupted_file_path}. Skipping." in process.stderr, "Script should indicate failure to process corrupted file"
    assert corrupted_file_path.exists(), "Corrupted file should not be deleted"
    
    # Ensure no output file was created for the corrupted input
    output_path = corrupted_file_path.parent / f"{corrupted_file_path.stem}_re-encoded.mp4"
    assert not output_path.exists(), "No output file should be created for corrupted input"

@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.state_transition_testing
def test_e2e_state_transitions(temp_dir, run_vidcompress_cli, setup_test_video):
    """Test various state transitions of a file (e.g., H264->H265, then H265->VP9)."""
    # Initial state: H.264 MP4
    test_dir, video_path = setup_test_video('h264_sample.mp4')
    initial_path = video_path

    # Transition 1: H.264 MP4 -> H.265 MP4 (re-encode)
    print(f"\n--- Transition 1: {initial_path.name} (H264) -> H265 MP4 ---")
    process1 = run_vidcompress_cli(test_dir, keep_original=False, video_codec='h.265', container='mp4')
    assert process1.returncode == 0, f"Transition 1 failed: {process1.stderr}"
    time.sleep(0.1)
    assert initial_path.exists(), "Original H264 file should be overwritten and exist"
    current_path = test_dir / f"{initial_path.stem}.mp4"
    assert current_path.exists(), "H265 MP4 file should exist"
    info1 = get_media_info(str(current_path))
    assert info1['streams'][0]['codec_name'] == 'hevc'
    assert 'mp4' in info1['format']['format_name']

    # Transition 2: H.265 MP4 -> VP9 MKV (re-encode)
    print(f"\n--- Transition 2: {current_path.name} (H265) -> VP9 MKV ---")
    # Rename the current file to a new name for the next step to avoid conflicts
    # and simulate processing a file that is now in the H265 MP4 state.
    # In a real scenario, the script would pick up the existing file.
    # For this test, we ensure the file is picked up correctly.
    # The script processes files in place if keep_original is False.
    process2 = run_vidcompress_cli(test_dir, keep_original=False, video_codec='vp9', container='mkv')
    assert process2.returncode == 0, f"Transition 2 failed: {process2.stderr}"
    assert not current_path.exists(), "H265 MP4 file should be deleted"
    final_path = test_dir / f"{initial_path.stem}.mkv"
    assert final_path.exists(), "VP9 MKV file should exist"
    info2 = get_media_info(str(final_path))
    assert info2['streams'][0]['codec_name'] == 'vp9'
    assert 'matroska' in info2['format']['format_name']

    # Transition 3: VP9 MKV -> H.265 MP4 (re-encode)
    print(f"\n--- Transition 3: {final_path.name} (VP9) -> H265 MP4 ---")
    process3 = run_vidcompress_cli(test_dir, keep_original=False, video_codec='h.265', container='mp4')
    assert process3.returncode == 0, f"Transition 3 failed: {process3.stderr}"
    assert not final_path.exists(), "VP9 MKV file should be deleted"
    final_path_again = test_dir / f"{initial_path.stem}.mp4"
    assert final_path_again.exists(), "H265 MP4 file should exist again"
    info3 = get_media_info(str(final_path_again))
    assert info3['streams'][0]['codec_name'] == 'hevc'
    assert 'mp4' in info3['format']['format_name']

@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.checklist_based_testing
def test_e2e_all_codec_container_combinations(temp_dir, run_vidcompress_cli, test_data_dir):
    """Check all specified codec and container combinations for transcoding/remuxing."""
    # Define test cases: (input_file, target_video_codec, target_container, expected_output_codec, expected_output_container_part)
    test_cases = [
        # Transcoding scenarios
        ('h264_sample.mp4', 'h.265', 'mp4', 'hevc', 'mp4'), # FR-TRANSCODE-001
        ('h264_sample.mp4', 'h.264', 'mkv', 'h264', 'matroska'), # Change container, keep codec
        ('h265_sample.mkv', 'h.264', 'mp4', 'h264', 'mp4'),
        ('vp9_sample.webm', 'h.265', 'mp4', 'hevc', 'mp4'),

        # Remuxing scenarios (codecs compatible, only container changes)
        ('h264_mkv_sample.mkv', 'h.264', 'mp4', 'h264', 'mp4'), # FR-REMUX-001
        ('h265_sample.mkv', 'h.265', 'mp4', 'hevc', 'mp4'), # H.265 MKV to H.265 MP4

        # Skip scenarios (already in target format)
        ('h264_sample.mp4', 'h.264', 'mp4', 'h264', 'mp4'), # Already H.264 MP4
        ('h265_sample.mkv', 'h.265', 'mkv', 'hevc', 'matroska'), # Already H.265 MKV
    ]

    for i, (input_filename, target_vcodec, target_container, expected_vcodec, expected_container_part) in enumerate(test_cases):
        print(f"\n--- Test Case {i+1}: {input_filename} -> {target_vcodec}/{target_container} ---")
        
        # Create a fresh temp directory for each test case to ensure isolation
        case_temp_dir = temp_dir / f"case_{i}"
        case_temp_dir.mkdir()

        source_video_path = test_data_dir / input_filename
        current_video_path = case_temp_dir / input_filename
        shutil.copy2(source_video_path, current_video_path)

        # Determine expected output path based on keep_original=False for simplicity
        expected_output_path = case_temp_dir / f"{Path(input_filename).stem}.{target_container}"

        # Run the CLI command
        process = run_vidcompress_cli(case_temp_dir, keep_original=False, 
                                      video_codec=target_vcodec, container=target_container)
        
        assert process.returncode == 0, f"Test Case {i+1} failed for {input_filename} -> {target_vcodec}/{target_container}: {process.stderr}"

        # Check if the file was skipped (i.e., no new file created, original still exists and is correct)
        if f"Skipping {current_video_path.name}" in process.stdout:
            assert current_video_path.exists(), "Original file should exist if skipped"
            info = get_media_info(str(current_video_path))
            assert info['streams'][0]['codec_name'] == expected_vcodec
            assert expected_container_part in info['format']['format_name']
            assert not expected_output_path.exists() or expected_output_path == current_video_path, "No new file should be created if skipped"
        else:
            # If not skipped, handle overwritten vs. new file creation
            if current_video_path == expected_output_path:
                # Scenario: Original file is overwritten (same name, different codec)
                assert current_video_path.exists(), "Overwritten file should exist"
            else:
                # Scenario: New file is created, original is deleted (different name/container)
                assert not current_video_path.exists(), "Original file should be deleted if processed"
                assert expected_output_path.exists(), "Output file should exist"
            
            media_info = get_media_info(str(expected_output_path))
            assert media_info is not None, f"Failed to get media info for {expected_output_path}"
            video_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'video'), None)
            audio_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'audio'), None)
            
            assert video_stream['codec_name'] == expected_vcodec, f"Expected video codec {expected_vcodec}, got {video_stream['codec_name']}"
            assert audio_stream['codec_name'] == 'aac', f"Expected audio codec aac, got {audio_stream['codec_name']}"
            assert audio_stream['channels'] == 2, f"Expected 2 audio channels, got {audio_stream['channels']}"
            assert expected_container_part in media_info['format']['format_name'], f"Expected container part {expected_container_part}, got {media_info['format']['format_name']}"
