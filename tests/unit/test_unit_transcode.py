import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.transcoder import FfmpegTranscoder, ProcessStatus, VideoInfo


@pytest.mark.parametrize(
    "mock_returncode, expected_result", [(0, True), (FileNotFoundError, False)]
)
def test_check_ffmpeg_availability(mock_returncode, expected_result):
    side_effects = []
    transcoder = FfmpegTranscoder()

    if mock_returncode == FileNotFoundError:  # noqa: E721
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


@pytest.mark.parametrize(
    "mock_list, functional_map, expected_result",
    [
        # Scenario 1: NVENC có trong list nhưng check phần cứng thất bại -> Về libx265
        (
            "V..... hevc_nvenc\nV..... libx265",
            {"hevc_nvenc": False, "libx265": True},
            "libx265",
        ),
        # Scenario 2: VideoToolbox ưu tiên cao nhất và pass check
        (
            "V..... hevc_nvenc\nV..... hevc_videotoolbox",
            {"hevc_videotoolbox": True, "hevc_nvenc": True},
            "hevc_videotoolbox",
        ),
        # Scenario 3: Cả NVENC và QSV đều có, NVENC thường ưu tiên hơn QSV (tùy logic của bạn)
        (
            "V..... hevc_nvenc\nV..... hevc_qsv",
            {"hevc_qsv": True, "hevc_nvenc": True},
            "hevc_nvenc",
        ),
        # Scenario 4: List trống hoặc không khớp -> Fallback mặc định
        ("", {}, "libx265"),
    ],
)
@patch("app.transcoder.FfmpegTranscoder._is_encoder_functional")
@patch("subprocess.run")
def test_get_best_hevc_encoder_logic(
    mock_run, mock_is_functional, mock_list, functional_map, expected_result
):
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


@pytest.mark.parametrize(
    "ffprobe_streams, expected",
    [
        (
            # Need transcode
            [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "eac3"},
            ],
            {
                "video_codec": "h264",
                "audio_codec": ["eac3"],
                "needs_transcoding": True,
            },
        ),
        (
            # No transcode
            [
                {"codec_type": "video", "codec_name": "hevc"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            {
                "video_codec": "hevc",
                "audio_codec": ["aac"],
                "needs_transcoding": False,
            },
        ),
    ],
)
def test_get_video_info(monkeypatch, tmp_path, ffprobe_streams, expected):
    transcoder = FfmpegTranscoder()

    input_file = tmp_path / "video.mp4"
    input_file.write_text("dummy")

    ffprobe_output = {
        "streams": ffprobe_streams,
        "format": {"duration": "123.45"},
    }

    def mock_run(cmd, capture_output=True, text=True, check=True):
        mock = Mock()
        mock.stdout = json.dumps(ffprobe_output)
        return mock

    monkeypatch.setattr("subprocess.run", mock_run)

    info = transcoder.get_video_info(input_file)

    assert info.video_codec == expected["video_codec"]
    assert info.audio_codec == expected["audio_codec"]
    assert info.needs_transcoding == expected["needs_transcoding"]
    assert info.duration == 123.45


@pytest.mark.parametrize(
    "file_path",
    [
        "tests/videos_temp/test_subtitles_extract.mp4",
    ],
)
def test_extract_subtitles_creates_srt_files(tmp_path, monkeypatch, file_path):
    transcoder = FfmpegTranscoder()
    input_file = Path(file_path)

    # Fake ffprobe output: 1 subtitle stream
    ffprobe_output = {
        "streams": [
            {"index": 2, "tags": {"language": "eng"}},
        ]
    }

    def mock_run(cmd, capture_output=True, text=True, check=True):
        mock = Mock()

        if cmd[0] == "ffprobe":
            mock.stdout = json.dumps(ffprobe_output)
            return mock

        if cmd[0] == "ffmpeg":
            # ffmpeg normally creates the file → we simulate it
            output_srt = Path(cmd[-1])
            output_srt.write_text("dummy subtitle")
            return mock

        raise RuntimeError("Unexpected command")

    monkeypatch.setattr("subprocess.run", mock_run)

    # Act
    transcoder.extract_subtitles(input_file, tmp_path)

    # Assert
    srt_files = list(tmp_path.glob(f"{input_file.stem}.*.srt"))
    assert srt_files, "Expected at least one .srt file to be extracted"


@pytest.mark.parametrize(
    "video_info, expected_status",
    [
        (None, ProcessStatus.FILE_NOT_FOUND),
        (VideoInfo(needs_transcoding=False), ProcessStatus.SKIPPED),
        (
            VideoInfo(video_codec="h264", audio_codec="mp3", needs_transcoding=True),
            ProcessStatus.SUCCESS,
        ),
    ],
)
def test_process_video_unit(video_info, expected_status):
    transcoder = FfmpegTranscoder()
    transcoder.temp_file_list = []

    input_path = Path("/fake/input.mp4")

    with patch.object(transcoder, "get_video_info", return_value=video_info), patch(
        "subprocess.run"
    ) as mock_run, patch.object(Path, "rename") as mock_rename, patch.object(
        Path,
        "with_suffix",
        side_effect=lambda s: Path(str(input_path).replace(".mp4", s)),
    ):
        mock_run.return_value.returncode = 0
        result = transcoder.process_video(input_path)

        assert result.status == expected_status

        if expected_status == ProcessStatus.SUCCESS:
            mock_run.assert_called_once()
            assert mock_rename.call_count == 2
            assert len(transcoder.temp_file_list) == 1
        else:
            mock_run.assert_not_called()
            mock_rename.assert_not_called()
            assert transcoder.temp_file_list == []


@pytest.mark.parametrize(
    "mock_returncode",
    [1],
)
@patch("subprocess.run")
def test_process_video_ffmpeg_fail(mock_run, mock_returncode):
    mock_proc = MagicMock()
    mock_proc.stdout = ""
    mock_proc.stderr = "ffmpeg error"
    mock_proc.returncode = mock_returncode
    mock_run.return_value = mock_proc

    transcoder = FfmpegTranscoder()
    file_obj = Path("tests/videos_temp/test_need_transcode.mkv")
    
    with patch.object(transcoder, "get_video_info") as mock_get_info:
        mock_get_info.return_value = VideoInfo(video_codec="h264", audio_codec=["mp3"], needs_transcoding=True)
        result = transcoder.process_video(file_obj)
        assert result.status == ProcessStatus.ERROR
        assert result.error_message == "ffmpeg error"
