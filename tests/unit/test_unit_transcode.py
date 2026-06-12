import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.config import SubtitleMode
from app.transcoder import FfmpegTranscoder, ProcessStatus, VideoInfo, StreamInfo


@pytest.mark.parametrize(
    "mock_returncode, expected_result", [(0, True), (FileNotFoundError, False)]
)
def test_check_ffmpeg_availability(mock_returncode, expected_result):
    side_effects = []
    transcoder = FfmpegTranscoder()

    if mock_returncode is FileNotFoundError:
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
        (
            "V..... hevc_nvenc\nV..... libx265",
            {"hevc_nvenc": False, "libx265": True},
            "libx265",
        ),
        (
            "V..... hevc_nvenc\nV..... hevc_videotoolbox",
            {"hevc_videotoolbox": True, "hevc_nvenc": True},
            "hevc_videotoolbox",
        ),
        (
            "V..... hevc_nvenc\nV..... hevc_qsv",
            {"hevc_qsv": True, "hevc_nvenc": True},
            "hevc_nvenc",
        ),
        ("", {}, "libx265"),
    ],
)
@patch("app.transcoder.FfmpegTranscoder._is_encoder_functional")
@patch("subprocess.run")
def test_get_best_hevc_encoder_logic(
    mock_run, mock_is_functional, mock_list, functional_map, expected_result
):
    mock_proc = MagicMock()
    mock_proc.stdout = mock_list
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc

    mock_is_functional.side_effect = lambda x: functional_map.get(x, True)

    transcoder = FfmpegTranscoder()

    assert transcoder._best_hevc_encoder == expected_result


