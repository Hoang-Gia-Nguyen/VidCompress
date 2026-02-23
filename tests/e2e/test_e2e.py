from pathlib import Path

from app.jobrepo import SQLiteJobRepository
from app.media_scanner import MediaScanner
from app.pipeline import Pipeline
from app.transcoder import BackupStrategy, FfmpegTranscoder


def test_pipeline_e2e_backup_strategy_delete():
    MEDIA_DIRS = ["tests/test_assets/videos_temp"]
    scanner = MediaScanner()
    transcoder = FfmpegTranscoder()
    jobrepo = SQLiteJobRepository("tests/test_assets/videos_temp/test.db")
    pipeline = Pipeline(
        scanner=scanner,
        jobrepo=jobrepo,
        transcoder=transcoder,
        media_dirs=MEDIA_DIRS,
        backup_strategy=BackupStrategy.DELETE,
        backup_dir=None,
        extract_subtitle=False,
    )

    pipeline.scan()
    pipeline.run()
    pipeline.clean()

    expected_transcoded_file = Path(
        "tests/test_assets/videos_temp/test_need_transcode.mkv"
    )
    expected_temp_file = Path(
        "tests/test_assets/videos_temp/test_need_transcode.mkv.orginalmedia"
    )
    assert expected_transcoded_file.exists() is True
    new_state = transcoder.get_video_info(expected_transcoded_file)
    assert new_state.needs_transcoding is False
    assert expected_temp_file.exists() is False


def test_pipeline_e2e_backup_strategy_archive():
    MEDIA_DIRS = ["tests/test_assets/videos_temp"]
    ARCHIVE_DIRS = "tests/test_assets/videos_temp_archived"
    scanner = MediaScanner()
    transcoder = FfmpegTranscoder()
    db_path = Path("tests/test_assets/videos_temp/test.db")
    if db_path.exists():
        db_path.unlink()
    jobrepo = SQLiteJobRepository("tests/test_assets/videos_temp/test.db")
    pipeline = Pipeline(
        scanner=scanner,
        jobrepo=jobrepo,
        transcoder=transcoder,
        media_dirs=MEDIA_DIRS,
        backup_strategy=BackupStrategy.ARCHIVE,
        backup_dir=ARCHIVE_DIRS,
        extract_subtitle=False,
    )

    pipeline.scan()
    pipeline.run()
    pipeline.clean()

    expected_transcoded_file = Path(
        "tests/test_assets/videos_temp/test_need_transcode.mkv"
    )
    expected_temp_file = Path(
        "tests/test_assets/videos_temp/test_need_transcode.mkv.orginalmedia"
    )
    expected_archived_dir = Path(ARCHIVE_DIRS)
    assert expected_transcoded_file.exists() is True
    new_state = transcoder.get_video_info(expected_transcoded_file)
    assert new_state.needs_transcoding is False
    assert expected_archived_dir.exists() is True
    assert expected_archived_dir.is_dir() is True
    assert expected_temp_file.exists() is False
