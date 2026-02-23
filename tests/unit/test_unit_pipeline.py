from pathlib import Path
from unittest.mock import Mock

import pytest

from app.jobrepo import Job
from app.pipeline import Pipeline
from app.transcoder import BackupStrategy, ProcessStatus, VideoInfo


@pytest.fixture
def mock_jobrepo():
    repo = Mock()
    # ⚠️ các method bị iterate phải trả iterable
    repo.iter_pending.return_value = []
    repo.iter_trash.return_value = []
    return repo


@pytest.fixture
def mock_scanner():
    scanner = Mock()
    scanner.iter_media_files.return_value = []
    return scanner


@pytest.fixture
def mock_transcoder():
    transcoder = Mock()
    transcoder.get_temp_files.return_value = []
    return transcoder


@pytest.fixture
def pipeline(mock_jobrepo, mock_scanner, mock_transcoder):
    return Pipeline(
        jobrepo=mock_jobrepo,
        scanner=mock_scanner,
        transcoder=mock_transcoder,
        media_dirs=["/media"],
        extract_subtitle=False,
        backup_strategy=BackupStrategy.DO_NOTHING,
    )


def test_scan_enqueues_media_files(pipeline, mock_scanner, mock_jobrepo):
    files = [Path("/media/a.mp4"), Path("/media/b.mkv")]
    mock_scanner.iter_media_files.return_value = files

    pipeline.scan()

    assert mock_jobrepo.enqueue.call_count == 2
    mock_jobrepo.enqueue.assert_any_call(files[0])
    mock_jobrepo.enqueue.assert_any_call(files[1])


def test_run_skips_when_no_transcoding_needed(pipeline, mock_jobrepo, mock_transcoder):
    job = Job(id=1, path=Path("/media/a.mp4"))
    mock_jobrepo.iter_pending.return_value = [job]

    mock_transcoder.get_video_info.return_value = VideoInfo(needs_transcoding=False)

    pipeline.run()

    mock_jobrepo.mark_skipped.assert_called_once_with(job.id)
    mock_transcoder.process_video.assert_not_called()


def test_run_transcode_success_updates_repo(pipeline, mock_jobrepo, mock_transcoder):
    job = Job(id=2, path=Path("/media/b.mp4"))
    mock_jobrepo.iter_pending.return_value = [job]

    mock_transcoder.get_video_info.return_value = VideoInfo(needs_transcoding=True)
    mock_transcoder.process_video.return_value = ProcessStatus.SUCCESS

    pipeline.run()

    mock_transcoder.process_video.assert_called_once_with(job.path)
    mock_jobrepo.mark_done.assert_called_once_with(job.id)


def test_run_extracts_subtitles_when_enabled(
    mock_jobrepo, mock_scanner, mock_transcoder
):
    pipeline = Pipeline(
        jobrepo=mock_jobrepo,
        scanner=mock_scanner,
        transcoder=mock_transcoder,
        media_dirs=[],
        extract_subtitle=True,
        backup_strategy=BackupStrategy.DO_NOTHING,
    )

    job = Job(id=3, path=Path("/media/c.mp4"))
    mock_jobrepo.iter_pending.return_value = [job]
    mock_transcoder.get_video_info.return_value = VideoInfo(needs_transcoding=False)
    pipeline.run()

    mock_transcoder.extract_subtitles.assert_called_once_with(job.path, job.path.parent)


@pytest.mark.parametrize(
    "strategy, expected_method",
    [
        (BackupStrategy.DO_NOTHING, "mark_skipped"),
        (BackupStrategy.ARCHIVE, "mark_archived"),
        (BackupStrategy.DELETE, "mark_deleted"),
    ],
)
def test_clean_updates_repo_by_backup_strategy(
    mock_jobrepo, mock_scanner, mock_transcoder, strategy, expected_method
):
    pipeline = Pipeline(
        jobrepo=mock_jobrepo,
        scanner=mock_scanner,
        transcoder=mock_transcoder,
        media_dirs=[],
        extract_subtitle=False,
        backup_strategy=strategy,
        backup_dir="/backup",
    )

    job = Job(id=99, path=Path("/tmp/file.tmp"))
    mock_jobrepo.iter_trash.return_value = [job]

    pipeline.clean()

    getattr(mock_jobrepo, expected_method).assert_called_once_with(job.id)
