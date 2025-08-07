import pytest
import os
import subprocess
import json
from unittest.mock import patch, MagicMock
from vidcompress import (
    get_ffmpeg_path,
    get_ffprobe_path,
    get_media_info,
    get_duration,
    is_videotoolbox_available,
    transcode_file
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
    assert is_videotoolbox_available() == True

@patch('subprocess.run')
def test_is_videotoolbox_available_false(mock_run):
    mock_run.return_value = MagicMock(
        stdout='',
        returncode=0
    )
    assert is_videotoolbox_available() == False

@patch('subprocess.Popen')
def test_transcode_file_success(mock_popen):
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = []
    mock_popen.return_value = mock_process
    
    assert transcode_file('input.mp4', 'output.mkv', False) == True

@patch('subprocess.Popen')
def test_transcode_file_failure(mock_popen):
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stdout = []
    mock_popen.return_value = mock_process
    
    assert transcode_file('input.mp4', 'output.mkv', False) == False
