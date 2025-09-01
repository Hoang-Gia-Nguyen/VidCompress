# Project Information

## Project Overview (from README.md)
This Python script, VidCompress, transcodes and remuxes video files within a specified folder to a standardized format. It optimizes media libraries for storage and playback compatibility, offering flexibility in video codecs (H.265, H.264, VP9) and container formats (MKV, MP4). It features automated remuxing for files already matching target codecs, standardized AAC 2-channel audio, and hardware acceleration (VideoToolbox on macOS). It skips already processed files and supports various video extensions. Prerequisites include Python 3.x, FFmpeg, and FFprobe. Usage involves providing a folder path and optional arguments for video codec, container, and keeping original files. The script analyzes media info, conditionally processes files (remux or transcode), and cleans up original files by default. The project is under the MIT License.

## Dependencies

### `requirements.txt` (Main Dependencies)
The `requirements.txt` file is empty. This suggests that the project might be using only standard Python libraries or that dependencies are managed differently (e.g., implicitly via the environment or not explicitly listed). This needs further investigation if external libraries are used in `vidcompress.py`.

### `requirements-test.txt` (Test Dependencies)
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
- `allure-pytest==2.13.2`
- `playwright==1.45.0`

## Pytest Configuration (`pytest.ini`)
The `pytest.ini` file defines custom markers for categorizing tests:

**Test Levels/Types:**
- `e2e`: End-to-end tests.
- `functional`: Functional tests.
- `non_functional`: Non-functional tests.
- `performance`: Performance tests.
- `reliability`: Reliability tests.
- `unit`: Unit tests.
- `integration`: Integration tests.

**Test Design Techniques:**
- `use_case_testing`
- `state_transition_testing`
- `checklist_based_testing`
- `decision_table_testing`
- `equivalence_partitioning`
- `boundary_value_analysis`
- `statement_coverage`
- `decision_coverage`
- `error_guessing`

**Requirements Traceability:**
- `FR_TRANSCODE_001`: Functional Requirement for transcoding.
- `FR_REMUX_001`: Functional Requirement for remuxing.
- `FR_KEEP_ORIGINAL_001`: Functional Requirement for keeping original files.
- `FR_ERROR_001`: Functional Requirement for error handling.
- `NFR_PERF_001`: Non-Functional Requirement for performance.
- `NFR_RELIABILITY_001`: Non-Functional Requirement for reliability.

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
    - Tests: `test_unit.py::test_transcode_h264_to_h265`, `test_integration.py::test_transcode_h264_to_h265_mocked_ffmpeg`, `test_e2e.py::test_e2e_transcode_h264_to_h265`

- **FR-REMUX-001: Remux MKV to MP4 (same codecs)**
    - Description: Remux MKV to MP4 without re-encoding if codecs are compatible.
    - Priority: High
    - Tags: `remuxing`, `mkv`, `mp4`, `functional`
    - Tests: `test_unit.py::test_remux_mkv_to_mp4`, `test_integration.py::test_remux_mkv_to_mp4_mocked_ffmpeg`, `test_e2e.py::test_e2e_remux_mkv_to_mp4`

- **FR-KEEP-ORIGINAL-001: Keep Original File**
    - Description: Retain original file when `--keep-original` flag is used.
    - Priority: Medium
    - Tags: `file_handling`, `functional`
    - Tests: `test_e2e.py::test_e2e_keep_original_flag`

- **FR-ERROR-001: Handle Invalid Input Path**
    - Description: Exit with error if provided folder path does not exist.
    - Priority: High
    - Tags: `error_handling`, `functional`
    - Tests: `test_e2e.py::test_e2e_invalid_input_path`

### Non-Functional Requirements
- **NFR-PERF-001: Transcoding Performance**
    - Description: Transcode a 1-minute 1080p H.264 video to H.265 within 30 seconds on a standard CI runner.
    - Priority: Medium
    - Tags: `performance`, `non_functional`
    - Tests: `test_e2e.py::test_e2e_transcoding_performance`

- **NFR-RELIABILITY-001: Robustness to Corrupted Files**
    - Description: Gracefully handle corrupted or unreadable video files, skipping and logging errors.
    - Priority: Medium
    - Tags: `reliability`, `non_functional`
    - Tests: `test_e2e.py::test_e2e_corrupted_file_handling`

## Test Technique Coverage (from `docs/technique_coverage_map.md`)

This section summarizes the test technique coverage based on the provided `technique_coverage_map.md`.

