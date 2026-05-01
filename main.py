import json
import os
import sys

from app.config import AppConfig
from app.jobrepo import SQLiteJobRepository
from app.logger import logger, setup_logger
from app.media_scanner import MediaScanner
from app.pipeline import Pipeline
from app.transcoder import FfmpegTranscoder

def main():
    basedir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(basedir, "config.json")

    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        logger.info("Please create config.json based on config.example.json")
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

    scanner = MediaScanner()
    transcoder = FfmpegTranscoder()
    jobrepo = SQLiteJobRepository(config.job_repo_file)

    pipeline = Pipeline(
        scanner=scanner,
        jobrepo=jobrepo,
        transcoder=transcoder,
        media_dirs=config.media_dirs,
        backup_strategy=config.backup_strategy,
        backup_dir=str(config.backup_dir),
        extract_subtitle=config.extract_subtitle,
    )

    try:
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