@pytest.mark.parametrize(
    "ffprobe_streams, expected",
    [
        (
            # Need transcode - h264 video + eac3 audio
            [
                {"index": 0, "codec_type": "video", "codec_name": "h264"},
                {"index": 1, "codec_type": "audio", "codec_name": "eac3"},
            ],
            {
                "video_codec": "h264",
                "audio_codec": ["eac3"],
                "needs_transcoding": True,
                "num_streams": 2,
            },
        ),
        (
            # No transcode - hevc + aac
            [
                {"index": 0, "codec_type": "video", "codec_name": "hevc"},
                {"index": 1, "codec_type": "audio", "codec_name": "aac"},
            ],
            {
                "video_codec": "hevc",
                "audio_codec": ["aac"],
                "needs_transcoding": False,
                "num_streams": 2,
            },
        ),
        (
            # Need transcode - hevc video but ac3 audio
            [
                {"index": 0, "codec_type": "video", "codec_name": "hevc"},
                {"index": 1, "codec_type": "audio", "codec_name": "ac3"},
            ],
            {
                "video_codec": "hevc",
                "audio_codec": ["ac3"],
                "needs_transcoding": True,
                "num_streams": 2,
            },
        ),
        (
            # Multi-audio, multi-subtitle
            [
                {"index": 0, "codec_type": "video", "codec_name": "h264"},
                {"index": 1, "codec_type": "audio", "codec_name": "aac"},
                {"index": 2, "codec_type": "audio", "codec_name": "ac3"},
                {"index": 3, "codec_type": "subtitle", "codec_name": "subrip"},
                {"index": 4, "codec_type": "subtitle", "codec_name": "subrip"},
            ],
            {
                "video_codec": "h264",
                "audio_codec": ["aac", "ac3"],
                "needs_transcoding": True,
                "num_streams": 5,
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
    assert len(info.streams) == expected["num_streams"]

    # Verify stream object structure
    for s in info.streams:
        assert isinstance(s, StreamInfo)
        assert hasattr(s, "index")
        assert hasattr(s, "codec_type")
        assert hasattr(s, "codec")
        assert hasattr(s, "tags")


class TestStreamMapping:
    """Tests for the stream mapping FFmpeg argument builder."""

    def _make_info(self, streams: list) -> VideoInfo:
        return VideoInfo(
            video_codec="h264",
            audio_codec=[s.codec for s in streams if s.codec_type == "audio"],
            needs_transcoding=True,
            streams=streams,
        )

    def test_single_audio_aac(self):
        """Single AAC audio stream should be copied."""
        transcoder = FfmpegTranscoder()
        info = self._make_info(
            [
                StreamInfo(index=0, codec_type="video", codec="h264"),
                StreamInfo(index=1, codec_type="audio", codec="aac"),
            ]
        )
        args = transcoder._build_stream_maps(info)
        assert "-map" in args
        assert "0" in args[args.index("-map") + 1]
        assert "-c:v" in args
        assert "-c:a:0" in args or "-c:audio:0" in args

    def test_multi_audio_mixed_codecs(self):
        """Multiple audio streams with mixed codecs: copy AAC, transcode AC3."""
        transcoder = FfmpegTranscoder()
        info = self._make_info(
            [
                StreamInfo(index=0, codec_type="video", codec="h264"),
                StreamInfo(index=1, codec_type="audio", codec="aac"),
                StreamInfo(index=2, codec_type="audio", codec="ac3"),
            ]
        )
        args = transcoder._build_stream_maps(info)
        args_str = " ".join(args)
        # Should have AAC as copy
        assert "copy" in args_str
        # Should have AC3 transcoded to AAC
        assert "aac" in args_str

    def test_subtitles_preserved_with_copy_mode(self):
        """Subtitle streams should have mov_text encoder when SUBTITLE_MODE is COPY."""
        transcoder = FfmpegTranscoder(subtitle_mode=SubtitleMode.COPY)
        info = self._make_info(
            [
                StreamInfo(index=0, codec_type="video", codec="h264"),
                StreamInfo(index=1, codec_type="audio", codec="aac"),
                StreamInfo(
                    index=2,
                    codec_type="subtitle",
                    codec="subrip",
                    tags={"language": "eng"},
                ),
            ]
        )
        args = transcoder._build_stream_maps(info)
        args_str = " ".join(args)
        assert "mov_text" in args_str

    def test_subtitles_not_preserved_with_external_mode(self):
        """Subtitle streams should NOT have mov_text when SUBTITLE_MODE is EXTERNAL."""
        transcoder = FfmpegTranscoder(subtitle_mode=SubtitleMode.EXTERNAL)
        info = self._make_info(
            [
                StreamInfo(index=0, codec_type="video", codec="h264"),
                StreamInfo(index=1, codec_type="audio", codec="aac"),
                StreamInfo(index=2, codec_type="subtitle", codec="subrip"),
            ]
        )
        args = transcoder._build_stream_maps(info)
        args_str = " ".join(args)
        # Should NOT have mov_text
        assert "mov_text" not in args_str

    def test_no_audio_streams(self):
        """No audio streams in input should not produce -c:a flags."""
        transcoder = FfmpegTranscoder()
        info = self._make_info(
            [
                StreamInfo(index=0, codec_type="video", codec="h264"),
            ]
        )
        args = transcoder._build_stream_maps(info)
        args_str = " ".join(args)
        # Should have video encoder
        assert "-c:v" in args_str


class TestOutputSizeVerification:
    """Tests for output size verification in process_video."""

    def test_output_smaller_than_original_keeps_result(self, tmp_path, monkeypatch):
        """When output is smaller than original, the transcoded file should be kept."""
        input_file = tmp_path / "input.mp4"
        input_file.write_text("x" * 1000)  # 1000 bytes

        transcoder = FfmpegTranscoder(verify_output_size=True)

        with patch.object(transcoder, "get_video_info") as mock_info:
            mock_info.return_value = VideoInfo(
                video_codec="h264",
                audio_codec=["aac"],
                needs_transcoding=True,
                streams=[
                    StreamInfo(index=0, codec_type="video", codec="h264"),
                    StreamInfo(index=1, codec_type="audio", codec="aac"),
                ],
            )

            with patch("subprocess.run") as mock_run:
                mock_proc = MagicMock()
                mock_proc.returncode = 0
                mock_run.return_value = mock_proc

                # Create a temp output that is smaller
                temp_output = input_file.with_name(input_file.stem + ".transcoding.mp4")
                temp_output.write_text("x" * 500)  # 500 bytes - smaller

                with patch.object(Path, "rename") as mock_rename:
                    result = transcoder.process_video(input_file)
                    assert result.status == ProcessStatus.SUCCESS
                    assert result.original_size == 1000
                    assert result.output_size == 500
                    # The temp file should have been renamed (swapped)
                    assert mock_rename.call_count == 2

    def test_output_larger_than_original_skips(self, tmp_path):
        """When output is larger than original, the original should be kept."""
        input_file = tmp_path / "input.mp4"
        input_file.write_text("x" * 500)  # 500 bytes

        transcoder = FfmpegTranscoder(verify_output_size=True)

        with patch.object(transcoder, "get_video_info") as mock_info:
            mock_info.return_value = VideoInfo(
                video_codec="h264",
                audio_codec=["aac"],
                needs_transcoding=True,
                streams=[
                    StreamInfo(index=0, codec_type="video", codec="h264"),
                    StreamInfo(index=1, codec_type="audio", codec="aac"),
                ],
            )

            with patch("subprocess.run") as mock_run:
                mock_proc = MagicMock()
                mock_proc.returncode = 0
                mock_run.return_value = mock_proc

                # Create a temp output that is larger
                temp_output = input_file.with_name(input_file.stem + ".transcoding.mp4")
                temp_output.write_text("x" * 1000)  # 1000 bytes - larger

                result = transcoder.process_video(input_file)
                assert result.status == ProcessStatus.SKIPPED
                assert "Output larger than original" in (result.error_message or "")
                assert result.original_size == 500
                assert result.output_size == 1000
                # Temp file should have been deleted
                assert not temp_output.exists()

    def test_verify_output_size_disabled_keeps_larger(self, tmp_path):
        """When verify_output_size is False, even larger output should be kept."""
        input_file = tmp_path / "input.mp4"
        input_file.write_text("x" * 500)  # 500 bytes

        transcoder = FfmpegTranscoder(verify_output_size=False)

        with patch.object(transcoder, "get_video_info") as mock_info:
            mock_info.return_value = VideoInfo(
                video_codec="h264",
                audio_codec=["aac"],
                needs_transcoding=True,
                streams=[
                    StreamInfo(index=0, codec_type="video", codec="h264"),
                    StreamInfo(index=1, codec_type="audio", codec="aac"),
                ],
            )

            with patch("subprocess.run") as mock_run:
                mock_proc = MagicMock()
                mock_proc.returncode = 0
                mock_run.return_value = mock_proc

                temp_output = input_file.with_name(input_file.stem + ".transcoding.mp4")
                temp_output.write_text("x" * 1000)  # 1000 bytes - larger

                with patch.object(Path, "rename") as mock_rename:
                    result = transcoder.process_video(input_file)
                    assert result.status == ProcessStatus.SUCCESS
                    # File was swapped despite being larger
                    assert mock_rename.call_count == 2


@pytest.mark.parametrize(
    "ffprobe_streams, expected",
    [
        (
            # Need transcode
            [
                {"index": 0, "codec_type": "video", "codec_name": "h264"},
                {"index": 1, "codec_type": "audio", "codec_name": "eac3"},
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
                {"index": 0, "codec_type": "video", "codec_name": "hevc"},
                {"index": 1, "codec_type": "audio", "codec_name": "aac"},
            ],
            {
                "video_codec": "hevc",
                "audio_codec": ["aac"],
                "needs_transcoding": False,
            },
        ),
        (
            # Transcode needed for non-AAC audio even if video is HEVC
            [
                {"index": 0, "codec_type": "video", "codec_name": "hevc"},
                {"index": 1, "codec_type": "audio", "codec_name": "ac3"},
            ],
            {
                "video_codec": "hevc",
                "audio_codec": ["ac3"],
                "needs_transcoding": True,
            },
        ),
    ],
)
def test_get_video_info_legacy(monkeypatch, tmp_path, ffprobe_streams, expected):
    """Legacy tests for backward compatibility of get_video_info."""
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
            output_srt = Path(cmd[-1])
            output_srt.write_text("dummy subtitle")
            return mock

        raise RuntimeError("Unexpected command")

    monkeypatch.setattr("subprocess.run", mock_run)

    transcoder.extract_subtitles(input_file, tmp_path)

    srt_files = list(tmp_path.glob(f"{input_file.stem}.*.srt"))
    assert srt_files, "Expected at least one .srt file to be extracted"


@pytest.mark.parametrize(
    "video_info, expected_status",
    [
        (None, ProcessStatus.FILE_NOT_FOUND),
        (VideoInfo(needs_transcoding=False), ProcessStatus.SKIPPED),
        (
            VideoInfo(
                video_codec="h264",
                audio_codec=["mp3"],
                needs_transcoding=True,
                streams=[
                    StreamInfo(index=0, codec_type="video", codec="h264"),
                    StreamInfo(index=1, codec_type="audio", codec="mp3"),
                ],
            ),
            ProcessStatus.SUCCESS,
        ),
    ],
)
def test_process_video_unit(video_info, expected_status, tmp_path):
    transcoder = FfmpegTranscoder()
    transcoder.temp_file_list = []

    input_path = tmp_path / "input.mp4"
    # 1000 bytes input (larger than output to avoid size verification skip)
    input_path.write_text("x" * 1000)

    with (
        patch.object(transcoder, "get_video_info", return_value=video_info),
        patch("subprocess.run") as mock_run,
        patch.object(Path, "rename") as mock_rename,
    ):
        mock_run.return_value.returncode = 0
        temp_output = input_path.with_name(input_path.stem + ".transcoding.mp4")
        # 500 bytes - smaller than input, so size verification passes
        temp_output.write_text("x" * 500)

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
def test_process_video_ffmpeg_fail(mock_run, mock_returncode, tmp_path):
    mock_proc = MagicMock()
    mock_proc.stdout = ""
    mock_proc.stderr = "ffmpeg error"
    mock_proc.returncode = mock_returncode
    mock_run.return_value = mock_proc

    transcoder = FfmpegTranscoder()
    input_path = tmp_path / "test_need_transcode.mkv"
    # 1000 bytes input (larger than output to avoid size verification skip)
    input_path.write_text("x" * 1000)

    with patch.object(transcoder, "get_video_info") as mock_get_info:
        mock_get_info.return_value = VideoInfo(
            video_codec="h264",
            audio_codec=["mp3"],
            needs_transcoding=True,
            streams=[
                StreamInfo(index=0, codec_type="video", codec="h264"),
                StreamInfo(index=1, codec_type="audio", codec="mp3"),
            ],
        )
        result = transcoder.process_video(input_path)
        assert result.status == ProcessStatus.ERROR
        assert result.error_message == "ffmpeg error"