**Coverage Matrix Highlights:**
- **FR-TRANSCODE-001 (Transcode H.264 to H.265):** Covered by Unit, Integration, and System/E2E tests using Use Case Testing.
- **FR-REMUX-001 (Remux MKV to MP4):** Covered by Unit, Integration, and System/E2E tests using Use Case Testing.
- **FR-KEEP-ORIGINAL-001 (Keep Original File):** Covered by System/E2E tests using Use Case Testing.
- **FR-ERROR-001 (Handle Invalid Input Path):** Covered by Unit (Error Guessing) and System/E2E (Use Case Testing).
- **NFR-PERF-001 (Transcoding Performance):** Covered by System/E2E tests using Exploratory Testing.
- **NFR-RELIABILITY-001 (Robustness to Corrupted Files):** Covered by System/E2E tests using Error Guessing.

**General Coverage (Unit Level):**
- **Equivalence Partitioning:** `test_unit.py::test_get_media_info_various_inputs`
- **Boundary Value Analysis:** `test_unit.py::test_get_duration_boundary_values`
- **Statement Coverage:** Extensive coverage across various utility functions and core logic (e.g., `get_ffmpeg_path`, `get_media_info`, `transcode_file`, `remux_file`).
- **Decision Coverage:** Covered in `is_videotoolbox_available`, `transcode_file`, `remux_file`, and `main` logic related to file processing and cleanup.
- **Error Guessing:** Comprehensive error handling tests for `get_media_info`, `is_videotoolbox_available`, `transcode_file`, `remux_file`, and various file operations within `main`.
- **Use Case Testing:** Covered for `main` function scenarios like empty folder, non-video files, skipping correct formats, and CLI argument handling.

**General Coverage (Integration Level):**
- **Decision Table Testing:** `test_integration.py::test_main_decision_table_scenarios`

**General Coverage (System/E2E Level):**
- **State Transition Testing:** `test_e2e.py::test_e2e_state_transitions`
- **Checklist-based Testing:** `test_e2e.py::test_e2e_all_codec_container_combinations`

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

### `test_integration.py`
- **Focus:** Tests the interaction between different modules and components of `vidcompress.py`, often with mocked external tools (FFmpeg/FFprobe) but real file system operations.
- **Techniques:** Primarily uses Use Case Testing and Decision Table Testing to cover various scenarios of transcoding, remuxing, and file handling.
- **Key Tests:** Includes tests for processing empty folders, folders with non-video files, transcoding H.264 to H.265, remuxing MKV to MP4, transcoding VP9 to H.265, and handling nested folders. The `test_main_decision_table_scenarios` specifically covers different combinations of codec/container matches to verify the core decision logic.

### `test_e2e.py`
- **Focus:** Tests the entire application flow from command-line invocation to file system changes, using actual FFmpeg/FFprobe execution (not mocked).
- **Techniques:** Utilizes Use Case Testing for functional requirements, Exploratory Testing for performance, Error Guessing for reliability, State Transition Testing for sequential operations, and Checklist-based Testing for comprehensive codec/container combinations.
- **Key Tests:** Covers end-to-end scenarios for transcoding (H.264 to H.265), remuxing (MKV to MP4), `--keep-original` flag functionality, invalid input path handling, transcoding performance, robustness to corrupted files, and state transitions (e.2., H264->H265 then H265->VP9). The `test_e2e_all_codec_container_combinations` systematically checks all defined codec and container targets.

### Overall Testing Approach
- **Layered Testing:** The project follows a layered testing approach (Unit -> Integration -> E2E) to ensure comprehensive coverage and efficient defect localization.
- **Requirement Traceability:** Pytest markers and Allure annotations are used to link tests directly to functional and non-functional requirements, as well as ISTQB test design techniques.
- **Test Data Management:** Fixtures in `conftest.py` are used to generate and manage test video files, ensuring consistent and isolated test environments.
- **Error Handling:** Extensive tests are in place to verify the application's robustness against various error conditions, including invalid inputs, file system issues, and subprocess failures.
- **CI/CD Integration:** The use of Pytest and Allure suggests an intention for automated testing within a CI/CD pipeline, with detailed reporting capabilities.

## Test Strategy

### 1. Scope In/Out, Risks, Assumptions

**Scope In:**
- Functional testing of video transcoding (H.264 to H.265, VP9 to H.265, H.265 to H.264).
- Functional testing of video remuxing (MKV to MP4, MP4 to MKV) when codecs are compatible.
- Functional testing of `--keep-original` flag behavior.
- Functional testing of invalid input path handling.
- Non-functional testing for transcoding performance.
- Non-functional testing for robustness to corrupted/unreadable files.
- Unit testing of utility functions (`get_ffmpeg_path`, `get_ffprobe_path`, `get_media_info`, `get_duration`, `is_videotoolbox_available`).
- Integration testing of `main` function logic with mocked external calls.
- End-to-end testing of the CLI with actual FFmpeg/FFprobe execution.
- Coverage of all ISTQB Foundation Level test design techniques.

