from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BackupStrategy(str, Enum):
    ARCHIVE = "ARCHIVE"
    DELETE = "DELETE"
    DO_NOTHING = "DO_NOTHING"


class SubtitleMode(str, Enum):
    COPY = "COPY"
    EXTERNAL = "EXTERNAL"
    BOTH = "BOTH"


class AppConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    media_dirs: list[Path] = Field(..., alias="MEDIA_DIRS")
    backup_dir: Path = Field(..., alias="BACKUP_DIR")
    extract_subtitle: bool = Field(False, alias="EXTRACT_SUBTITLE")
    backup_strategy: BackupStrategy = Field(
        BackupStrategy.ARCHIVE, alias="BACKUP_STRATEGY"
    )
    job_repo_file: str = Field("jobs.db", alias="JOB_REPO_FILE")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    subtitle_mode: SubtitleMode = Field(SubtitleMode.COPY, alias="SUBTITLE_MODE")
    verify_output_size: bool = Field(True, alias="VERIFY_OUTPUT_SIZE")
    transcode_retry_timeout: int = Field(600, alias="TRANCODE_RETRY_TIMEOUT")

    @field_validator("media_dirs", mode="before")
    @classmethod
    def validate_media_dirs(cls, v):
        if isinstance(v, str):
            return [v]
        return v
