import os
import shutil

import pytest


@pytest.fixture(scope="function", autouse=True)
def manage_test_folders():
    print("\n[Setup] Preparing environment...")

    source_dir = "tests/test_assets/videos"
    temp_dir = "tests/test_assets/videos_temp"
    archive_dir = "tests/test_assets/videos_temp_archive"

    if os.path.exists(source_dir):
        shutil.copytree(source_dir, temp_dir)

    yield
    print("\n[Teardown] Tearing down environment...")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists(archive_dir):
        shutil.rmtree(archive_dir)