**Scope Out:**
- UI testing (as there is no UI).
- Extensive cross-platform testing beyond macOS (where VideoToolbox is relevant) and general Linux/Windows compatibility (FFmpeg/FFprobe).
- Detailed audio codec testing beyond AAC 2-channel standardization.
- Testing of all possible FFmpeg/FFprobe command-line options not directly exposed by the script.
- Performance testing on a wide range of hardware configurations.
- Security penetration testing.

**Risks:**
- **FFmpeg/FFprobe availability and version compatibility:** Different versions might behave differently or have varying codec support.
- **Hardware acceleration (VideoToolbox) inconsistencies:** Behavior might vary across macOS versions or hardware.
- **File system permissions:** Issues with creating/deleting/moving files in target directories.
- **Corrupted/edge-case video files:** FFmpeg/FFprobe might crash or produce unexpected output for malformed inputs.
- **Performance degradation:** New features or changes could negatively impact transcoding/remuxing speed.
- **Race conditions:** Potential issues with temporary file handling, especially in concurrent operations (though not explicitly supported, could arise from external automation).

**Assumptions:**
- Python 3.x is installed and accessible.
- FFmpeg and FFprobe are correctly installed and available in the system's PATH.
- Test video files generated by `conftest.py` are representative and valid for testing purposes.
- The `test_output` directory is writable by the test runner.
- The `requirements-test.txt` dependencies are installed in the test environment.

### 2. Test Levels

-   **Unit Testing:**
    -   **Target:** Individual functions and methods within `vidcompress.py` (e.g., `get_media_info`, `transcode_file`, `remux_file`).
    -   **Techniques:** Statement Coverage, Decision Coverage, Equivalence Partitioning, Boundary Value Analysis, Error Guessing.
    -   **Tools:** `pytest`, `unittest.mock`.
    -   **Purpose:** Verify the correctness of isolated logic, input validation, and error handling.

-   **Integration Testing:**
    -   **Target:** Interactions between `vidcompress.py`'s functions and mocked external tools (FFmpeg/FFprobe), or between different parts of the `main` function's logic.
    -   **Techniques:** Decision Table Testing, Use Case Testing.
    -   **Tools:** `pytest`, `unittest.mock`.
    -   **Purpose:** Verify that components work together as expected, especially the decision-making logic for transcoding vs. remuxing.

-   **System/End-to-End (E2E) Testing:**
    -   **Target:** The entire `vidcompress.py` application as a black box, executed via its command-line interface, interacting with real FFmpeg/FFprobe and the file system.
    -   **Techniques:** Use Case Testing, State Transition Testing, Checklist-based Testing, Exploratory Testing, Error Guessing.
    -   **Tools:** `pytest`, `subprocess`.
    -   **Purpose:** Verify that the application meets functional and non-functional requirements from a user's perspective, including performance and reliability under realistic conditions.

### 3. Test Types

-   **Functional Testing:**
    -   **Transcoding:** Verify correct conversion of video codecs (H.264 to H.265, VP9 to H.265, etc.) and audio to AAC 2-channel, with correct container output. (FR-TRANSCODE-001)
    -   **Remuxing:** Verify fast container change without re-encoding when codecs are compatible. (FR-REMUX-001)
    -   **File Handling:** Verify `--keep-original` flag behavior (original file retention) and default deletion. (FR-KEEP-ORIGINAL-001)
    -   **Error Handling:** Verify graceful handling of invalid input paths and corrupted files. (FR-ERROR-001)
    -   **Skipping:** Verify that already-processed files are correctly identified and skipped.

-   **Non-Functional Testing:**
    -   **Performance:** Measure transcoding time for a standard video to ensure it meets specified SLAs. (NFR-PERF-001)
    -   **Reliability:** Verify the application's robustness when encountering corrupted or unreadable video files (should not crash, should log and skip). (NFR-RELIABILITY-001)
    -   **Compatibility:** Implicitly covered by using standard FFmpeg/FFprobe and Python 3.x.

-   **Regression Testing:**
    -   All unit, integration, and E2E tests will serve as a regression suite to ensure that new changes do not introduce defects into existing functionality.

### 4. Environments, Data Management, Mocking/Stubbing, and Observability

-   **Test Environments:**
    -   **Local Development:** Developers run unit and integration tests locally.
    -   **CI/CD Pipeline:** Automated execution of all test levels on a dedicated CI runner (e.g., GitHub Actions as indicated by `.github/workflows/`). This environment should have Python 3.x, FFmpeg, and FFprobe installed.
    -   **Operating Systems:** macOS (for VideoToolbox testing) and Linux (for general FFmpeg behavior). Windows compatibility is assumed but not explicitly tested in E2E.

