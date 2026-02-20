# tests/test_pipeline.py
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from app.pipeline import Pipeline
from app.media_scanner import MediaScanner, BackupStrategy
from app.transcoder import Transcoder

@pytest.fixture
def mock_transcoder():
    return Mock(spec=Transcoder)

@pytest.fixture
def mock_media_scanner():
    return Mock(spec=MediaScanner)

def test_pipeline_init(mock_transcoder):
    pipeline = Pipeline(mock_transcoder, ["tests/videos_temp"], False, BackupStrategy.DO_NOTHING)
    assert pipeline.transcoder == mock_transcoder
    assert pipeline.media_dirs == ["tests/videos_temp"]
    assert pipeline.extract_subtitle == False
    assert pipeline.backup_strategy == BackupStrategy.DO_NOTHING

# def test_run_pipeline_with_no_media_dirs(pipeline, mock_transcoder):
#     pipeline.media_dirs = []
#     pipeline.run()
#     assert pipeline.transcoder.extract_subtitles.call_count == 0
#     assert pipeline.transcoder.get_video_info.call_count == 0
#     assert pipeline.transcoder.process_video.call_count == 0

# def test_run_pipeline_with_media_dirs(pipeline, mock_transcoder, mock_media_scanner):
#     pipeline.media_dirs = ["tests/videos_temp"]
#     pipeline.extract_subtitle = True
#     with patch("app.pipeline.MediaScanner", return_value=mock_media_scanner) as mock_media_scanner_class:
#         pipeline.run()
#     mock_media_scanner_class.assert_called_once_with("tests/videos_temp")
#     mock_media_scanner.list_media_files.assert_called_once()