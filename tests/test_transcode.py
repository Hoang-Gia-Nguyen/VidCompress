import pytest
from pathlib import Path
from app.transcoder import extract_subtitles, get_video_info, process_video, ProcessStatus

@pytest.mark.parametrize("path, needs_transcoding, video_codec, audio_codec", [
    ("tests/videos_temp/test_need_transcode.mkv", True, "h264", ["eac3"]), # need transcode
    ("tests/videos_temp/test_no_transcode.mp4", False, "hevc", ["aac"]), # no transcode
])
def test_get_video_info(path, needs_transcoding, video_codec, audio_codec):
    path_obj = Path(path)
    info = get_video_info(path)
    assert info['needs_transcoding'] == needs_transcoding
    assert info['video_codec'] == video_codec
    assert info['audio_codec'] == audio_codec


@pytest.mark.parametrize("file_path", [
    #("tests/videos_temp/test_need_transcode.mkv"), # no subtitle
    ("tests/videos_temp/test_subtitles_extract.mp4"), # subtitle
])
def test_extract_subtitles(file_path):
    file_obj = Path(file_path)
    folder_path = file_obj.parent
    folder_obj = Path(folder_path)
    extract_subtitles(file_obj, folder_obj)
    #breakpoint()
    srt_files = list(folder_obj.glob("*.srt"))
    assert len(srt_files) > 0, f"No .srt file found in {folder_path}"


@pytest.mark.parametrize("file_path, needs_transcoding", [
    ("tests/videos_temp/test_need_transcode.mkv", True), # no subtitle
    ("tests/videos_temp/test_no_transcode.mp4", False), # subtitle
])
def test_process_video(file_path, needs_transcoding):
    file_obj = Path(file_path)
    status = process_video(file_obj)
    if not file_obj.exists():
        assert status == ProcessStatus.FILE_NOT_FOUND
    elif needs_transcoding:
        info = get_video_info(file_obj)
        assert status == ProcessStatus.SUCCESS
        assert info['needs_transcoding'] == False
        original_file_obj = Path(file_path + '.originalmedia')
        assert original_file_obj.exists()
    else:
        assert status == ProcessStatus.SKIPPED

#TODO: Write a test case use mock to simulate ffmpeg fail, return ProcessStatus.ERROR