-   **Test Data Management:**
    -   **Generation:** `conftest.py`'s `create_test_video_file` and `test_data_dir` fixtures are used to programmatically generate various valid and corrupted video files.
    -   **Isolation:** `temp_dir` and `setup_test_video` fixtures ensure each test runs in an isolated temporary directory, preventing test interference and ensuring a clean state.
    -   **Realism:** Test videos are small but functionally representative of real-world video files. Corrupted files are specifically crafted to test error handling.

-   **Mocking/Stubbing:**
    -   **Unit Tests:** `unittest.mock.patch` is heavily used to mock `subprocess.run`, `subprocess.Popen`, and file system operations (`os.walk`, `os.path.exists`, `os.remove`, `shutil.move`) to control test conditions and isolate the code under test from external dependencies and the file system.
    -   **Integration Tests:** `unittest.mock.patch` is used to mock `subprocess.run` for `get_media_info` and `subprocess.Popen` for `transcode_file`/`remux_file` when focusing on the `main` function's logic, allowing control over FFmpeg/FFprobe outcomes without actual execution.

-   **Observability:**
    -   **Logging:** The `vidcompress.py` script prints debug and error messages to `stdout` and `stderr`, which are captured by `subprocess.run` in E2E tests for assertion.
    -   **Allure Reports:** `allure-pytest` is used to generate detailed test reports, providing clear visibility into test results, steps, and links to requirements.
    -   **Coverage Reports:** `pytest-cov` generates code coverage reports to identify untested areas.
    -   **Performance Metrics:** E2E performance tests explicitly measure execution time.

### 5. Entry/Exit Criteria and Definition of Done

**Test Entry Criteria:**
-   All requirements (functional and non-functional) are defined and understood.
-   Test environment is set up and stable.
-   Necessary test data is available or can be generated.
-   Development code is feature-complete for the current iteration.
-   Unit tests for new features are written and passing.

**Test Exit Criteria:**
-   All high-priority (P1) functional and non-functional tests pass.
-   Code coverage meets the defined target (e.g., >80% statement and branch coverage).
-   No critical or high-severity open defects.
-   Performance benchmarks are met.
-   Allure reports are generated and reviewed.
-   Regression tests pass.

**Definition of Done (for a feature/story):**
-   Code implemented and reviewed.
-   Unit tests written and passing.
-   Integration tests written and passing.
-   E2E tests written and passing.
-   All relevant test design techniques applied.
-   Code meets project coding standards (linting, formatting).
-   Documentation (e.g., `README.md`, `requirements.yaml`) updated as necessary.
-   Allure report shows successful execution and requirement coverage.

## Technique-to-Coverage Map

This section contains the detailed mapping of requirements to test cases and ISTQB test design techniques, as extracted from `docs/technique_coverage_map.md`.

### Coverage Matrix: {Requirement × Technique × Test Level}

