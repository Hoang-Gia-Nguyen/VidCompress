from pathlib import Path

from app.config import BackupStrategy
from app.jobrepo import Job, JobRepository
from app.logger import logger
from app.media_scanner import MediaScanner
from app.transcoder import ProcessResult, ProcessStatus, Transcoder


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
        logger.info("Starting pipeline scan...")
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
            logger.info(f"Processing task {job.id}: {job.path.name}")
            if self.extract_subtitle:
                self.transcoder.extract_subtitles(job.path, Path(job.path.parent))
            
            info = self.transcoder.get_video_info(job.path)
            if info is None:
                logger.warning(f"No video information could be extracted for {job.path}")
                self.jobrepo.mark_error(job.id, "No video info extracted")
                continue
                
            if info.needs_transcoding is False:
                logger.info(f"Skipping {job.path.name}: Already in target format")
                self.jobrepo.mark_skipped(job.id)
                continue
            
            logger.info(f"Transcoding {job.path.name}...")
            result = self.transcoder.process_video(job.path)
            logger.info(f"Transcoding complete for {job.path.name} (Status: {result.status.name})")
            self._update_process_status_to_repo(result, job)

            # Add all temp file to be a job to be cleaned later
            temp_files = self.transcoder.get_temp_files()
            for temp_file in temp_files:
                logger.debug(f"Adding to trash: {temp_file}")
                self.jobrepo.enqueue_trash(temp_file)

    def clean(self):
        """
        Cleans up temporary files generated during media processing.

        This method iterates over the list of trash jobs, cleans up temporary files, and updates the job repository.

        Returns:
            None
        """
        logger.info("Starting cleanup...")
        for job in self.jobrepo.iter_trash():
            logger.info(f"Cleaning up task {job.id}: {job.path.name}")
            self.transcoder.clean_temp_file(
                file=job.path, action=self.backup_strategy, archive_dest=self.backup_dir
            )
            self._update_cleanup_status_to_repo(job)

    def _update_process_status_to_repo(self, result: ProcessResult, job: Job):
        """
        Updates the process status of a job in the repository.

        Args:
            result (ProcessResult): The result of the process.
            job (Job): The job to update.

        Returns:
            None
        """
        if result.status == ProcessStatus.SUCCESS:
            self.jobrepo.mark_done(job.id)
        elif result.status == ProcessStatus.SKIPPED:
            self.jobrepo.mark_skipped(job.id)
        elif result.status == ProcessStatus.FILE_NOT_FOUND:
            self.jobrepo.mark_error(job.id, result.error_message or "File not found")
        elif result.status == ProcessStatus.ERROR:
            self.jobrepo.mark_error(job.id, result.error_message or "Unknown error")

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
