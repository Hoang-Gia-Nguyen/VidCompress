import json
import os
from app.media_scanner import MediaScanner
from app.transcoder import FfmpegTranscoder, BackupStrategy
from app.jobrepo import SQLiteJobRepository
from app.pipeline import Pipeline

basedir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(basedir, "config.json")

with open(config_path) as f:
    config = json.load(f)

MEDIA_DIRS = config["MEDIA_DIRS"]
BACKUP_DIR = config["BACKUP_DIR"]
EXTRACT_SUBTITLE = config["EXTRACT_SUBTITLE"]
JOB_REPO_FILE = config["JOB_REPO_FILE"]

try:
    BACKUP_STRATEGY = BackupStrategy[config["BACKUP_STRATEGY"]]
except KeyError:
    raise ValueError(
        f"Invalid backup strategy: '{config['BACKUP_STRATEGY']}'. Supported strategies: {[e.name for e in BackupStrategy]}. Please update 'config.json' with a valid backup strategy and restart the application."
    )

scanner = MediaScanner()
transcoder = FfmpegTranscoder()
jobrepo = SQLiteJobRepository(JOB_REPO_FILE)

pipeline = Pipeline(
    scanner=scanner,
    jobrepo=jobrepo,
    transcoder=transcoder,
    media_dirs=MEDIA_DIRS,
    backup_strategy=BACKUP_STRATEGY,
    backup_dir=BACKUP_DIR,
    extract_subtitle=EXTRACT_SUBTITLE,
)

pipeline.scan()
pipeline.run()
pipeline.clean()
