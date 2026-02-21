from app.media_scanner import MediaScanner
from app.transcoder import Transcoder, ProcessStatus, BackupStrategy
from app.jobrepo import JobRepository, Job
from pathlib import Path


class Pipeline:
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

    def __init__(
        self,
        jobrepo: JobRepository,
        scanner: MediaScanner,
        transcoder: Transcoder,
        media_dirs: list,
        extract_subtitle: bool,
        backup_strategy: BackupStrategy,
        backup_dir: str = "",
        dry_run: bool = False,
    ):
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
        self.jobrepo = jobrepo
        self.scanner = scanner
        self.transcoder = transcoder
        self.media_dirs = media_dirs
        self.backup_strategy = backup_strategy
        self.backup_dir = backup_dir
        self.extract_subtitle = extract_subtitle

    def scan(self):
        """
        Runs the media processing pipeline.

        This method iterates over the list of media directories, scans for media files,
        extracts subtitles if specified, analyzes and transcodes video files if necessary,
        and manages backups according to the specified strategy.

        Returns:
            None
        """
        print("\n[PIPELINE] Start pipeline!!!")
        for dir in self.media_dirs:
            for file in self.scanner.iter_media_files(dir):
                self.jobrepo.enqueue(file)

    def run(self):
        """
        Runs the media processing pipeline by processing pending jobs.

        This method iterates over the list of pending jobs, extracts subtitles if specified,
        analyzes and transcodes video files if necessary, and manages backups according to the specified strategy.

        Returns:
            None
        """
        for job in self.jobrepo.iter_pending():
            print(f"\n---- PROCESS TASK {job.id}----")
            if self.extract_subtitle:
                self.transcoder.extract_subtitles(job.path, Path(job.path.parent))
            info = self.transcoder.get_video_info(job.path)
            if info["needs_transcoding"] is False:
                print(
                    f"[PIPELINE][SKIP] {job.path}: Video already in expected format (hevc, aac)"
                )
                self.jobrepo.mark_skipped(job.id)
                continue
            else:
                print(f"[PIPELINE][TRANSCODING] {job.path}")
                exit_code = self.transcoder.process_video(job.path)
                print(
                    f"[PIPELINE][TRANSCODING COMPLETE] {job.path} (Exit code: {exit_code})"
                )
                self._update_process_status_to_repo(exit_code, job)

            # Add all temp file to be a job to be cleaned later
            for temp_file in self.transcoder.get_temp_files():
                self.jobrepo.enqueue_trash(temp_file)

    def clean(self):
        """
        Cleans up temporary files generated during media processing.

        This method iterates over the list of trash jobs, cleans up temporary files, and updates the job repository.

        Returns:
            None
        """
        for job in self.jobrepo.iter_trash():
            print(f"\n---- CLEAN UP TASK {job.id}----")
            self.transcoder.clean_temp_file(
                job.path, self.backup_strategy, self.backup_dir
            )
            self._update_cleanup_status_to_repo(job)

    def _update_process_status_to_repo(self, process_status: ProcessStatus, job: Job):
        """
        Updates the process status of a job in the repository.

        Args:
            process_status (ProcessStatus): The status of the process.
            job (Job): The job to update.

        Returns:
            None
        """
        update_actions = {
            ProcessStatus.SUCCESS: self.jobrepo.mark_done,
            ProcessStatus.SKIPPED: self.jobrepo.mark_skipped,
            ProcessStatus.FILE_NOT_FOUND: self.jobrepo.mark_error,
            ProcessStatus.ERROR: self.jobrepo.mark_error,
        }
        action = update_actions.get(process_status)
        if action:
            action(job.id)

    def _update_cleanup_status_to_repo(self, job: Job):
        """
        Updates the cleanup status of a job in the repository.

        Args:
            job (Job): The job to update.

        Returns:
            None
        """
        update_actions = {
            BackupStrategy.DO_NOTHING: self.jobrepo.mark_skipped,
            BackupStrategy.ARCHIVE: self.jobrepo.mark_archived,
            BackupStrategy.DELETE: self.jobrepo.mark_deleted,
        }
        action = update_actions.get(self.backup_strategy)
        if action:
            action(job.id)
