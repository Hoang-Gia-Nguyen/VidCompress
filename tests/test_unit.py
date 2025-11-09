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
import zipfile

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
    get_preferred_audio_index,
    is_mp4_faststart,
    send_notification,
    extract_subtitles,
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

@allure.feature("Utility Functions")
@allure.story("Dprint Debug Output")
@pytest.mark.unit
@patch('builtins.print')
@patch('vidcompress.DEBUG', True) # Set DEBUG to True for this test
def test_dprint_debug_output(mock_print):
    from vidcompress import dprint
    dprint("Debug message")
    mock_print.assert_called_once_with("Debug message")

@allure.feature("Utility Functions")
@allure.story("Dprint No Debug Output")
@pytest.mark.unit
@patch('builtins.print')
def test_dprint_no_debug_output(mock_print):
    import vidcompress
    original_debug = vidcompress.DEBUG
    vidcompress.DEBUG = False
    vidcompress.dprint("Debug message")
    mock_print.assert_not_called()
    vidcompress.DEBUG = original_debug # Restore original DEBUG value

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

@allure.feature("Utility Functions")
@allure.story("Is VideoToolbox Available - File Not Found")
@pytest.mark.unit
@patch('subprocess.run', side_effect=FileNotFoundError)
def test_is_videotoolbox_available_file_not_found(mock_run):
    """
    Tests that is_videotoolbox_available handles FileNotFoundError.
    """
    assert is_videotoolbox_available('hevc') is False

@allure.feature("Utility Functions")
@allure.story("Is VideoToolbox Available - Called Process Error")
@pytest.mark.unit
@patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'ffmpeg'))
def test_is_videotoolbox_available_called_process_error(mock_run):
    assert is_videotoolbox_available('hevc') is False

@allure.feature("Main Function")
@allure.story("Main - MP4 Faststart Remux")
@pytest.mark.unit
@patch('os.walk')
@patch('vidcompress.get_media_info')
@patch('vidcompress.is_mp4_faststart', return_value=False)
@patch('vidcompress.remux_file', return_value=True)
@patch('shutil.move')
@patch('os.path.exists', return_value=False)
@patch('os.makedirs')
def test_main_mp4_faststart_remux(mock_makedirs, mock_exists, mock_move, mock_remux_file, mock_is_mp4_faststart, mock_get_media_info, mock_walk):
    """
    Tests that main triggers remuxing if an MP4 file is not faststart optimized.
    """
    mock_walk.return_value = [('dummy_path', [], ['video.mp4'])]
    mock_get_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }
    from vidcompress import main
    main('dummy_path', False, 'h.264', 'mp4', extract_subtitles_flag=False)
    mock_is_mp4_faststart.assert_called_once()
    mock_remux_file.assert_called_once()

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

@allure.feature("Utility Functions")
@allure.story("Remux File - Output to Stdout")
@pytest.mark.unit
@patch('subprocess.Popen')
def test_remux_file_output(mock_popen):
    """
    Tests that remux_file writes process output to stdout.
    """
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = ['Progress: 50%\\n', 'Progress: 100%\\n']
    mock_popen.return_value = mock_process

    with patch('sys.stdout') as mock_stdout:
        assert remux_file('input.mkv', 'output.mp4') is True
        assert mock_stdout.write.call_count >= 2

def test_get_media_info_json_decode_error(mocker):
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MagicMock(
        stdout="this is not json", # Invalid JSON
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
    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv', extract_subtitles_flag=False)
    
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
    
    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv', extract_subtitles_flag=False)
    
    # Should skip files with no video stream
    mock_media_info.assert_called_once()

@allure.feature("Main Function")
@allure.story("Main - No Video Stream")
@pytest.mark.unit
@patch('os.walk')
@patch('vidcompress.get_media_info')
@patch('sys.stderr', new_callable=MagicMock)
def test_main_no_video_stream_skip(mock_stderr, mock_get_media_info, mock_walk):
    """
    Tests that main skips files that do not have a video stream.
    """
    mock_walk.return_value = [('dummy_path', [], ['video.mp4'])]
    mock_get_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }
    from vidcompress import main
    main('dummy_path', False, 'h.265', 'mp4', extract_subtitles_flag=False)


