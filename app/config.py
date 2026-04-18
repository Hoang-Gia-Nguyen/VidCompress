from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BackupStrategy(str, Enum):
    ARCHIVE = "ARCHIVE"
    DELETE = "DELETE"
    DO_NOTHING = "DO_NOTHING"


class AppConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    media_dirs: List[Path] = Field(..., alias="MEDIA_DIRS")
    backup_dir: Path = Field(..., alias="BACKUP_DIR")
    extract_subtitle: bool = Field(False, alias="EXTRACT_SUBTITLE")
    backup_strategy: BackupStrategy = Field(
        BackupStrategy.ARCHIVE, alias="BACKUP_STRATEGY"
    )
    job_repo_file: str = Field("jobs.db", alias="JOB_REPO_FILE")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @field_validator("media_dirs", mode="before")
    @classmethod
    def validate_media_dirs(cls, v):
        if isinstance(v, str):
            return [v]
        return v
