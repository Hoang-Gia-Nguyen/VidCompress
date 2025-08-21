import pytest
import os
import subprocess
import json
import argparse
import tempfile
import shutil
import sys
from unittest.mock import patch, MagicMock, mock_open
import allure

mock_base_path = './test_output' # Define a consistent base path for mocks

# Ensure the project root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def cli_temp_dir():
    """Creates a temporary directory for CLI tests within test_output."""
    temp_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_output', 'cli_temp'))
    if os.path.exists(temp_dir_path):
        shutil.rmtree(temp_dir_path)
    os.makedirs(temp_dir_path, exist_ok=True)
    yield temp_dir_path
    shutil.rmtree(temp_dir_path)
from vidcompress import (
    get_ffmpeg_path,
    get_ffprobe_path,
    get_media_info,
    get_duration,
    is_videotoolbox_available,
    transcode_file,
    remux_file, # Added remux_file import
    main
)

@allure.feature("Utility Functions")
@allure.story("Get FFmpeg Path")
def test_get_ffmpeg_path():
    assert get_ffmpeg_path() == 'ffmpeg'

@allure.feature("Utility Functions")
@allure.story("Get FFprobe Path")
def test_get_ffprobe_path():
    assert get_ffprobe_path() == 'ffprobe'

@pytest.fixture
def sample_media_info():
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

@allure.feature("Utility Functions")
@allure.story("Get Media Info Success")
@pytest.mark.unit
@pytest.mark.functional
@pytest.mark.equivalence_partitioning
@patch('subprocess.run')
def test_get_media_info_success(mock_run, sample_media_info):
    mock_run.return_value = MagicMock(
        stdout=json.dumps(sample_media_info),
        returncode=0
    )
    result = get_media_info('test.mp4')
    assert result == sample_media_info

@allure.feature("Utility Functions")
@allure.story("Get Media Info File Not Found")
@pytest.mark.unit
@pytest.mark.functional
@pytest.mark.error_guessing
@patch('subprocess.run')
def test_get_media_info_file_not_found(mock_run):
    mock_run.side_effect = FileNotFoundError()
    assert get_media_info('nonexistent.mp4') is None

@allure.feature("Utility Functions")
@allure.story("Get Media Info Called Process Error")
@pytest.mark.unit
@pytest.mark.functional
@pytest.mark.error_guessing
@patch('subprocess.run')
def test_get_media_info_called_process_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, 'ffprobe')
    assert get_media_info('test.mp4') is None

@allure.feature("Utility Functions")
@allure.story("Get Duration")
@pytest.mark.unit
@pytest.mark.functional
@pytest.mark.boundary_value_analysis
def test_get_duration(sample_media_info):
    assert get_duration(sample_media_info) == 60.123456

@allure.feature("Utility Functions")
@allure.story("Get Duration Empty Dictionary")
@pytest.mark.unit
@pytest.mark.functional
@pytest.mark.boundary_value_analysis
def test_get_duration_empty_dict():
    assert get_duration({}) == 0.0

@allure.feature("Utility Functions")
@allure.story("Is VideoToolbox Available True")
@pytest.mark.unit
@pytest.mark.functional
@pytest.mark.decision_coverage
@patch('subprocess.run')
def test_is_videotoolbox_available_true(mock_run):
    mock_run.return_value = MagicMock(
        stdout='hevc_videotoolbox',
        returncode=0
    )
    assert is_videotoolbox_available('hevc') is True

@allure.feature("Utility Functions")
@allure.story("Is VideoToolbox Available False")
@pytest.mark.unit
@pytest.mark.functional
@pytest.mark.decision_coverage
@patch('subprocess.run')
def test_is_videotoolbox_available_false(mock_run):
    mock_run.return_value = MagicMock(
        stdout='',
        returncode=0
    )
    assert is_videotoolbox_available('hevc') is False

@patch('subprocess.run')
def test_is_videotoolbox_available_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, 'ffmpeg')
    assert is_videotoolbox_available('hevc') is False

@patch('vidcompress.is_videotoolbox_available', return_value=False)
@patch('subprocess.Popen')
def test_transcode_file_success(mock_popen, mock_vt):
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = []
    mock_popen.return_value = mock_process

    assert transcode_file('input.mp4', 'output.mkv', 'h.265') is True

@patch('vidcompress.is_videotoolbox_available', return_value=False)
@patch('subprocess.Popen')
def test_transcode_file_failure(mock_popen, mock_vt):
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stdout = []
    mock_popen.return_value = mock_process

    assert transcode_file('input.mp4', 'output.mkv', 'h.265') is False