@allure.feature("Main Function")
@allure.story("Main - No Audio Stream")
@pytest.mark.unit
@patch('os.walk')
@patch('vidcompress.get_media_info')
@patch('builtins.print')
@patch('vidcompress.transcode_file', return_value=True)
@patch('shutil.move')
@patch('os.path.exists', return_value=False)
@patch('os.makedirs')
def test_main_no_audio_stream(mock_makedirs, mock_exists, mock_move, mock_transcode_file, mock_print, mock_get_media_info, mock_walk):
    """
    Tests that main handles files with no audio streams.
    """
    mock_walk.return_value = [('dummy_path', [], ['video.mp4'])]
    mock_get_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'}
        ]
    }
    from vidcompress import main
    main('dummy_path', False, 'h.265', 'mp4', extract_subtitles_flag=False)
    # Assert that transcoding still happens even without an audio stream
    mock_transcode_file.assert_called_once()

@allure.feature("Main Function")
@allure.story("Main - Zipping/Removal OSError")
@pytest.mark.unit
@patch('os.walk')
@patch('vidcompress.get_media_info')
@patch('vidcompress.transcode_file', return_value=True)
@patch('shutil.move')
@patch('os.path.exists', return_value=True)
@patch('os.remove')
@patch('zipfile.ZipFile', side_effect=zipfile.BadZipFile("Test BadZipFile"))
@patch('sys.stderr', new_callable=MagicMock)
def test_main_zipping_removal_oserror(mock_stderr, mock_zipfile, mock_remove, mock_exists, mock_move, mock_transcode_file, mock_get_media_info, mock_walk):
    """
    Tests that main handles OSError during zipping or removing the original file.
    """
    mock_walk.return_value = [('dummy_path', [], ['video.mp4'])]
    mock_get_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }
    from vidcompress import main
    
    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_exists dynamically
    exists_state = {
        'dummy_path/video.mp4': True,
        'dummy_path/video.temp.mkv': False,
        'dummy_path/video.mkv': False
    }

    def exists_side_effect(path):
        return exists_state.get(path, False)

    mock_exists.side_effect = exists_side_effect

    # Configure mock_remove to raise OSError only for the original file
    def remove_side_effect(path):
        if path == 'dummy_path/video.mp4':
            raise OSError("Test OSError")
        else:
            return None

    mock_remove.side_effect = remove_side_effect

    main('dummy_path', False, 'h.265', 'mkv', extract_subtitles_flag=False)
    mock_stderr.write.assert_any_call('Error zipping or removing original file dummy_path/video.mp4: Test BadZipFile\n')

@patch('subprocess.Popen')
@patch('subprocess.run')
def test_transcode_file_output(mock_run, mock_popen):
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

@allure.feature("Utility Functions")
@allure.story("Extract Subtitles - No Media Info")
@pytest.mark.unit
@patch('vidcompress.get_media_info', return_value=None)
@patch('builtins.print')
def test_extract_subtitles_no_media_info(mock_print, mock_get_media_info):
    """
    Tests that extract_subtitles handles cases where media info cannot be retrieved.
    """
    from vidcompress import extract_subtitles
    extract_subtitles('dummy.mp4', 'dummy_dir')
    mock_print.assert_called_with(
        "Failed to get media info for dummy.mp4. Skipping subtitle extraction.",
        file=sys.stderr
    )

@allure.feature("Utility Functions")
@allure.story("Extract Subtitles - Non-Text Subtitle Stream")
@pytest.mark.unit
@patch('subprocess.run')
@patch('builtins.print')
def test_extract_subtitles_non_text_stream(mock_print, mock_run):
    """
    Tests that extract_subtitles skips non-text subtitle streams.
    """
    from vidcompress import extract_subtitles
    media_info = {
        'streams': [
            {'codec_type': 'subtitle', 'index': 0, 'codec_name': 'hdmv_pgs_subtitle'} # Non-text codec
        ]
    }
    extract_subtitles('dummy.mp4', 'dummy_dir', media_info)
    mock_print.assert_called_with(
        "Skipping non-text subtitle stream 0 (hdmv_pgs_subtitle) in dummy.mp4",
        file=sys.stderr
    )
    mock_run.assert_not_called()

