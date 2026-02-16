from pathlib import Path

from media_scanner import list_media_files, manage_backups
from transcoder import get_video_info, extract_subtitles, process_video

MEDIA_DIR_SONARR = "/Volumes/MEDIA/sonarr"
MEDIA_DIR_RADARR = "/Volumes/MEDIA/radarr"
ARCHIVE_DIR = "/Volumes/MEDIA/archive"
VIDEO_EXTS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']

def pipeline(media_dir):
    media_list = list_media_files(media_dir, VIDEO_EXTS)
    for file in media_list:
        file_obj = Path(file)
        folder_obj = Path(file.parent)
        print('\n\n=========================')
        print(f"Handling file: {file}")
        print(f"\n* Extract subtitle from media file to srt:")
        extract_subtitles(file_obj, folder_obj)
        print(f"\n* Analyze if file need transcoding")
        info = get_video_info(file_obj)
        if info["needs_transcoding"] is False:
            print(f"==> SKIP: Video codec and audio codec match expected format (hevc, aac)")
            continue
        else:
            print(f"==> START TRANSCODING")
            exit_code = process_video(file_obj)
            print(f"==> TRANSCODING COMPLETED WITH EXIT CODE: {exit_code}")
    manage_backups(MEDIA_DIR_SONARR, 'archive', ARCHIVE_DIR)

if __name__ == '__main__':
    pipeline(MEDIA_DIR_SONARR)