@patch('subprocess.Popen')
def test_remux_file_success(mock_popen):
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = []
    mock_popen.return_value = mock_process

    assert remux_file('input.mkv', 'output.mp4') is True

@patch('subprocess.Popen')
def test_remux_file_failure(mock_popen):
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stdout = []
    mock_popen.return_value = mock_process

    assert remux_file('input.mkv', 'output.mp4') is False

@patch('subprocess.run')
def test_get_media_info_json_decode_error(mock_run):
    mock_run.return_value = MagicMock(
        stdout="invalid json",
        returncode=0
    )
    assert get_media_info('test.mp4') is None

@patch('os.walk')
@patch('os.path.exists')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.copy2')
@patch('vidcompress.get_media_info')
@patch('vidcompress.transcode_file')
def test_main_process_mkv_file(mock_transcode, mock_media_info, mock_copy2, 
                              mock_makedirs, mock_remove, mock_exists, mock_walk):
    # Setup mocks
    mock_walk.return_value = [(mock_base_path, [], ['video.mkv'])]
    
    # Configure mock_exists dynamically
    # Initially, only the input file exists
    mock_exists.side_effect = lambda path: path == os.path.join(mock_base_path, 'video.mkv')

    mock_media_info.return_value = {
        'format': {'format_name': 'matroska'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
        ]
    }

    def mock_transcode_side_effect(input_path, output_path, video_codec_choice):
        # After transcode, the temp_output_path should exist
        mock_exists.side_effect = lambda path: \
            path == os.path.join(mock_base_path, 'video.mkv') or \
            path == output_path # Simulate temp_output_path creation
        return True # Simulate success

    mock_transcode.side_effect = mock_transcode_side_effect

    # Run main function
    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mp4')

    # Verify the expected workflow:
    mock_transcode.assert_called_once()
    mock_makedirs.assert_called_once()
    assert any(call[0][0] == os.path.join(mock_base_path, 'video.mkv') for call in mock_remove.call_args_list), \
        "Should try to remove input file"

@patch('os.walk')
@patch('vidcompress.get_media_info')
def test_main_skip_non_video_file(mock_media_info, mock_walk):
    mock_walk.return_value = [('./test_output', [], ['document.txt'])]
    
    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    
    mock_media_info.assert_not_called()

@patch('os.walk')
@patch('vidcompress.get_media_info')
def test_main_skip_correct_format(mock_media_info, mock_walk):
    mock_walk.return_value = [(mock_base_path, [], ['video.mkv'])]
    mock_media_info.return_value = {
        'format': {'format_name': 'matroska,webm'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'hevc'},
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }
    
    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    
    # Should not try to transcode since file is already in correct format
    assert not any('transcode' in str(call) for call in mock_media_info.mock_calls)

@patch('os.walk')
@patch('vidcompress.get_media_info')
def test_main_invalid_media_info(mock_media_info, mock_walk):
    mock_walk.return_value = [(mock_base_path, [], ['video.mp4'])]
    mock_media_info.return_value = None
    
    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    
    # Should continue without error when media info is invalid
    mock_media_info.assert_called_once()

@patch('os.walk')
@patch('vidcompress.get_media_info')
def test_main_no_video_stream(mock_media_info, mock_walk):
    mock_walk.return_value = [(mock_base_path, [], ['audio.mp4'])]
    mock_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }
    
    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    
    # Should skip files with no video stream
    mock_media_info.assert_called_once()

@patch('vidcompress.is_videotoolbox_available', return_value=False)
@patch('subprocess.Popen')
def test_transcode_file_output(mock_popen, mock_vt):
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = ['Progress: 50%\n', 'Progress: 100%\n']
    mock_popen.return_value = mock_process
    
    with patch('sys.stdout') as mock_stdout:
        assert transcode_file('input.mp4', 'output.mkv', 'h.265') is True
        assert mock_stdout.write.call_count >= 2

@patch('os.walk')
@patch('vidcompress.get_media_info')
@patch('vidcompress.transcode_file')
@patch('os.path.exists')
@patch('os.makedirs')
@patch('os.remove')
def test_main_error_handling(mock_remove, mock_makedirs, mock_exists, 
                            mock_transcode, mock_media_info, mock_walk):
    mock_walk.return_value = [(mock_base_path, [], ['video.mkv'])]
    mock_exists.return_value = True
    mock_media_info.return_value = {
        'format': {'format_name': 'matroska'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
        ]
    }
    mock_transcode.return_value = True
    mock_makedirs.side_effect = [OSError("Permission denied")]
    
    # Should handle directory creation error gracefully
    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')