@pytest.mark.unit
@pytest.mark.functional

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



@patch('os.walk')
@patch('os.path.exists')
@patch('zipfile.ZipFile')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.remux_file')
def test_main_remux_and_delete_original(mock_remux, mock_media_info, mock_move, mock_makedirs, mock_remove, mock_zip, mock_exists, mock_walk):
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
    mock_zip.assert_called_once_with(os.path.join(mock_base_path, 'video.mkv.zip'), 'w', zipfile.ZIP_DEFLATED)
    zip_instance = mock_zip.return_value.__enter__.return_value
    zip_instance.write.assert_called_once_with(os.path.join(mock_base_path, 'video.mkv'), 'video.mkv')
    mock_remove.assert_called_once_with(os.path.join(mock_base_path, 'video.mkv'))


@patch('os.walk')
@patch('os.path.exists')
@patch('zipfile.ZipFile')
@patch('os.remove')
@patch('os.makedirs')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.transcode_file')
def test_main_transcode_and_delete_original(mock_transcode, mock_media_info, mock_move, mock_makedirs, mock_remove, mock_zip, mock_exists, mock_walk):
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
    mock_zip.assert_called_once_with(os.path.join(mock_base_path, 'video.mp4.zip'), 'w', zipfile.ZIP_DEFLATED)
    zip_instance = mock_zip.return_value.__enter__.return_value
    zip_instance.write.assert_called_once_with(os.path.join(mock_base_path, 'video.mp4'), 'video.mp4')
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


@allure.feature("Utility Functions")
@allure.story("Get Preferred Audio Index - No Language Fallback")
@pytest.mark.unit
def test_get_preferred_audio_index_no_language_fallback():
    """
    Tests that get_preferred_audio_index falls back to the first stream
    when no language information is available.
    """
    media_info = {
        'streams': [
            {'codec_type': 'audio'},
            {'codec_type': 'audio'}
        ]
    }
    assert get_preferred_audio_index(media_info) == 0

@allure.feature("Utility Functions")
@allure.story("Is MP4 Faststart - Optimized")
@pytest.mark.unit
@patch('os.path.getsize')
@patch('builtins.open', new_callable=mock_open)
def test_is_mp4_faststart_optimized(mock_file_open, mock_getsize):
    """
    Tests that is_mp4_faststart returns True for an optimized MP4 file.
    """
    # Simulate a file where moov comes before mdat
    # ftyp...moov...mdat
    mock_getsize.return_value = 100
    mock_file_open.return_value.read.side_effect = [
        b'\x00\x00\x00\x18ftyp',  # ftyp box
        b'\x00\x00\x00\x18moov',  # moov box
        b'\x00\x00\x00\x18mdat',  # mdat box
        b'' # EOF
    ]
    assert is_mp4_faststart('dummy.mp4') is True

@allure.feature("Utility Functions")
@allure.story("Is MP4 Faststart - Not Optimized")
@pytest.mark.unit
@patch('os.path.getsize')
@patch('builtins.open', new_callable=mock_open)
def test_is_mp4_faststart_not_optimized(mock_file_open, mock_getsize):
    """
    Tests that is_mp4_faststart returns False for a non-optimized MP4 file.
    """
    # Simulate a file where mdat comes before moov
    # ftyp...mdat...moov
    mock_getsize.return_value = 100
    mock_file_open.return_value.read.side_effect = [
        b'\x00\x00\x00\x18ftyp',  # ftyp box
        b'\x00\x00\x00\x18mdat',  # mdat box
        b'\x00\x00\x00\x18moov',  # moov box
        b'' # EOF
    ]
    assert is_mp4_faststart('dummy.mp4') is False

