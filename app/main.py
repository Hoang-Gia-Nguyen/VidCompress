import json
from media_scanner import BackupStrategy
from transcoder import FfmpegTranscoder
from pipeline import Pipeline

with open('config.json') as f:
    config = json.load(f)

MEDIA_DIRS = config['MEDIA_DIRS']
BACKUP_DIR = config['BACKUP_DIR']
EXTRACT_SUBTITLE = config['EXTRACT_SUBTITLE']

try:
    BACKUP_STRATEGY = BackupStrategy[config['BACKUP_STRATEGY']]
except KeyError:
    raise ValueError(f"Invalid backup strategy: '{config['BACKUP_STRATEGY']}'. Supported strategies: {[e.name for e in BackupStrategy]}. Please update 'config.json' with a valid backup strategy and restart the application.")

transcoder = FfmpegTranscoder()

pipeline = Pipeline(
    transcoder=transcoder,
    media_dirs=MEDIA_DIRS,
    backup_strategy=BACKUP_STRATEGY,
    backup_dir=BACKUP_DIR,
    extract_subtitle=EXTRACT_SUBTITLE
    )

pipeline.run()