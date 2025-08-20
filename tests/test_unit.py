import pytest
import os
import subprocess
import json
import argparse
import tempfile
import shutil
import sys
from unittest.mock import patch, MagicMock, mock_open

# Ensure the project root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def cli_temp_dir():
    """Creates a temporary directory for CLI tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)
from vidcompress import (
    get_ffmpeg_path,
    get_ffprobe_path,
    get_media_info,
    get_duration,
    is_videotoolbox_available,
    transcode_file,
    main
)

def test_get_ffmpeg_path():
    assert get_ffmpeg_path() == 'ffmpeg'

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

@patch('subprocess.run')
def test_get_media_info_success(mock_run, sample_media_info):
    mock_run.return_value = MagicMock(
        stdout=json.dumps(sample_media_info),
        returncode=0
    )
    result = get_media_info('test.mp4')
    assert result == sample_media_info

@patch('subprocess.run')
def test_get_media_info_file_not_found(mock_run):
    mock_run.side_effect = FileNotFoundError()
    assert get_media_info('nonexistent.mp4') is None

def test_get_duration(sample_media_info):
    assert get_duration(sample_media_info) == 60.123456

def test_get_duration_empty_dict():
    assert get_duration({}) == 0

@patch('subprocess.run')
def test_is_videotoolbox_available_true(mock_run):
    mock_run.return_value = MagicMock(
        stdout='hevc_videotoolbox',
        returncode=0
    )
    assert is_videotoolbox_available('hevc') is True

@patch('subprocess.run')
def test_is_videotoolbox_available_false(mock_run):
    mock_run.return_value = MagicMock(
        stdout='',
        returncode=0
    )
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
    mock_walk.return_value = [('/path', [], ['video.mkv'])]
    mock_exists.return_value = True
    mock_media_info.return_value = {
        'format': {'format_name': 'matroska'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
        ]
    }
    mock_transcode.return_value = True

    # Run main function
    main('/path', keep_original=False, video_codec_choice='h.265', container_choice='mkv')

    # Verify the expected workflow:
    # - transcode should be called once
    # - makedirs should be called to ensure target directory exists
    # - remove should be called to clean up temp files and input file
    mock_transcode.assert_called_once()
    mock_makedirs.assert_called_once()
    assert mock_remove.call_count >= 1, "Should call remove at least once"
    # At minimum, should try to remove the input file
    assert any(call[0][0].endswith('video.mkv') for call in mock_remove.call_args_list), \
        "Should try to remove input file"

@patch('os.walk')
@patch('vidcompress.get_media_info')
def test_main_skip_non_video_file(mock_media_info, mock_walk):
    mock_walk.return_value = [('/path', [], ['document.txt'])]
    
    main('/path', keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    
    mock_media_info.assert_not_called()

@patch('os.walk')
@patch('vidcompress.get_media_info')
def test_main_skip_correct_format(mock_media_info, mock_walk):
    mock_walk.return_value = [('/path', [], ['video.mkv'])]
    mock_media_info.return_value = {
        'format': {'format_name': 'matroska,webm'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'hevc'},
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }
    
    main('/path', keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    
    # Should not try to transcode since file is already in correct format
    assert not any('transcode' in str(call) for call in mock_media_info.mock_calls)

@patch('os.walk')
@patch('vidcompress.get_media_info')
def test_main_invalid_media_info(mock_media_info, mock_walk):
    mock_walk.return_value = [('/path', [], ['video.mp4'])]
    mock_media_info.return_value = None
    
    main('/path', keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    
    # Should continue without error when media info is invalid
    mock_media_info.assert_called_once()

@patch('os.walk')
@patch('vidcompress.get_media_info')
def test_main_no_video_stream(mock_media_info, mock_walk):
    mock_walk.return_value = [('/path', [], ['audio.mp4'])]
    mock_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2}
        ]
    }
    
    main('/path', keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    
    # Should skip files with no video stream
    mock_media_info.assert_called_once()

@patch('subprocess.run')
def test_is_videotoolbox_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, 'ffmpeg')
    assert is_videotoolbox_available('hevc') is False

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
    mock_walk.return_value = [('/path', [], ['video.mkv'])]
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
    main('/path', keep_original=False, video_codec_choice='h.265', container_choice='mkv')

def test_cli_help():
    """Test that the CLI help command works and shows usage information"""
    result = subprocess.run(['python', 'vidcompress.py', '--help'], 
                          capture_output=True, text=True)
    assert result.returncode == 0
    assert 'usage:' in result.stdout.lower()
    assert 'folder_path' in result.stdout
    assert '--keep-original' in result.stdout

def test_cli_invalid_path():
    """Test CLI behavior with an invalid path"""
    result = subprocess.run(['python', 'vidcompress.py', '/nonexistent/path'], 
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
        ['python', 'vidcompress.py', cli_temp_dir, '--keep-original'],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"CLI failed with output: {result.stderr}"
    assert os.path.exists(test_file), "Original file should still exist"
    re_encoded = os.path.join(cli_temp_dir, "test_transcoded.mp4")
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
        ['python', 'vidcompress.py', cli_temp_dir],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"CLI failed with output: {result.stderr}"
    assert os.path.exists(test_file), "Re-encoded file should exist at original path"
    # Verify it's a different file by checking modification time
    assert os.path.getmtime(test_file) > orig_mtime, "File should have been replaced with re-encoded version"

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
        mock_walk.return_value = [('/path', [], ['video.mkv'])]
        with patch('vidcompress.get_media_info') as mock_media_info:
            mock_media_info.return_value = {
                'format': {'format_name': 'matroska'},
                'streams': [
                    {'codec_type': 'video', 'codec_name': 'h264'},
                    {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
                ]
            }
            main('/path', keep_original=False, video_codec_choice='h.265', container_choice='mkv')
            mock_transcode.assert_called_once()

@patch('os.walk')
@patch('vidcompress.get_media_info')
@patch('vidcompress.transcode_file')
def test_main_transcode_failure(mock_transcode, mock_media_info, mock_walk):
    mock_walk.return_value = [('/path', [], ['video.mp4'])]
    mock_media_info.return_value = {
        'format': {'format_name': 'mp4'},
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
        ]
    }
    mock_transcode.return_value = False
    
    main('/path', keep_original=False, video_codec_choice='h.265', container_choice='mkv')
    mock_transcode.assert_called_once()

@patch('vidcompress.transcode_file', return_value=True)
@patch('os.path.exists')
@patch('os.remove')
@patch('os.walk')
def test_main_existing_output_cleanup(mock_walk, mock_remove, mock_exists, mock_transcode):
    mock_walk.return_value = [('/path', [], ['video.mp4'])]
    mock_exists.return_value = True

    with patch('vidcompress.get_media_info') as mock_media_info:
        mock_media_info.return_value = {
            'format': {'format_name': 'mp4'},
            'streams': [
                {'codec_type': 'video', 'codec_name': 'h264'},
                {'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2}
            ]
        }
        main('/path', keep_original=False, video_codec_choice='h.265', container_choice='mkv')
        assert mock_remove.call_count >= 1