@allure.feature("Utility Functions")
@allure.story("Is MP4 Faststart - Corrupt File")
@pytest.mark.unit
@patch('os.path.getsize')
@patch('builtins.open', new_callable=mock_open)
def test_is_mp4_faststart_corrupt_file(mock_file_open, mock_getsize):
    """
    Tests that is_mp4_faststart handles corrupt files gracefully.
    """
    mock_getsize.return_value = 100
    mock_file_open.return_value.read.side_effect = [
        b'corrupt data', # Not a valid box
        b'' # EOF
    ]
    assert is_mp4_faststart('dummy.mp4') is True # Should return True on error

@allure.feature("Utility Functions")
@allure.story("Is MP4 Faststart - Exception Handling")
@pytest.mark.unit
@patch('os.path.getsize', side_effect=Exception("Test Error"))
@patch('builtins.open', new_callable=mock_open)
def test_is_mp4_faststart_exception(mock_file_open, mock_getsize):
    """
    Tests that is_mp4_faststart handles exceptions gracefully.
    """
    assert is_mp4_faststart('dummy.mp4') is True # Should return True on error

@allure.feature("Utility Functions")
@allure.story("Is MP4 Faststart - Short Header")
@pytest.mark.unit
@patch('os.path.getsize')
@patch('builtins.open', new_callable=mock_open)
def test_is_mp4_faststart_short_header(mock_file_open, mock_getsize):
    """
    Tests that is_mp4_faststart handles a file with a short header.
    """
    mock_getsize.return_value = 5
    mock_file_open.return_value.read.side_effect = [
        b'\x00\x00\x00', # Header shorter than 8 bytes
        b'' # EOF
    ]
    assert is_mp4_faststart('dummy.mp4') is True

@allure.feature("Utility Functions")
@allure.story("Is MP4 Faststart - 64-bit Extended Size Box")
@pytest.mark.unit
@patch('os.path.getsize')
@patch('builtins.open', new_callable=mock_open)
def test_is_mp4_faststart_64bit_extended_size(mock_file_open, mock_getsize):
    """
    Tests that is_mp4_faststart handles a 64-bit extended size box.
    """
    mock_getsize.return_value = 100
    mock_file_open.return_value.read.side_effect = [
        b'\x00\x00\x00\x01moov', # size == 1
        b'\x00\x00\x00\x00\x00\x00\x00\x18', # extended size (24 bytes)
        b'\x00\x00\x00\x18mdat', # mdat box
        b'' # EOF
    ]
    assert is_mp4_faststart('dummy.mp4') is True

@allure.feature("Utility Functions")
@allure.story("Is MP4 Faststart - Box Extends to EOF")
@pytest.mark.unit
@patch('os.path.getsize')
@patch('builtins.open', new_callable=mock_open)
def test_is_mp4_faststart_box_extends_to_eof(mock_file_open, mock_getsize):
    """
    Tests that is_mp4_faststart handles a box that extends to EOF (size == 0).
    """
    mock_getsize.return_value = 100
    mock_file_open.return_value.read.side_effect = [
        b'\x00\x00\x00\x00moov', # size == 0
        b'\x00\x00\x00\x18mdat', # mdat box
        b'' # EOF
    ]
    assert is_mp4_faststart('dummy.mp4') is True

@allure.feature("Utility Functions")
@allure.story("Is MP4 Faststart - Size Less Than Header Size")
@pytest.mark.unit
@patch('os.path.getsize')
@patch('builtins.open', new_callable=mock_open)
def test_is_mp4_faststart_size_less_than_header(mock_file_open, mock_getsize):
    """
    Tests that is_mp4_faststart handles a box where the reported size is less than the header size.
    """
    mock_getsize.return_value = 100
    mock_file_open.return_value.read.side_effect = [
        b'\x00\x00\x00\x04moov', # size = 4, which is less than header_size = 8
        b'' # EOF
    ]
    assert is_mp4_faststart('dummy.mp4') is True

@allure.feature("Utility Functions")
@allure.story("Is MP4 Faststart - Box Extends to EOF")
@pytest.mark.unit
@patch('os.path.getsize')
@patch('builtins.open', new_callable=mock_open)
def test_is_mp4_faststart_box_extends_to_eof(mock_file_open, mock_getsize):
    """
    Tests that is_mp4_faststart handles a box that extends to EOF (size == 0).
    """
    mock_getsize.return_value = 100
    mock_file_open.return_value.read.side_effect = [
        b'\x00\x00\x00\x00moov', # size == 0
        b'\x00\x00\x00\x18mdat', # mdat box
        b'' # EOF
    ]
    assert is_mp4_faststart('dummy.mp4') is True

