# Project Information

## Project Overview (from README.md)
This Python script, VidCompress, transcodes and remuxes video files within a specified folder to a standardized format. It optimizes media libraries for storage and playback compatibility, offering flexibility in video codecs (H.265, H.264, VP9) and container formats (MKV, MP4). It features automated remuxing for files already matching target codecs, standardized AAC 2-channel audio, and hardware acceleration (VideoToolbox on macOS). It skips already processed files and supports various video extensions. Prerequisites include Python 3.x, FFmpeg, and FFprobe. Usage involves providing a folder path and optional arguments for video codec, container, and keeping original files. The script analyzes media info, conditionally processes files (remux or transcode), and cleans up original files by default. The project is under the MIT License.

## Dependencies

### `requirements.txt` (Main Dependencies)
The `requirements.txt` file is empty. This suggests that the project might be using only standard Python libraries or that dependencies are managed differently (e.g., implicitly via the environment or not explicitly listed). This needs further investigation if external libraries are used in `vidcompress.py`.

### `requirements-test.txt` (Test Dependencies)
- `pytest==7.4.4`
- `pytest-cov==6.2.1`
- `pytest-mock==3.12.0`
- `pytest-xdist==3.8.0`
- `coverage>=7.5`

## Pytest Configuration (`pytest.ini`)
The `pytest.ini` file defines custom markers for categorizing tests:

**Test Levels/Types:**
- `unit`: Unit tests.

## Application Logic (`vidcompress.py`)

**Core Functionality:**
- **`get_ffmpeg_path()` and `get_ffprobe_path()`:** Provide paths to FFmpeg and FFprobe executables.
- **`get_media_info(file_path)`:** Extracts detailed media information using `ffprobe`.
- **`get_duration(media_info)`:** Retrieves video duration.
- **`is_videotoolbox_available(codec_type)`:** Checks for macOS VideoToolbox hardware acceleration for H.264/HEVC.
- **`transcode_file(input_path, output_path, video_codec_choice)`:** Transcodes video, utilizing hardware acceleration if available. Converts audio to AAC 2-channel.
- **`remux_file(input_path, output_path)`:** Changes container without re-encoding (fast operation).
- **`main(folder_path, keep_original, video_codec_choice, container_choice)`:**
    - Iterates through video files in a given folder.
    - Skips files already in the target format/container.
    - Decides between transcoding or remuxing based on current vs. target codecs/container.
    - Processes files to a temporary location, then moves to final destination.
    - Deletes original files by default, unless `--keep-original` flag is set.
    - Includes error handling and temporary file cleanup.
- **Command-line Interface:** Uses `argparse` to handle `folder_path`, `--keep-original`, `--video-codec` (h.265, h.264, vp9), and `--container` (mkv, mp4) arguments.

**Key Observations:**
- Relies on external `ffmpeg` and `ffprobe` tools.
- Implements hardware acceleration for specific codecs on macOS.
- Differentiates between full transcoding and efficient remuxing.
- `requirements.txt` is empty, indicating reliance on standard Python libraries.

## Requirements (from `docs/requirements/functional_requirements.yaml`)

### Functional Requirements
- **FR-TRANSCODE-001: Transcode H.264 to H.265 (HEVC)**
    - Description: Transcode H.264 video to H.265 (HEVC) with AAC 2-channel audio in an MP4 container.
    - Priority: High
    - Tags: `transcoding`, `h265`, `mp4`, `functional`

- **FR-REMUX-001: Remux MKV to MP4 (same codecs)**
    - Description: Remux MKV to MP4 without re-encoding if codecs are compatible.
    - Priority: High
    - Tags: `remuxing`, `mkv`, `mp4`, `functional`

- **FR-KEEP-ORIGINAL-001: Keep Original File**
    - Description: Retain original file when `--keep-original` flag is used.
    - Priority: Medium
    - Tags: `file_handling`, `functional`

- **FR-ERROR-001: Handle Invalid Input Path**
    - Description: Exit with error if provided folder path does not exist.
    - Priority: High
    - Tags: `error_handling`, `functional`

### Non-Functional Requirements
- **NFR-PERF-001: Transcoding Performance**
    - Description: Transcode a 1-minute 1080p H.264 video to H.265 within 30 seconds on a standard CI runner.
    - Priority: Medium
    - Tags: `performance`, `non_functional`

- **NFR-RELIABILITY-001: Robustness to Corrupted Files**
    - Description: Gracefully handle corrupted or unreadable video files, skipping and logging errors.
    - Priority: Medium
    - Tags: `reliability`, `non_functional`

## Testing Strategy and Implementation

### `conftest.py`
- **Fixtures:** Provides essential fixtures for testing:
    - `ffmpeg_path`, `ffprobe_path`: Ensures FFmpeg/FFprobe executables are available or skips tests.
    - `temp_dir`: Creates and cleans up a temporary directory for each test run, ensuring isolation.
    - `sample_media_info_data`: Provides a mock media info dictionary.
    - `create_test_video_file`: Helper to generate various test video files with specified codecs and containers using FFmpeg.
    - `test_data_dir`: Sets up a directory with pre-generated sample video files (H.264 MP4, H.265 MKV, VP9 WebM, H.264 MKV, corrupted file) for consistent testing.
    - `setup_test_video`: Copies a specific test video to an isolated temporary directory for individual test cases.
    - `run_vidcompress_cli`: A utility to execute the `vidcompress.py` script as a subprocess with given arguments, capturing output.

### `test_unit.py`
- **Focus:** Tests individual functions and components of `vidcompress.py` in isolation.
- **Mocking:** Extensively uses `unittest.mock.patch` to mock external dependencies like `subprocess.run`, `subprocess.Popen`, and file system operations (`os.walk`, `os.path.exists`, `os.remove`, `shutil.move`) to control test conditions and isolate the unit under test.
- **Coverage:** Aims for high statement and decision coverage for utility functions (`get_ffmpeg_path`, `get_ffprobe_path`, `get_media_info`, `get_duration`, `is_videotoolbox_available`) and core logic within `main`.
- **Techniques:** Employs Equivalence Partitioning, Boundary Value Analysis, Error Guessing, and Decision Coverage for thorough testing of various inputs and error conditions.
- **Key Tests:** Covers successful media info retrieval, error handling for file not found/subprocess errors, duration calculation, VideoToolbox availability, transcode/remux success/failure, CLI argument parsing, and various file operation error scenarios within `main`.

### Overall Testing Approach
- **Layered Testing:** The project follows a layered testing approach (Unit) to ensure comprehensive coverage and efficient defect localization.
- **Test Data Management:** Fixtures in `conftest.py` are used to generate and manage test video files, ensuring consistent and isolated test environments.
- **Error Handling:** Extensive tests are in place to verify the application's robustness against various error conditions, including invalid inputs, file system issues, and subprocess failures.
- **CI/CD Integration:** The use of Pytest suggests an intention for automated testing within a CI/CD pipeline, with detailed reporting capabilities.