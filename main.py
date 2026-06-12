import json
import os
import sys
import argparse
from pathlib import Path

from app.config import AppConfig
from app.jobrepo import SQLiteJobRepository
from app.logger import logger, setup_logger
from app.media_scanner import MediaScanner
from app.pipeline import Pipeline
from app.transcoder import FfmpegTranscoder


def _build_pipeline(config: AppConfig) -> Pipeline:
    """Build and return a fully-configured Pipeline instance."""
    scanner = MediaScanner()
    transcoder = FfmpegTranscoder(
        subtitle_mode=config.subtitle_mode,
        verify_output_size=config.verify_output_size,
    )
    jobrepo = SQLiteJobRepository(
        config.job_repo_file,
        retry_timeout=config.transcode_retry_timeout,
    )

    return Pipeline(
        scanner=scanner,
        jobrepo=jobrepo,
        transcoder=transcoder,
        media_dirs=config.media_dirs,
        backup_strategy=config.backup_strategy,
        backup_dir=str(config.backup_dir),
        extract_subtitle=config.extract_subtitle,
        subtitle_mode=config.subtitle_mode,
        verify_output_size=config.verify_output_size,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Simple VidCompress — automated HEVC transcoding pipeline"
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Transcode a single media file instead of scanning directories",
    )
    args = parser.parse_args()

    basedir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(basedir, "config.json")

    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        logger.info(
            "Please create config.json based on config.example.json "
            "and ensure ffmpeg/ffprobe are in PATH"
        )
        sys.exit(1)

    try:
        with open(config_path) as f:
            config_data = json.load(f)
        config = AppConfig(**config_data)
    except Exception as e:
        logger.error(f"Invalid configuration: {e}")
        sys.exit(1)

    # Re-setup logger with configured level
    setup_logger(level=config.log_level)

    logger.info("Initializing application...")

    pipeline = _build_pipeline(config)

    # Check FFmpeg availability early
    availability = pipeline.transcoder.check_availability()
    ffmpeg_ok = availability.get("ffmpeg", {}).get("available")
    ffprobe_ok = availability.get("ffprobe", {}).get("available")
    if not ffmpeg_ok or not ffprobe_ok:
        logger.error(
            "Required tools not found: ffmpeg and/or ffprobe are missing from PATH"
        )
        sys.exit(1)

    try:
        # Clean orphaned temp files from previous runs
        pipeline._clean_orphan_temp_files()

        if args.path:
            file_path = Path(args.path).resolve()
            if not file_path.exists():
                logger.error(f"Specified file does not exist: {file_path}")
                sys.exit(1)
            logger.info(f"Processing single file: {file_path}")
            pipeline.jobrepo.enqueue(file_path)
        else:
            pipeline.scan()

        pipeline.run()
        pipeline.clean()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Exiting...")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
