# tests/test_media_scanner.py
import pytest
from pathlib import Path
import os
import shutil
from app.media_scanner import MediaScanner, BackupStrategy


@pytest.mark.parametrize("path, expected_len", [
    ("tests/videos_temp", 5), # valid path
])
def test_list_media_files_valid_path(path, expected_len):
    VIDEO_EXTS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']
    scanner = MediaScanner(path)
    media_list = scanner.list_media_files(VIDEO_EXTS)
    assert len(media_list) == expected_len

@pytest.mark.parametrize("path", [
    ("tests/videos_temp_not_exist"), # invalid path
])
def test_list_media_files_path_not_exist(path):
    VIDEO_EXTS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']
    with pytest.raises(FileNotFoundError) as excinfo:
        MediaScanner(path)
    assert f"Path does not exist: '{path}'" in str(excinfo.value)

@pytest.mark.parametrize("path", [
    ("tests/videos_temp/test_subtitles_extract.mp4"), # file path
])
def test_list_media_files_path_is_file(path):
    VIDEO_EXTS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']
    with pytest.raises(NotADirectoryError) as excinfo:
        MediaScanner(path)
    assert f"Path is not dir: '{path}'" in str(excinfo.value)

def test_manage_backups_archive():
    scanner = MediaScanner("tests/videos_temp")
    scanner.manage_backups(BackupStrategy.ARCHIVE, "tests/archived")
    archive_folder_path = Path("tests/archived")
    file_path = Path("tests/archived/test_backup.mp4.originalmedia")
    assert archive_folder_path.exists, f"Archive path was not created {archive_folder_path}"
    assert archive_folder_path.is_dir, f"Archive path is not a folder {archive_folder_path}"
    assert file_path.exists(), f"Path does not exist {file_path}"
    assert file_path.is_file(), f"Path is not file {file_path}"
    if os.path.exists("tests/archived"):
        shutil.rmtree("tests/archived")

def test_manage_backups_delete():
    scanner = MediaScanner("tests/videos_temp")
    scanner.manage_backups(BackupStrategy.DELETE)
    file_path = Path("tests/videos_temp/test_backup.mp4.originalmedia")
    assert not file_path.exists(), f"Original file was not deleted {file_path}"