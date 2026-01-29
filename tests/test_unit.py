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
from vidcompress import (
    get_ffmpeg_path,
    get_ffprobe_path,
    get_media_info,
    get_duration,
    is_videotoolbox_available,
    transcode_file,
    remux_file, 
    get_preferred_audio_index,
    is_mp4_faststart,
    send_notification,
    main
)

mock_base_path = './test_output'

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
@patch('vidcompress.DEBUG', True) 
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
    vidcompress.DEBUG = original_debug 

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
@patch('vidcompress.remux_file')
@patch('shutil.move')
@patch('os.path.exists', return_value=False)
@patch('os.makedirs')
def test_main_mp4_faststart_remux(mock_makedirs, mock_exists, mock_move, mock_remux_file, mock_is_mp4_faststart, mock_get_media_info, mock_walk):
    mock_remux_file.return_value = True
    mock_walk.return_value = [('dummy_path', [], ['video.mp4'])]
    mock_get_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }
    from vidcompress import main
    main('dummy_path', False, 'h.264', 'mp4')
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
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = ['Progress: 50%\\n', 'Progress: 100%\\n']
    mock_popen.return_value = mock_process

    with patch('sys.stdout') as mock_stdout:
        assert remux_file('input.mkv', 'output.mp4') is True
        assert mock_stdout.write.call_count >= 2

@patch('subprocess.run')
def test_get_media_info_json_decode_error(mock_run):
    mock_run.return_value = MagicMock(
        stdout="this is not json", 
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
    mock_walk.return_value = [(mock_base_path, [], ['video.mkv'])]
    
    mock_exists.side_effect = lambda path: path == os.path.join(mock_base_path, 'video.mkv')

    mock_media_info.return_value = {
        'format': {'format_name': 'matroska'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
        ]
    }

    def mock_transcode_side_effect(input_path, output_path, video_codec_choice, bitrate=None, media_info=None, preset='medium'):
        mock_exists.side_effect = lambda path: \
            path == os.path.join(mock_base_path, 'video.mkv') or \
            path == output_path 
        return True 

    mock_transcode.side_effect = mock_transcode_side_effect

    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mp4')

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
    
    assert not any('transcode' in str(call) for call in mock_media_info.mock_calls)

@patch('os.walk')
@patch('vidcompress.get_media_info')
def test_main_invalid_media_info(mock_media_info, mock_walk):
    mock_walk.return_value = [(mock_base_path, [], ['video.mp4'])]
    mock_media_info.return_value = None
    main(mock_base_path, keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    
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
    
    mock_media_info.assert_called_once()

@allure.feature("Main Function")
@allure.story("Main - No Video Stream")
@pytest.mark.unit
@patch('os.walk')
@patch('vidcompress.get_media_info')
@patch('sys.stderr', new_callable=MagicMock)
def test_main_no_video_stream_skip(mock_stderr, mock_get_media_info, mock_walk):
    mock_walk.return_value = [('dummy_path', [], ['video.mp4'])]
    mock_get_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }
    from vidcompress import main
    main('dummy_path', False, 'h.265', 'mp4')

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
    mock_walk.return_value = [('dummy_path', [], ['video.mp4'])]
    mock_get_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'}
        ]
    }
    from vidcompress import main
    main('dummy_path', False, 'h.265', 'mp4')
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
    mock_walk.return_value = [('dummy_path', [], ['video.mp4'])]
    mock_get_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }
    from vidcompress import main
    
    main('dummy_path', False, 'h.265', 'mkv')

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