| Requirement ID | Requirement Name | Test Level | ISTQB Technique | Test Case(s) | Coverage Status |
|---|---|---|---|---|---|
| FR-TRANSCODE-001 | Transcode H.264 to H.265 (HEVC) | Unit | Use Case Testing | `test_unit.py::test_main_process_mkv_file` | Covered |
| FR-TRANSCODE-001 | Transcode H.264 to H.265 (HEVC) | Integration | Use Case Testing | `test_integration.py::test_transcode_h264_to_h265` | Covered |
| FR-TRANSCODE-001 | Transcode H.264 to H.265 (HEVC) | System/E2E | Use Case Testing | `test_e2e.py::test_e2e_transcode_h264_to_h265` | Covered |
| FR-REMUX-001 | Remux MKV to MP4 (same codecs) | Unit | Use Case Testing | `test_unit.py::test_main_general_processing_remux_path` | Covered |
| FR-REMUX-001 | Remux MKV to MP4 (same codecs) | Integration | Use Case Testing | `test_integration.py::test_remux_mkv_to_mp4` | Covered |
| FR-REMUX-001 | Remux MKV to MP4 (same codecs) | System/E2E | Use Case Testing | `test_e2e.py::test_e2e_remux_mkv_to_mp4` | Covered |
| FR-KEEP-ORIGINAL-001 | Keep Original File | System/E2E | Use Case Testing | `test_e2e.py::test_e2e_keep_original_flag` | Covered |
| FR-ERROR-001 | Handle Invalid Input Path | Unit | Error Guessing | `test_unit.py::test_cli_invalid_path_error_message` | Covered |
| FR-ERROR-001 | Handle Invalid Input Path | System/E2E | Use Case Testing | `test_e2e.py::test_e2e_invalid_input_path` | Covered |
| NFR-PERF-001 | Transcoding Performance | System/E2E | Exploratory Testing | `test_e2e.py::test_e2e_transcoding_performance` | Covered |
| NFR-RELIABILITY-001 | Robustness to Corrupted Files | System/E2E | Error Guessing | `test_e2e.py::test_e2e_corrupted_file_handling` | Covered |
| - | - | Unit | Equivalence Partitioning | `test_unit.py::test_get_media_info_various_inputs` | Covered (General) |
| - | - | Unit | Boundary Value Analysis | `test_unit.py::test_get_duration_boundary_values` | Covered (General) |
| - | - | Unit | Statement Coverage | `test_unit.py::test_get_ffmpeg_path_statement_coverage`, `test_unit.py::test_get_ffprobe_path_statement_coverage`, `test_unit.py::test_get_media_info_success`, `test_unit.py::test_get_duration`, `test_unit.py::test_is_videotoolbox_available_true`, `test_unit.py::test_is_videotoolbox_available_false`, `test_unit.py::test_transcode_file_success`, `test_unit.py::test_remux_file_success`, `test_unit.py::test_transcode_file_output` | Covered (General) |
| - | - | Unit | Decision Coverage | `test_unit.py::test_is_videotoolbox_available_decision_coverage`, `test_unit.py::test_transcode_file_decision_coverage`, `test_unit.py::test_remux_file_decision_coverage`, `test_unit.py::test_main_remux_existing_temp_file_cleanup`, `test_unit.py::test_main_transcode_existing_temp_file_cleanup`, `test_unit.py::test_main_remux_and_delete_original`, `test_unit.py::test_main_transcode_and_delete_original`, `test_unit.py::test_main_general_processing_remux_path`, `test_unit.py::test_main_general_processing_transcode_path`, `test_unit.py::test_main_existing_output_cleanup` | Covered (General) |
| - | - | Unit | Error Guessing | `test_unit.py::test_get_media_info_file_not_found`, `test_unit.py::test_get_media_info_called_process_error`, `test_unit.py::test_is_videotoolbox_available_error`, `test_unit.py::test_transcode_file_failure`, `test_unit.py::test_remux_file_failure`, `test_unit.py::test_get_media_info_json_decode_error`, `test_unit.py::test_main_invalid_media_info`, `test_unit.py::test_main_error_handling`, `test_unit.py::test_cli_invalid_path`, `test_unit.py::test_main_file_operations_error`, `test_unit.py::test_main_transcode_failure`, `test_unit.py::test_main_remux_failure_cleanup`, `test_unit.py::test_main_transcode_failure_cleanup`, `test_unit.py::test_get_media_info_corrupted_json`, `test_unit.py::test_transcode_file_ffmpeg_not_found`, `test_unit.py::test_remux_file_ffprobe_not_found`, `test_unit.py::test_main_get_media_info_failure`, `test_unit.py::test_main_transcode_failure_message`, `test_unit.py::test_main_remux_failure_message`, `test_unit.py::test_main_makedirs_permission_denied`, `test_unit.py::test_main_remove_original_permission_denied`, `test_unit.py::test_main_move_temp_file_permission_denied`, `test_unit.py::test_main_temp_file_cleanup_failure`, `test_unit.py::test_main_rename_original_to_temp_failure`, `test_unit.py::test_main_copy_original_to_temp_failure`, `test_unit.py::test_main_temp_file_post_move_cleanup_failure`, `test_unit.py::test_main_original_file_post_transcode_cleanup_failure`, `test_unit.py::test_main_original_file_post_remux_cleanup_failure`, `test_unit.py::test_main_rename_original_to_temp_failure_keep_original_false`, `test_unit.py::test_main_copy_original_to_temp_failure_keep_original_false`, `test_unit.py::test_main_temp_file_post_move_cleanup_failure_keep_original_false`, `test_unit.py::test_main_original_file_post_transcode_cleanup_failure_keep_original_false`, `test_unit.py::test_main_original_file_post_remux_cleanup_failure_keep_original_false`, `test_unit.py::test_main_rename_original_to_temp_failure_keep_o... [truncated]
| - | - | Unit | Use Case Testing | `test_unit.py::test_main_empty_folder`, `test_unit.py::test_main_with_non_video_file`, `test_unit.py::test_main_skip_non_video_file`, `test_unit.py::test_main_skip_correct_format`, `test_unit.py::test_main_no_video_stream`, `test_unit.py::test_cli_help`, `test_unit.py::test_cli_with_keep_original`, `test_unit.py::test_cli_without_keep_original` | Covered (General) |
| - | - | Integration | Decision Table Testing | `test_integration.py::test_main_decision_table_scenarios` | Covered (General) |
| - | - | System/E2E | State Transition Testing | `test_e2e.py::test_e2e_state_transitions` | Covered (General) |
| - | - | System/E2E | Checklist-based Testing | `test_e2e.py::test_e2e_all_codec_container_combinations` | Covered (General) |



## Pytest Configuration (`pytest.ini`)
The `pytest.ini` file defines custom markers for categorizing tests:

**Test Levels/Types:**
- `e2e`: End-to-end tests.
- `functional`: Functional tests.
- `non_functional`: Non-functional tests.
- `performance`: Performance tests.
- `reliability`: Reliability tests.
- `unit`: Unit tests.
- `integration`: Integration tests.

**Test Design Techniques:**
- `use_case_testing`
- `state_transition_testing`
- `checklist_based_testing`
- `decision_table_testing`
- `equivalence_partitioning`
- `boundary_value_analysis`
- `statement_coverage`
- `decision_coverage`
- `error_guessing`

**Requirements Traceability:**
- `FR_TRANSCODE_001`: Functional Requirement for transcoding.
- `FR_REMUX_001`: Functional Requirement for remuxing.
- `FR_KEEP_ORIGINAL_001`: Functional Requirement for keeping original files.
- `FR_ERROR_001`: Functional Requirement for error handling.
- `NFR_PERF_001`: Non-Functional Requirement for performance.
- `NFR_RELIABILITY_001`: Non-Functional Requirement for reliability.

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
    - Tests: `test_unit.py::test_transcode_h264_to_h265`, `test_integration.py::test_transcode_h264_to_h265_mocked_ffmpeg`, `test_e2e.py::test_e2e_transcode_h264_to_h265`

- **FR-REMUX-001: Remux MKV to MP4 (same codecs)**
    - Description: Remux MKV to MP4 without re-encoding if codecs are compatible.
    - Priority: High
    - Tags: `remuxing`, `mkv`, `mp4`, `functional`
    - Tests: `test_unit.py::test_remux_mkv_to_mp4`, `test_integration.py::test_remux_mkv_to_mp4_mocked_ffmpeg`, `test_e2e.py::test_e2e_remux_mkv_to_mp4`

- **FR-KEEP-ORIGINAL-001: Keep Original File**
    - Description: Retain original file when `--keep-original` flag is used.
    - Priority: Medium
    - Tags: `file_handling`, `functional`
    - Tests: `test_e2e.py::test_e2e_keep_original_flag`

- **FR-ERROR-001: Handle Invalid Input Path**
    - Description: Exit with error if provided folder path does not exist.
    - Priority: High
    - Tags: `error_handling`, `functional`
    - Tests: `test_e2e.py::test_e2e_invalid_input_path`

### Non-Functional Requirements
- **NFR-PERF-001: Transcoding Performance**
    - Description: Transcode a 1-minute 1080p H.264 video to H.265 within 30 seconds on a standard CI runner.
    - Priority: Medium
    - Tags: `performance`, `non_functional`
    - Tests: `test_e2e.py::test_e2e_transcoding_performance`

- **NFR-RELIABILITY-001: Robustness to Corrupted Files**
    - Description: Gracefully handle corrupted or unreadable video files, skipping and logging errors.
    - Priority: Medium
    - Tags: `reliability`, `non_functional`
    - Tests: `test_e2e.py::test_e2e_corrupted_file_handling`

## Test Technique Coverage (from `docs/technique_coverage_map.md`)

This section summarizes the test technique coverage based on the provided `technique_coverage_map.md`.

**Coverage Matrix Highlights:**
- **FR-TRANSCODE-001 (Transcode H.264 to H.265):** Covered by Unit, Integration, and System/E2E tests using Use Case Testing.
- **FR-REMUX-001 (Remux MKV to MP4):** Covered by Unit, Integration, and System/E2E tests using Use Case Testing.
- **FR-KEEP-ORIGINAL-001 (Keep Original File):** Covered by System/E2E tests using Use Case Testing.
- **FR-ERROR-001 (Handle Invalid Input Path):** Covered by Unit (Error Guessing) and System/E2E (Use Case Testing).
- **NFR-PERF-001 (Transcoding Performance):** Covered by System/E2E tests using Exploratory Testing.
- **NFR-RELIABILITY-001 (Robustness to Corrupted Files):** Covered by System/E2E tests using Error Guessing.

**General Coverage (Unit Level):**
- **Equivalence Partitioning:** `test_unit.py::test_get_media_info_various_inputs`
- **Boundary Value Analysis:** `test_unit.py::test_get_duration_boundary_values`
- **Statement Coverage:** Extensive coverage across various utility functions and core logic (e.g., `get_ffmpeg_path`, `get_media_info`, `transcode_file`, `remux_file`).
- **Decision Coverage:** Covered in `is_videotoolbox_available`, `transcode_file`, `remux_file`, and `main` logic related to file processing and cleanup.
- **Error Guessing:** Comprehensive error handling tests for `get_media_info`, `is_videotoolbox_available`, `transcode_file`, `remux_file`, and various file operations within `main`.
- **Use Case Testing:** Covered for `main` function scenarios like empty folder, non-video files, skipping correct formats, and CLI argument handling.

**General Coverage (Integration Level):**
- **Decision Table Testing:** `test_integration.py::test_main_decision_table_scenarios`

**General Coverage (System/E2E Level):**
- **State Transition Testing:** `test_e2e.py::test_e2e_state_transitions`
- **Checklist-based Testing:** `test_e2e.py::test_e2e_all_codec_container_combinations`

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
- **Mocking:** Extensively uses `unittest.mock.patch` to mock external dependencies like `subprocess.run`, `subprocess.Popen`, `os.walk`, `os.path.exists`, `os.remove`, `shutil.move`, `shutil.copy2`, and `sys.stderr` to control test conditions and isolate the unit under test.
- **Coverage:** Aims for high statement and decision coverage for utility functions (`get_ffmpeg_path`, `get_ffprobe_path`, `get_media_info`, `get_duration`, `is_videotoolbox_available`) and core logic within `main`.
- **Techniques:** Employs Equivalence Partitioning, Boundary Value Analysis, Error Guessing, and Decision Coverage for thorough testing of various inputs and error conditions.
- **Key Tests:** Covers successful media info retrieval, error handling for file not found/subprocess errors, duration calculation, VideoToolbox availability, transcode/remux success/failure, CLI argument parsing, and various file operation error scenarios within `main`.

### `test_integration.py`
- **Focus:** Tests the interaction between different modules and components of `vidcompress.py`, often with mocked external tools (FFmpeg/FFprobe) but real file system operations.
- **Techniques:** Primarily uses Use Case Testing and Decision Table Testing to cover various scenarios of transcoding, remuxing, and file handling.
- **Key Tests:** Includes tests for processing empty folders, folders with non-video files, transcoding H.264 to H.265, remuxing MKV to MP4, transcoding VP9 to H.265, and handling nested folders. The `test_main_decision_table_scenarios` specifically covers different combinations of codec/container matches to verify the core decision logic.

### `test_e2e.py`
- **Focus:** Tests the entire application flow from command-line invocation to file system changes, using actual FFmpeg/FFprobe execution (not mocked).
- **Techniques:** Utilizes Use Case Testing for functional requirements, Exploratory Testing for performance, Error Guessing for reliability, State Transition Testing for sequential operations, and Checklist-based Testing for comprehensive codec/container combinations.
- **Key Tests:** Covers end-to-end scenarios for transcoding (H.264 to H.265), remuxing (MKV to MP4), `--keep-original` flag functionality, invalid input path handling, transcoding performance, robustness to corrupted files, and state transitions (e.2., H264->H265 then H265->VP9). The `test_e2e_all_codec_container_combinations` systematically checks all defined codec and container targets.

### Overall Testing Approach
- **Layered Testing:** The project follows a layered testing approach (Unit -> Integration -> E2E) to ensure comprehensive coverage and efficient defect localization.
- **Requirement Traceability:** Pytest markers and Allure annotations are used to link tests directly to functional and non-functional requirements, as well as ISTQB test design techniques.
- **Test Data Management:** Fixtures in `conftest.py` are used to generate and manage test video files, ensuring consistent and isolated test environments.
- **Error Handling:** Extensive tests are in place to verify the application's robustness against various error conditions, including invalid inputs, file system issues, and subprocess failures.
- **CI/CD Integration:** The use of Pytest and Allure suggests an intention for automated testing within a CI/CD pipeline, with detailed reporting capabilities.

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
    - Tests: `test_unit.py::test_transcode_h264_to_h265`, `test_integration.py::test_transcode_h264_to_h265_mocked_ffmpeg`, `test_e2e.py::test_e2e_transcode_h264_to_h265`

- **FR-REMUX-001: Remux MKV to MP4 (same codecs)**
    - Description: Remux MKV to MP4 without re-encoding if codecs are compatible.
    - Priority: High
    - Tags: `remuxing`, `mkv`, `mp4`, `functional`
    - Tests: `test_unit.py::test_remux_mkv_to_mp4`, `test_integration.py::test_remux_mkv_to_mp4_mocked_ffmpeg`, `test_e2e.py::test_e2e_remux_mkv_to_mp4`

- **FR-KEEP-ORIGINAL-001: Keep Original File**
    - Description: Retain original file when `--keep-original` flag is used.
    - Priority: Medium
    - Tags: `file_handling`, `functional`
    - Tests: `test_e2e.py::test_e2e_keep_original_flag`

- **FR-ERROR-001: Handle Invalid Input Path**
    - Description: Exit with error if provided folder path does not exist.
    - Priority: High
    - Tags: `error_handling`, `functional`
    - Tests: `test_e2e.py::test_e2e_invalid_input_path`

### Non-Functional Requirements
- **NFR-PERF-001: Transcoding Performance**
    - Description: Transcode a 1-minute 1080p H.264 video to H.265 within 30 seconds on a standard CI runner.
    - Priority: Medium
    - Tags: `performance`, `non_functional`
    - Tests: `test_e2e.py::test_e2e_transcoding_performance`

- **NFR-RELIABILITY-001: Robustness to Corrupted Files**
    - Description: Gracefully handle corrupted or unreadable video files, skipping and logging errors.
    - Priority: Medium
    - Tags: `reliability`, `non_functional`
    - Tests: `test_e2e.py::test_e2e_corrupted_file_handling`

## Test Technique Coverage (from `docs/technique_coverage_map.md`)

This section summarizes the test technique coverage based on the provided `technique_coverage_map.md`.

**Coverage Matrix Highlights:**
- **FR-TRANSCODE-001 (Transcode H.264 to H.265):** Covered by Unit, Integration, and System/E2E tests using Use Case Testing.
- **FR-REMUX-001 (Remux MKV to MP4):** Covered by Unit, Integration, and System/E2E tests using Use Case Testing.
- **FR-KEEP-ORIGINAL-001 (Keep Original File):** Covered by System/E2E tests using Use Case Testing.
- **FR-ERROR-001 (Handle Invalid Input Path):** Covered by Unit (Error Guessing) and System/E2E (Use Case Testing).
- **NFR-PERF-001 (Transcoding Performance):** Covered by System/E2E tests using Exploratory Testing.
- **NFR-RELIABILITY-001 (Robustness to Corrupted Files):** Covered by System/E2E tests using Error Guessing.

**General Coverage (Unit Level):**
- **Equivalence Partitioning:** `test_unit.py::test_get_media_info_various_inputs`
- **Boundary Value Analysis:** `test_unit.py::test_get_duration_boundary_values`
- **Statement Coverage:** Extensive coverage across various utility functions and core logic (e.g., `get_ffmpeg_path`, `get_media_info`, `transcode_file`, `remux_file`).
- **Decision Coverage:** Covered in `is_videotoolbox_available`, `transcode_file`, `remux_file`, and `main` logic related to file processing and cleanup.
- **Error Guessing:** Comprehensive error handling tests for `get_media_info`, `is_videotoolbox_available`, `transcode_file`, `remux_file`, and various file operations within `main`.
- **Use Case Testing:** Covered for `main` function scenarios like empty folder, non-video files, skipping correct formats, and CLI argument handling.

**General Coverage (Integration Level):**
- **Decision Table Testing:** `test_integration.py::test_main_decision_table_scenarios`

**General Coverage (System/E2E Level):**
- **State Transition Testing:** `test_e2e.py::test_e2e_state_transitions`
- **Checklist-based Testing:** `test_e2e.py::test_e2e_all_codec_container_combinations`

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
    - Tests: `test_unit.py::test_transcode_h264_to_h265`, `test_integration.py::test_transcode_h264_to_h265_mocked_ffmpeg`, `test_e2e.py::test_e2e_transcode_h264_to_h265`

- **FR-REMUX-001: Remux MKV to MP4 (same codecs)**
    - Description: Remux MKV to MP4 without re-encoding if codecs are compatible.
    - Priority: High
    - Tags: `remuxing`, `mkv`, `mp4`, `functional`
    - Tests: `test_unit.py::test_remux_mkv_to_mp4`, `test_integration.py::test_remux_mkv_to_mp4_mocked_ffmpeg`, `test_e2e.py::test_e2e_remux_mkv_to_mp4`

- **FR-KEEP-ORIGINAL-001: Keep Original File**
    - Description: Retain original file when `--keep-original` flag is used.
    - Priority: Medium
    - Tags: `file_handling`, `functional`
    - Tests: `test_e2e.py::test_e2e_keep_original_flag`

- **FR-ERROR-001: Handle Invalid Input Path**
    - Description: Exit with error if provided folder path does not exist.
    - Priority: High
    - Tags: `error_handling`, `functional`
    - Tests: `test_e2e.py::test_e2e_invalid_input_path`

### Non-Functional Requirements
- **NFR-PERF-001: Transcoding Performance**
    - Description: Transcode a 1-minute 1080p H.264 video to H.265 within 30 seconds on a standard CI runner.
    - Priority: Medium
    - Tags: `performance`, `non_functional`
    - Tests: `test_e2e.py::test_e2e_transcoding_performance`

- **NFR-RELIABILITY-001: Robustness to Corrupted Files**
    - Description: Gracefully handle corrupted or unreadable video files, skipping and logging errors.
    - Priority: Medium
    - Tags: `reliability`, `non_functional`
    - Tests: `test_e2e.py::test_e2e_corrupted_file_handling`

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