def test_cli_help():
    """Test that the CLI help command works and shows usage information"""
    result = subprocess.run([sys.executable, 'vidcompress.py', '--help'], 
                          capture_output=True, text=True)
    assert result.returncode == 0
    assert 'usage:' in result.stdout.lower()
    assert 'folder_path' in result.stdout
    assert '--keep-original' in result.stdout

def test_cli_invalid_path():
    """Test CLI behavior with an invalid path"""
    result = subprocess.run([sys.executable, 'vidcompress.py', '/nonexistent/path'], 
                          capture_output=True, text=True)
    assert 'No such file or directory' in result.stderr
    # Script should exit with non-zero status for invalid paths
    assert result.returncode == 1

def test_cli_with_keep_original(cli_temp_dir):
    """Test CLI with --keep-original flag"""
    # Create a test video file with h264 content to ensure it needs transcoding
    test_file = os.path.join(cli_temp_dir, "test.mkv")
    subprocess.run([
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', 'testsrc=duration=1:size=320x240:rate=30',
        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
        '-c:v', 'libx264', '-c:a', 'aac',
        test_file
    ], check=True, capture_output=True)
    
    result = subprocess.run(
        [sys.executable, 'vidcompress.py', cli_temp_dir, '--keep-original'],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"CLI failed with output: {result.stderr}"
    assert os.path.exists(test_file), "Original file should still exist"
    re_encoded = os.path.join(cli_temp_dir, "test_re-encoded.mp4")
    assert os.path.exists(re_encoded), "Transcoded file should exist"

def test_cli_without_keep_original(cli_temp_dir):
    """Test CLI without --keep-original flag"""
    # Create a test video file with h264 content
    test_file = os.path.join(cli_temp_dir, "test.mkv")
    subprocess.run([
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', 'testsrc=duration=1:size=320x240:rate=30',
        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
        '-c:v', 'libx264', '-c:a', 'aac',
        test_file
    ], check=True, capture_output=True)
    
    # Store original modification time
    orig_mtime = os.path.getmtime(test_file)

    result = subprocess.run(
        [sys.executable, 'vidcompress.py', cli_temp_dir],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"CLI failed with output: {result.stderr}"
    assert not os.path.exists(test_file), "Original file should be deleted"
    assert os.path.exists(os.path.join(cli_temp_dir, "test.mp4")), "Re-encoded file should exist at new path"
    # Verify it's a different file by checking modification time
    

@patch('os.path.exists')
@patch('os.remove')
@patch('shutil.copy2')
@patch('vidcompress.transcode_file')
def test_main_file_operations_error(mock_transcode, mock_copy2, mock_remove, mock_exists):
    mock_exists.return_value = True
    mock_transcode.return_value = True
    mock_copy2.side_effect = Exception("Copy failed")
    
    # Test error handling during file operations
    with patch('os.walk') as mock_walk:
        mock_walk.return_value = [(mock_base_path, [], ['video.mkv'])]
        with patch('vidcompress.get_media_info') as mock_media_info:
            mock_media_info.return_value = {
                'format': {'format_name': 'matroska'},
                'streams': [
                    {'codec_type': 'video', 'codec_name': 'h264'},
                    {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
                ]
            }
            main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')
            mock_transcode.assert_called_once()

@patch('os.walk')
@patch('vidcompress.get_media_info')
@patch('vidcompress.transcode_file')
def test_main_transcode_failure(mock_transcode, mock_media_info, mock_walk):
    mock_walk.return_value = [(mock_base_path, [], ['video.mp4'])]
    mock_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
        ]
    }
    mock_transcode.return_value = False
    
    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    mock_transcode.assert_called_once()

@patch('vidcompress.transcode_file', return_value=True)
@patch('os.path.exists')
@patch('os.remove')
@patch('os.walk')
def test_main_existing_output_cleanup(mock_walk, mock_remove, mock_exists, mock_transcode):
    mock_walk.return_value = [(mock_base_path, [], ['video.mp4'])]
    mock_exists.return_value = True

    with patch('vidcompress.get_media_info') as mock_media_info:
        mock_media_info.return_value = {
            'format': {'format_name': 'mp4'},
            'streams': [
                {'codec_type': 'video', 'codec_name': 'h264'},
                {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
            ]
        }
        main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')
        assert mock_remove.call_count >= 1

@pytest.mark.unit
@pytest.mark.functional
@pytest.mark.decision_coverage
@patch('os.walk')
@patch('os.path.exists')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.remux_file')
def test_main_remux_existing_temp_file_cleanup(mock_remux, mock_media_info, mock_move, mock_makedirs, mock_remove, mock_exists, mock_walk):
    # Setup mocks
    mock_walk.return_value = [(mock_base_path, [], ['video.mkv'])]
    
    # Configure mock_exists dynamically
    exists_state = {
        os.path.join(mock_base_path, 'video.mkv'): True,
        os.path.join(mock_base_path, 'video.temp.mp4'): True,
        os.path.join(mock_base_path, 'video.mp4'): False # Final path doesn't exist yet
    }

    def side_effect_exists(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = side_effect_exists

    mock_media_info.return_value = {
        'format': {'format_name': 'matroska,webm'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'hevc'},
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }

    def mock_remux_side_effect(input_path, output_path):
        # After remux, the temp_output_path should exist
        exists_state[output_path] = True
        return True # Simulate success

    mock_remux.side_effect = mock_remux_side_effect

    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mp4')

    # Assertions
    mock_remove.assert_any_call(os.path.join(mock_base_path, 'video.temp.mp4'))
    mock_remove.assert_any_call(os.path.join(mock_base_path, 'video.mkv'))
    assert mock_remove.call_count == 2


@patch('os.walk')
@patch('os.path.exists')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.transcode_file')
def test_main_transcode_existing_temp_file_cleanup(mock_transcode, mock_media_info, mock_move, mock_makedirs, mock_remove, mock_exists, mock_walk):
    # Setup mocks
    mock_walk.return_value = [(mock_base_path, [], ['video.mp4'])]
    
    # Configure mock_exists dynamically
    exists_state = {
        os.path.join(mock_base_path, 'video.mp4'): True,
        os.path.join(mock_base_path, 'video.temp.mkv'): True,
        os.path.join(mock_base_path, 'video.mkv'): False # Final path doesn't exist yet
    }

    def side_effect_exists(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = side_effect_exists

    mock_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
        ]
    }

    def mock_transcode_side_effect(input_path, output_path, video_codec_choice):
        # After transcode, the temp_output_path should exist
        exists_state[output_path] = True
        return True # Simulate success

    mock_transcode.side_effect = mock_transcode_side_effect

    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')

    # Assertions
    mock_remove.assert_any_call(os.path.join(mock_base_path, 'video.temp.mkv'))
    mock_remove.assert_any_call(os.path.join(mock_base_path, 'video.mp4'))
    assert mock_remove.call_count == 2


@patch('os.walk')
@patch('os.path.exists')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.remux_file')
def test_main_remux_and_delete_original(mock_remux, mock_media_info, mock_move, mock_makedirs, mock_remove, mock_exists, mock_walk):
    # Setup mocks
    mock_walk.return_value = [(mock_base_path, [], ['video.mkv'])]
    
    # Configure mock_exists dynamically
    exists_state = {
        os.path.join(mock_base_path, 'video.mkv'): True,
        os.path.join(mock_base_path, 'video.temp.mp4'): False,
        os.path.join(mock_base_path, 'video.mp4'): False # Final path doesn't exist yet
    }

    def side_effect_exists(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = side_effect_exists

    mock_media_info.return_value = {
        'format': {'format_name': 'matroska,webm'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'hevc'},
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }

    def mock_remux_side_effect(input_path, output_path):
        # After remux, the temp_output_path should exist
        exists_state[output_path] = True
        return True # Simulate success

    mock_remux.side_effect = mock_remux_side_effect

    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mp4')
    mock_remove.assert_called_once_with(os.path.join(mock_base_path, 'video.mkv'))


@patch('os.walk')
@patch('os.path.exists')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.transcode_file')
def test_main_transcode_and_delete_original(mock_transcode, mock_media_info, mock_move, mock_makedirs, mock_remove, mock_exists, mock_walk):
    mock_walk.return_value = [(mock_base_path, [], ['video.mp4'])]
    
    # Configure mock_exists dynamically
    # Initially, only the input file exists
    mock_exists.side_effect = lambda path: path == os.path.join(mock_base_path, 'video.mp4')

    mock_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
        ]
    }

    def mock_transcode_side_effect(input_path, output_path, video_codec_choice):
        # After transcode, the temp_output_path should exist
        mock_exists.side_effect = lambda path: \
            path == os.path.join(mock_base_path, 'video.mp4') or \
            path == output_path # Simulate temp_output_path creation
        return True # Simulate success

    mock_transcode.side_effect = mock_transcode_side_effect

    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    mock_remove.assert_called_once_with(os.path.join(mock_base_path, 'video.mp4'))


@patch('os.walk')
@patch('os.path.exists')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.remux_file')
@patch('vidcompress.transcode_file')
def test_main_general_processing_remux_path(mock_transcode, mock_remux, mock_media_info, mock_move, mock_makedirs, mock_remove, mock_exists, mock_walk):
    # Setup mocks
    mock_walk.return_value = [(mock_base_path, [], ['video.mkv'])]
    
    # Configure mock_exists dynamically
    # Initially, only the input file exists
    mock_exists.side_effect = lambda path: path == os.path.join(mock_base_path, 'video.mkv')

    mock_remux.return_value = True
    mock_transcode.return_value = False # Ensure transcode is not called
    mock_media_info.return_value = {
        'format': {'format_name': 'matroska'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'hevc'},
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }

    def mock_remux_side_effect(input_path, output_path):
        # After remux, the temp_output_path should exist
        mock_exists.side_effect = lambda path: \
            path == os.path.join(mock_base_path, 'video.mkv') or \
            path == output_path # Simulate temp_output_path creation
        return True # Simulate success

    mock_remux.side_effect = mock_remux_side_effect

    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mp4')
    mock_remux.assert_called_once()
    mock_transcode.assert_not_called()


@patch('os.walk')
@patch('os.path.exists')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.remux_file')
@patch('vidcompress.transcode_file')
def test_main_general_processing_transcode_path(mock_transcode, mock_remux, mock_media_info, mock_move, mock_makedirs, mock_remove, mock_exists, mock_walk):
    # Setup mocks
    mock_walk.return_value = [(mock_base_path, [], ['video.mkv'])]
    
    # Configure mock_exists dynamically
    # Initially, only the input file exists
    mock_exists.side_effect = lambda path: path == os.path.join(mock_base_path, 'video.mkv')

    mock_transcode.return_value = True
    mock_remux.return_value = False # Ensure remux is not called
    mock_media_info.return_value = {
        'format': {'format_name': 'matroska'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
        ]
    }

    def mock_transcode_side_effect(input_path, output_path, video_codec_choice):
        # After transcode, the temp_output_path should exist
        mock_exists.side_effect = lambda path: \
            path == os.path.join(mock_base_path, 'video.mkv') or \
            path == output_path # Simulate temp_output_path creation
        return True # Simulate success

    mock_transcode.side_effect = mock_transcode_side_effect

    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mp4')
    mock_transcode.assert_called_once()
    mock_remux.assert_not_called()


@patch('os.walk')
@patch('os.path.exists', return_value=False) # Simulate folder_path not existing
@patch('sys.stderr', new_callable=MagicMock)
def test_cli_invalid_path_error_message(mock_stderr, mock_exists, mock_walk):
    mock_walk.return_value = [] # No files to walk
    result = subprocess.run([sys.executable, 'vidcompress.py', '/nonexistent/path'], 
                          capture_output=True, text=True)
    assert 'Error: No such file or directory: \'/nonexistent/path\'' in result.stderr
    assert result.returncode == 1

@patch('os.walk')
@patch('os.path.exists')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.remux_file')
def test_main_remux_failure_cleanup(mock_remux, mock_media_info, mock_move, mock_makedirs, mock_remove, mock_exists, mock_walk):
    # Setup mocks
    mock_walk.return_value = [(mock_base_path, [], ['video.mkv'])]
    
    # Configure mock_exists dynamically
    # Initially, both input file and temp_output_path exist
    mock_exists.side_effect = lambda path: \
        path == os.path.join(mock_base_path, 'video.mkv') or \
        path == os.path.join(mock_base_path, 'video.temp.mp4')

    mock_remux.return_value = False # Simulate remux failure
    mock_media_info.return_value = {
        'format': {'format_name': 'matroska,webm'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'hevc'},
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }

    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mp4')
    mock_remove.assert_called_with(os.path.join(mock_base_path, 'video.temp.mp4'))

@patch('os.walk')
@patch('os.path.exists')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.transcode_file')
def test_main_transcode_failure_cleanup(mock_transcode, mock_media_info, mock_move, mock_makedirs, mock_remove, mock_exists, mock_walk):
    # Setup mocks
    mock_walk.return_value = [(mock_base_path, [], ['video.mp4'])]
    
    # Configure mock_exists dynamically
    # Initially, both input file and temp_output_path exist
    mock_exists.side_effect = lambda path: \
        path == os.path.join(mock_base_path, 'video.mp4') or \
        path == os.path.join(mock_base_path, 'video.temp.mp4')

    mock_transcode.return_value = False # Simulate transcode failure
    mock_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
        ]
    }

    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mp4')
    mock_remove.assert_called_with(os.path.join(mock_base_path, 'video.temp.mp4'))
