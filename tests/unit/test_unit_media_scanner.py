from pathlib import Path

import pytest

from app.media_scanner import MediaScanner

# ---------- fixtures ----------


@pytest.fixture
def scanner() -> MediaScanner:
    return MediaScanner()


@pytest.fixture
def media_tree(tmp_path: Path) -> Path:
    """
    Creates a directory tree like:

    root/
      a.mp4
      b.mkv
      c.txt
      sub/
        d.avi
        e.jpg
    """
    root = tmp_path / "media"
    sub = root / "sub"

    root.mkdir()
    sub.mkdir()

    (root / "a.mp4").write_text("video")
    (root / "b.mkv").write_text("video")
    (root / "c.txt").write_text("text")
    (sub / "d.avi").write_text("video")
    (sub / "e.jpg").write_text("image")

    return root


# ---------- extension list ----------


def test_get_extension_list(scanner: MediaScanner):
    exts = scanner.get_extension_list()
    assert ".mp4" in exts
    assert ".mkv" in exts


def test_set_extension_list_valid(scanner: MediaScanner):
    scanner.set_extension_list([".mp4", ".webm"])
    assert scanner.get_extension_list() == [".mp4", ".webm"]


def test_set_extension_list_invalid(scanner: MediaScanner):
    with pytest.raises(ValueError):
        scanner.set_extension_list(["mp4", ".mkv"])


# ---------- iter_media_files ----------


def test_iter_media_files_default_extensions(scanner: MediaScanner, media_tree: Path):
    files = list(scanner.iter_media_files(str(media_tree)))

    names = sorted(p.name for p in files)
    assert names == ["a.mp4", "b.mkv", "d.avi"]


def test_iter_media_files_custom_extensions(scanner: MediaScanner, media_tree: Path):
    files = list(
        scanner.iter_media_files(
            str(media_tree),
            extensions=[".txt"],
        )
    )

    assert len(files) == 1
    assert files[0].name == "c.txt"


def test_iter_media_files_case_insensitive(scanner: MediaScanner, tmp_path: Path):
    root = tmp_path / "media"
    root.mkdir()
    (root / "VIDEO.MP4").write_text("video")

    files = list(scanner.iter_media_files(str(root)))
    assert len(files) == 1
    assert files[0].name == "VIDEO.MP4"


def test_iter_media_files_path_not_exist(scanner: MediaScanner):
    files = list(scanner.iter_media_files("does/not/exist"))
    assert files == []


def test_iter_media_files_path_is_file(scanner: MediaScanner, tmp_path: Path):
    file_path = tmp_path / "file.mp4"
    file_path.write_text("video")

    files = list(scanner.iter_media_files(str(file_path)))
    assert files == []
