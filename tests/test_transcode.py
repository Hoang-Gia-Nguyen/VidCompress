import pytest
from pathlib import Path
from app.transcoder import FfmpegTranscoder, ProcessStatus
from unittest.mock import patch, MagicMock

@pytest.mark.parametrize("mock_returncode, expected_result", [
    (0, True),
    (FileNotFoundError, False)
])
def test_check_ffmpeg_availability(mock_returncode, expected_result):
    side_effects = []
    transcoder = FfmpegTranscoder()

    if mock_returncode == FileNotFoundError:
        side_effects = [FileNotFoundError, FileNotFoundError]
    else:
        mock_ffmpeg = MagicMock()
        mock_ffmpeg.stdout = "ffmpeg version 6.0"
        mock_ffmpeg.returncode = mock_returncode

        mock_ffprobe = MagicMock()
        mock_ffprobe.stdout = "ffprobe version 6.0"
        mock_ffprobe.returncode = mock_returncode

        side_effects = [mock_ffmpeg, mock_ffprobe]

    with patch("subprocess.run") as mocked_run:
        mocked_run.side_effect = side_effects
        availability_info = transcoder.check_availability()
        assert availability_info["ffmpeg"]["available"] is expected_result
        assert availability_info["ffprobe"]["available"] is expected_result
        assert mocked_run.call_count == 2

@pytest.mark.parametrize("mock_list, functional_map, expected_result", [
    # Scenario 1: NVENC có trong list nhưng check phần cứng thất bại -> Về libx265
    ("V..... hevc_nvenc\nV..... libx265", {"hevc_nvenc": False, "libx265": True}, "libx265"),
    
    # Scenario 2: VideoToolbox ưu tiên cao nhất và pass check
    ("V..... hevc_nvenc\nV..... hevc_videotoolbox", {"hevc_videotoolbox": True, "hevc_nvenc": True}, "hevc_videotoolbox"),

    # Scenario 3: Cả NVENC và QSV đều có, NVENC thường ưu tiên hơn QSV (tùy logic của bạn)
    ("V..... hevc_nvenc\nV..... hevc_qsv", {"hevc_qsv": True, "hevc_nvenc": True}, "hevc_nvenc"),
    
    # Scenario 4: List trống hoặc không khớp -> Fallback mặc định
    ("", {}, "libx265"),
])
@patch("app.transcoder.FfmpegTranscoder._is_encoder_functional")
@patch("subprocess.run")
def test_get_best_hevc_encoder_logic(mock_run, mock_is_functional, mock_list, functional_map, expected_result):
    # 1. SETUP MOCKS FIRST
    # We create a mock object that behaves like a completed process
    mock_proc = MagicMock()
    mock_proc.stdout = mock_list
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc

    # Setup the functional check
    mock_is_functional.side_effect = lambda x: functional_map.get(x, True)

    # 2. INSTANTIATE SECOND
    # Now when __init__ calls the methods, the mocks are ready with strings
    transcoder = FfmpegTranscoder()

    # 4. Assert
    assert transcoder._best_hevc_encoder == expected_result

@pytest.mark.parametrize("path, needs_transcoding, video_codec, audio_codec", [
    ("tests/videos_temp/test_need_transcode.mkv", True, "h264", ["eac3"]), # need transcode
    ("tests/videos_temp/test_no_transcode.mp4", False, "hevc", ["aac"]), # no transcode
])
def test_get_video_info(path, needs_transcoding, video_codec, audio_codec):
    transcoder = FfmpegTranscoder()
    path_obj = Path(path)
    info = transcoder.get_video_info(path_obj)
    assert info['needs_transcoding'] == needs_transcoding
    assert info['video_codec'] == video_codec
    assert info['audio_codec'] == audio_codec


@pytest.mark.parametrize("file_path", [
    #("tests/videos_temp/test_need_transcode.mkv"), # no subtitle
    ("tests/videos_temp/test_subtitles_extract.mp4"), # subtitle
])
def test_extract_subtitles(file_path):
    transcoder = FfmpegTranscoder()
    file_obj = Path(file_path)
    folder_path = file_obj.parent
    folder_obj = Path(folder_path)
    transcoder.extract_subtitles(file_obj, folder_obj)
    #breakpoint()
    srt_files = list(folder_obj.glob("*.srt"))
    assert len(srt_files) > 0, f"No .srt file found in {folder_path}"


@pytest.mark.parametrize("file_path, needs_transcoding", [
    ("tests/videos_temp/test_need_transcode.mkv", True), # no subtitle
    ("tests/videos_temp/test_no_transcode.mp4", False), # subtitle
])
def test_process_video(file_path, needs_transcoding):
    transcoder = FfmpegTranscoder()
    file_obj = Path(file_path)
    status = transcoder.process_video(file_obj)
    if not file_obj.exists():
        assert status == ProcessStatus.FILE_NOT_FOUND
    elif needs_transcoding:
        info = transcoder.get_video_info(file_obj)
        assert status == ProcessStatus.SUCCESS
        assert info['needs_transcoding'] == False
        original_file_obj = Path(file_path + '.originalmedia')
        assert original_file_obj.exists()
    else:
        assert status == ProcessStatus.SKIPPED

#TODO: Write a test case use mock to simulate ffmpeg fail, return ProcessStatus.ERROR