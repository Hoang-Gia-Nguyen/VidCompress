import os
import shutil
import pytest

@pytest.fixture(scope="function", autouse=True)
def manage_test_folders():
    # --- SETUP: Chạy trước khi bắt đầu test ---
    print("\n[Setup] Preparing environment...")
    
    source_dir = "tests/videos"
    temp_dir = "tests/videos_temp"

    # Copy thư mục videos thành videos_temp
    if os.path.exists(source_dir):
        shutil.copytree(source_dir, temp_dir)

    yield  # Tại đây, Pytest sẽ tạm dừng để chạy các bài test của bạn

    # --- TEARDOWN: Chạy sau khi tất cả test đã xong ---
    print("\n[Teardown] Tearing down environment...")
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)