@allure.feature("Utility Functions")
@allure.story("Send Notification - Empty URL")
@pytest.mark.unit
@patch('subprocess.run')
def test_send_notification_empty_url(mock_run):
    """
    Tests that send_notification returns early if the URL is empty.
    """
    from vidcompress import send_notification
    send_notification('', 'Test Title', 'Test Message')
    mock_run.assert_not_called()

@allure.feature("Utility Functions")
@allure.story("Send Notification - Curl Not Found")
@pytest.mark.unit
@patch('subprocess.run', side_effect=FileNotFoundError)
@patch('vidcompress.dprint')
def test_send_notification_curl_not_found(mock_dprint, mock_run):
    """
    Tests that send_notification handles FileNotFoundError when curl is not found.
    """
    from vidcompress import send_notification
    send_notification('http://test.url', 'Test Title', 'Test Message')
    mock_dprint.assert_called_with("[DEBUG] curl not found; skipping notification")

@allure.feature("Utility Functions")
@allure.story("Send Notification - Generic Exception")
@pytest.mark.unit
@patch('subprocess.run', side_effect=Exception("Test Error"))
@patch('vidcompress.dprint')
def test_send_notification_generic_exception(mock_dprint, mock_run):
    """
    Tests that send_notification handles generic exceptions during subprocess execution.
    """
    from vidcompress import send_notification
    send_notification('http://test.url', 'Test Title', 'Test Message')
    mock_dprint.assert_called_with("[DEBUG] Failed to send notification: Test Error")

@patch('vidcompress.is_videotoolbox_available', return_value=True)
@patch('subprocess.Popen')
def test_transcode_file_videotoolbox_uses_bitrate(mock_popen, mock_is_vt_available):
    """
    Tests that transcode_file adds a bitrate when using a videotoolbox encoder.
    """
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = []
    mock_popen.return_value = mock_process

    transcode_file('input.mp4', 'output.mp4', 'h.265')

    mock_popen.assert_called_once()
    command = mock_popen.call_args[0][0]
    
    assert 'hevc_videotoolbox' in command
    assert '-b:v' in command
    assert '8000k' in command


@patch('os.walk')
@patch('os.path.exists')
@patch('zipfile.ZipFile')
@patch('os.remove')
@patch('shutil.move')
@patch('vidcompress.get_media_info')
@patch('vidcompress.transcode_file')
def test_main_zips_original_when_not_keeping(mock_transcode, mock_media_info, mock_move, mock_remove, mock_zip, mock_exists, mock_walk):
    # Setup mocks
    mock_walk.return_value = [('folder', [], ['video.mkv'])]
    
    # The input file exists, the temp file is created by transcode, then moved.
    def exists_handler(path):
        return path == 'folder/video.mkv'

    mock_exists.side_effect = exists_handler
    
    mock_media_info.return_value = {
        'format': {'format_name': 'matroska'},
        'streams': [{'codec_type': 'video', 'codec_name': 'h264'}]
    }
    mock_transcode.return_value = True

    # Run main
    main('folder', keep_original=False, video_codec_choice='h.265', container_choice='mp4', extract_subtitles_flag=False)

    # Assertions
    # 1. ZipFile was called to create the archive
    mock_zip.assert_called_with('folder/video.mkv.zip', 'w', zipfile.ZIP_DEFLATED)
    
    # 2. The original file was added to the zip archive
    zip_file_handle = mock_zip.return_value.__enter__.return_value
    zip_file_handle.write.assert_called_with('folder/video.mkv', 'video.mkv')

    # 3. The original file was removed
    mock_remove.assert_any_call('folder/video.mkv')

    # 4. The new file was moved into place
    mock_move.assert_called_with('folder/video.temp.mp4', 'folder/video.mp4')