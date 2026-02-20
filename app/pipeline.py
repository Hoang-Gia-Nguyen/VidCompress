from pathlib import Path

from app.media_scanner import MediaScanner, BackupStrategy
from app.transcoder import Transcoder

class Pipeline():
    """
    A class representing a media processing pipeline.

    It handles a list of media directories, extracts subtitles, analyzes and transcodes video files if necessary,
    and manages backups according to a specified strategy.

    Attributes:
        transcoder (Transcoder): The transcoder object used for video processing.
        media_dirs (list): A list of media directories to process.
        extract_subtitle (bool): A flag indicating whether to extract subtitles from media files.
        backup_strategy (BackupStrategy): The strategy used for managing backups.
        backup_dir (str): The directory where backups are stored. Defaults to an empty string.
        dry_run (bool): A flag indicating whether to perform a dry run. Defaults to False.
    """
    def __init__(self, transcoder: Transcoder, media_dirs: list, extract_subtitle: bool, backup_strategy: BackupStrategy, backup_dir: str = "", dry_run: bool = False):
        """
        Initializes a Pipeline object.

        Args:
            transcoder (Transcoder): The transcoder object used for video processing.
            media_dirs (list): A list of media directories to process.
            extract_subtitle (bool): A flag indicating whether to extract subtitles from media files.
            backup_strategy (BackupStrategy): The strategy used for managing backups.
            backup_dir (str, optional): The directory where backups are stored. Defaults to an empty string.
            dry_run (bool, optional): A flag indicating whether to perform a dry run. Defaults to False.

        Raises:
            None
        """
        self.transcoder = transcoder
        self.media_dirs = media_dirs
        self.backup_strategy = backup_strategy
        self.backup_dir = backup_dir
        self.extract_subtitle = extract_subtitle
    
    def run(self):
        """
        Runs the media processing pipeline.

        This method iterates over the list of media directories, scans for media files,
        extracts subtitles if specified, analyzes and transcodes video files if necessary,
        and manages backups according to the specified strategy.

        Returns:
            None
        """
        print("Start pipeline!!!")
        for media_dir in self.media_dirs:
            print(f"[Pipeline][DirHandling] Start working with {media_dir}")
            try:
                scanner = MediaScanner(media_dir)
            except FileNotFoundError as e:
                print(f"❌ [MediaScanner][ERROR]: Path does not exist {media_dir}")
                continue
            except NotADirectoryError as e:
                print(f"❌ [MediaScanner][ERROR]: Path is not dir '{media_dir}'")
                continue
            except Exception as e:
                print(f"⚠️  [MediaScanner][ERROR]: Unidentified: {e}")
                continue

            media_list = scanner.list_media_files()
            for file in media_list:
                folder = Path(file.parent)
                print('\n\n=========================')
                print(f"[Pipeline][FileHandling] Handling file: {file.name}")
                if self.extract_subtitle:
                    print(f"\n* Extract subtitle from media file to srt:")
                    self.transcoder.extract_subtitles(file, folder)
                print(f"\n* Analyze if file need transcoding")
                info = self.transcoder.get_video_info(file)
                if info["needs_transcoding"] is False:
                    print(f"==> SKIP: Video codec and audio codec match expected format (hevc, aac)")
                    continue
                else:
                    print(f"==> START TRANSCODING")
                    exit_code = self.transcoder.process_video(file)
                    print(f"==> TRANSCODING COMPLETED WITH EXIT CODE: {exit_code}")
            scanner.manage_backups(self.backup_strategy, self.backup_dir)