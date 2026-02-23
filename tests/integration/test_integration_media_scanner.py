# tests/test_media_scanner.py
import pytest

from app.media_scanner import MediaScanner


@pytest.mark.parametrize(
    "path, extensions, expected_len",
    [
        (
            "tests/test_assets/videos_temp",
            [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"],
            5,
        ),
        ("tests/test_assets/videos_temp", None, 5),
        ("tests/test_assets/videos_temp", [".mp4"], 4),
        ("tests/test_assets/videos_temp", [".mkv"], 1),
        ("tests/test_assets/videos_not_exist", None, 0),
    ],
)
def test_list_media_files_valid_path(path, extensions, expected_len):
    scanner = MediaScanner()
    count = 0
    for file in scanner.iter_media_files(path, extensions):
        count = count + 1
    assert count == expected_len
