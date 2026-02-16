import pytest
from pathlib import Path
import os
import shutil
from app.media_scanner import list_media_files, manage_backups


@pytest.mark.parametrize("path, expected_len", [
    ("tests/videos_temp", 5), # valid path
    ("tests/videos_temp_not_exist", 0), # invalid path
])
def test_list_media_files(path, expected_len):
    VIDEO_EXTS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']
    media_list = list_media_files(path, VIDEO_EXTS)
    assert len(media_list) == expected_len

def test_manage_backups_archive():
    manage_backups("tests/videos_temp", "archive", "tests/archived")
    archive_folder_path = Path("tests/archived")
    file_path = Path("tests/archived/test_backup.mp4.originalmedia")
    assert archive_folder_path.exists, f"Archive path was not created {archive_folder_path}"
    assert archive_folder_path.is_dir, f"Archive path is not a folder {archive_folder_path}"
    assert file_path.exists(), f"Path does not exist {file_path}"
    assert file_path.is_file(), f"Path is not file {file_path}"
    if os.path.exists("tests/archived"):
        shutil.rmtree("tests/archived")

def test_manage_backups_delete():
    manage_backups("tests/videos_temp", "delete")
    file_path = Path("tests/videos_temp/test_backup.mp4.originalmedia")
    assert not file_path.exists(), f"Original file was not deleted {file_path}"