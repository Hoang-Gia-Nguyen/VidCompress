import json
import re
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from app.config import BackupStrategy, SubtitleMode
from app.logger import logger


class ProcessStatus(Enum):
    SUCCESS = 1
    SKIPPED = 2
    FILE_NOT_FOUND = 3
    ERROR = 4


@dataclass
class ProcessResult:
    status: ProcessStatus
    error_message: Optional[str] = None
    original_size: Optional[int] = None
    output_size: Optional[int] = None


@dataclass
class StreamInfo:
    index: int
    codec_type: str
    codec: str
    tags: dict = field(default_factory=dict)


@dataclass
class VideoInfo:
    video_codec: Optional[str] = None
    audio_codec: Optional[List[str]] = None
    duration: Optional[float] = None
    needs_transcoding: bool = False
    streams: List[StreamInfo] = field(default_factory=list)


class Transcoder(ABC):
    """
    Base class for transcoding operations.
    """

    def __init__(self):
        """Initialize the Transcoder base class."""
        self.name = "base_empty"
        self.temp_file_list = []
        self.subtitle_mode = SubtitleMode.COPY
        self.verify_output_size = True
        pass

    @abstractmethod
    def list_tools(self) -> Optional[List[str]]:
        pass

    @abstractmethod
    def check_availability(self) -> Optional[Dict]:
        """
        Checks if tools are installed and accessible.
        Returns a dictionary with the status and paths of tools.
        """
        pass

    @abstractmethod
    def get_video_info(self, input_path: Path) -> Optional[VideoInfo]:
        """
        Uses tool to extract video and audio codec information.

        Args:
            input_path (Path): Path to the media file.

        Returns:
            dict: A dictionary containing 'video_codec', 'audio_codec', and 'duration',
                or None if the file cannot be parsed.
        """
        pass

    @abstractmethod
    def extract_subtitles(self, input_path: Path, output_dir: Path):
        """
        Detects and extracts all subtitle tracks from a video file into .srt files.

        Args:
            input_path (Path): Path object pointing to the source video file.
            output_dir (Path): Path object pointing to where .srt files should be saved.

        Returns:
            List[Path]: A list of Path objects representing the temporary files.
        """
        pass

    @abstractmethod
    def process_video(
        self, input_path: Path, output_path: Path = None
    ) -> ProcessResult:
        """
        Transcodes or copies video streams based on the existing codecs.

        Intelligently determines whether to transcode or copy the video and audio streams.
        If output_path is specified, the result will be saved to that location.
        Otherwise, the original file will be replaced after processing.

        Args:
            input_path (Path): The path to the input video file.
            output_path (Path): The optional path where the processed video will be saved.

        Returns:
            ProcessResult: The result of the processing operation.
        """
        pass

    def get_temp_files(self) -> List[Path]:
        """
        Retrieves the list of temporary files generated during processing.

        Returns:
            List[Path]: A list of Path objects representing the temporary files.
        """
        return self.temp_file_list

    def clean_temp_file(
        self,
        file: Path,
        action: BackupStrategy,
        archive_dest: Optional[str] = None,
        pattern: Optional[str] = "*.originalmedia",
    ):
        """
        Finds all files matching the provided pattern and either deletes them or moves them to an archive.

        Args:
            action (BackupStrategy): The action to perform on the found files.
            archive_dest (str): The folder to move files to if action is 'archive'.
            pattern (str): The pattern to search for. Defaults to "*.originalmedia".
        """
        if action == BackupStrategy.DO_NOTHING:
            return

        if action == BackupStrategy.ARCHIVE:
            if not archive_dest:
                return

            dest_path = Path(archive_dest)
            dest_path.mkdir(parents=True, exist_ok=True)

            try:
                # Move file to the archive folder
                # Note: If duplicate filenames exist in different subfolders,
                # we use the full name to avoid overwriting.
                target = dest_path / file.name
                shutil.move(str(file), str(target))
                logger.info(f"[Moved] {file.name} -> {archive_dest}")
            except Exception as e:
                logger.error(f"[Error] Could not move {file.name}: {e}")

        elif action == BackupStrategy.DELETE:
            try:
                file.unlink()
                logger.info(f"[Deleted] {file.name}")
            except Exception as e:
                logger.error(f"[Error] Could not delete {file.name}: {e}")


class FfmpegTranscoder(Transcoder):
    """
    FFmpeg-based transcoder implementation.
    """

    def __init__(
        self,
        subtitle_mode: SubtitleMode = SubtitleMode.COPY,
        verify_output_size: bool = True,
    ):
        """Initialize the FfmpegTranscoder class."""
        self.name = "ffmpeg"
        self.temp_file_list = []
        self._best_hevc_encoder = None
        self.subtitle_mode = subtitle_mode
        self.verify_output_size = verify_output_size
        self._detect_best_hevc_encoder()

    def list_tools(self) -> Optional[List[str]]:
        return ["ffmpeg", "ffprobe"]

    def check_availability(self) -> Optional[Dict]:
        """
        Checks if ffmpeg and ffprobe are installed and accessible.
        """
        tools = {"ffmpeg": {"available": False}, "ffprobe": {"available": False}}

        for tool in tools:
            try:
                result = subprocess.run(
                    [tool, "-version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if result.returncode == 0:
                    tools[tool]["available"] = True
            except Exception:
                tools[tool]["available"] = False

        return tools

    def get_video_info(self, input_path: Path) -> Optional[VideoInfo]:
        """
        Extracts video, audio, and subtitle stream information using ffprobe.

        Returns a VideoInfo object with:
        - The primary video codec
        - Combined audio codec list (for backward compatibility)
        - Duration
        - Whether transcoding is needed
        - Full stream inventory (streams field)
        """
        command = [
            "ffprobe",
            "-v",
            "error",
            "-analyzeduration",
            "0",
            "-show_entries",
            "stream=index,codec_type,codec_name:stream_tags=language,title",
            "-of",
            "json",
            "-i",
            str(input_path),
        ]

        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to probe {input_path.name}: {e.stderr}")
            return None
        except FileNotFoundError:
            logger.error(f"File not found: {input_path}")
            return None

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse ffprobe output for {input_path.name}")
            return None

        streams = data.get("streams", [])
        if not streams:
            logger.warning(f"No streams found in {input_path.name}")
            return None

        # Parse all streams into StreamInfo objects
        all_streams: List[StreamInfo] = []
        video_codec = None
        audio_codecs: List[str] = []
        subtitle_streams: List[StreamInfo] = []
        duration = None

        for s in streams:
            idx = s.get("index", 0)
            codec_type = s.get("codec_type", "unknown")
            codec_name = s.get("codec_name", "unknown")
            tags = {}
            if "tags" in s:
                tags = {k.lower(): v for k, v in s["tags"].items()}

            stream_info = StreamInfo(
                index=idx,
                codec_type=codec_type,
                codec=codec_name,
                tags=tags,
            )
            all_streams.append(stream_info)

            if codec_type == "video" and video_codec is None:
                video_codec = codec_name
            elif codec_type == "audio":
                audio_codecs.append(codec_name)
            elif codec_type == "subtitle":
                subtitle_streams.append(stream_info)

        # Get duration from format
        fmt = data.get("format", {})
        if "duration" in fmt:
            try:
                duration = float(fmt["duration"])
            except (ValueError, TypeError):
                pass

        # Determine if transcoding is needed
        needs_transcoding = False
        if video_codec and video_codec.lower() != "hevc":
            needs_transcoding = True
        if audio_codecs:
            for ac in audio_codecs:
                if ac.lower() != "aac":
                    needs_transcoding = True

        info = VideoInfo(
            video_codec=video_codec,
            audio_codec=audio_codecs if audio_codecs else None,
            duration=duration,
            needs_transcoding=needs_transcoding,
            streams=all_streams,
        )

        logger.info(
            f"[~] {input_path.name}: video={video_codec}, "
            f"audio={audio_codecs}, "
            f"subtitles={len(subtitle_streams)}, "
            f"needs_transcoding={needs_transcoding}"
        )

        return info

    def _detect_best_hevc_encoder(self):
        """
        Detects and selects the best available HEVC encoder.

        Priority order: VideoToolbox > NVENC > QSV > AMF > libx265
        Falls back to libx265 if no hardware encoder is available or functional.
        """
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True
            )
            if result.returncode != 0:
                self._best_hevc_encoder = "libx265"
                return
            encoder_list = result.stdout
        except Exception:
            self._best_hevc_encoder = "libx265"
            return

        # Priority list for HEVC encoders
        encoder_priority = [
            "hevc_videotoolbox",
            "hevc_nvenc",
            "hevc_qsv",
            "hevc_amf",
            "libx265",
        ]

        for enc in encoder_priority:
            # Check if encoder name appears in the list
            # Pattern: line starting with any char, then 5 dots, then encoder name
            pattern = r"\.{5}\s+" + re.escape(enc) + r"\b"
            if re.search(pattern, encoder_list, re.MULTILINE):
                # For hardware encoders, verify they are functional
                if enc == "libx265" or self._is_encoder_functional(enc):
                    self._best_hevc_encoder = enc
                    logger.info(f"[+] Selected encoder: {enc}")
                    return

        # Fallback
        self._best_hevc_encoder = "libx265"

    def _is_encoder_functional(self, encoder_name: str) -> bool:
        """Quickly test if a hardware encoder is functional by encoding a tiny segment."""
        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=2x2:d=0.1",
                    "-c:v",
                    encoder_name,
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _build_stream_maps(self, info: VideoInfo) -> List[str]:
        """
        Build FFmpeg stream mapping arguments.

        Uses -map 0 to copy all streams from the input, then applies
        per-codec-type encoder overrides.
        """
        args = ["-map", "0"]

        # Video encoder
        args += ["-c:v", self._best_hevc_encoder, "-crf", "23", "-preset", "medium"]

        # Audio: per-stream handling — copy AAC, transcode others to AAC
        audio_indices = [s for s in info.streams if s.codec_type == "audio"]
        if audio_indices:
            logger.info(
                f"[~] Processing {len(audio_indices)} audio track(s): "
                + ", ".join(
                    f"#{s.index} ({s.codec})"
                    + (
                        f" [{s.tags.get('language', 'und')}]"
                        if "language" in s.tags
                        else ""
                    )
                    for s in audio_indices
                )
            )
            stream_counter: Dict[str, int] = {}
            for s in audio_indices:
                codec_type = "a"  # short form for FFmpeg stream specifier
                stream_counter.setdefault(codec_type, 0)
                idx = stream_counter[codec_type]
                stream_counter[codec_type] += 1

                if s.codec.lower() == "aac":
                    logger.info(f"  Audio #{s.index} ({s.codec}): already AAC, copying")
                    args += [f"-c:{codec_type}:{idx}", "copy"]
                else:
                    logger.info(f"  Audio #{s.index} ({s.codec}): transcoding to AAC")
                    args += [f"-c:{codec_type}:{idx}", "aac", "-b:a", "128k"]
        else:
            # No audio stream — no audio flags needed
            logger.info("[~] No audio streams found")

        # Subtitles: copy to mov_text if SUBTITLE_MODE is COPY or BOTH
        subtitle_indices = [s for s in info.streams if s.codec_type == "subtitle"]
        if subtitle_indices and self.subtitle_mode in (
            SubtitleMode.COPY,
            SubtitleMode.BOTH,
        ):
            logger.info(
                f"[~] Preserving {len(subtitle_indices)} subtitle track(s): "
                + ", ".join(
                    f"#{s.index} ({s.codec})"
                    + (
                        f" [{s.tags.get('language', 'und')}]"
                        if "language" in s.tags
                        else ""
                    )
                    for s in subtitle_indices
                )
            )
            # Use mov_text for MP4 compatibility; copy bitmap subs as-is
            args += ["-c:s", "mov_text"]
        else:
            if subtitle_indices:
                logger.info(
                    f"[~] Subtitle tracks found but SUBTITLE_MODE={self.subtitle_mode.value}, "
                    f"not embedding in output"
                )
            # Explicitly disable subtitle copying when not preserving
            args += ["-c:s", "copy"]

        return args

    def process_video(
        self, input_path: Path, output_path: Path = None
    ) -> ProcessResult:
        """
        Transcodes or copies video streams based on the existing codecs.

        Uses explicit stream mapping (-map 0) to preserve all streams.
        Handles subtitle preservation and audio per-stream transcoding.
        Optionally verifies output is smaller than input before replacing.
        """
        if not input_path.exists():
            return ProcessResult(
                ProcessStatus.FILE_NOT_FOUND, "Input file does not exist"
            )

        info = self.get_video_info(input_path)
        if info is None:
            return ProcessResult(
                ProcessStatus.FILE_NOT_FOUND, "Could not extract video info"
            )

        # Check if transcoding is needed
        if not info.needs_transcoding:
            logger.info(f"[~] {input_path.name}: Already in target format, skipping")
            return ProcessResult(ProcessStatus.SKIPPED)

        # If output_path is not given, create a temp file alongside the input
        if output_path is None:
            temp_output = input_path.with_name(input_path.stem + ".transcoding.mp4")
        else:
            temp_output = Path(output_path)

        # Capture original size for verification
        original_size = input_path.stat().st_size

        # Build the FFmpeg command with explicit stream mapping
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
        ]

        # Add stream mapping and encoders
        command += self._build_stream_maps(info)

        # Add compatibility flags
        command += ["-movflags", "+faststart"]
        command += ["-tag:v", "hvc1", str(temp_output)]

        # Execute
        logger.info(
            f"[*] Transcoding {input_path.name} with encoder {self._best_hevc_encoder}..."
        )
        if info.audio_codec:
            logger.info(f"[*] Audio streams: {info.audio_codec}")
        subtitle_count = len([s for s in info.streams if s.codec_type == "subtitle"])
        if subtitle_count:
            logger.info(f"[*] Subtitle streams: {subtitle_count}")

        try:
            start_time = time.perf_counter()
            result = subprocess.run(command, capture_output=True, text=True)
            elapsed = time.perf_counter() - start_time

            if result.returncode != 0:
                logger.error(
                    f"[-] FFmpeg Failed for {input_path.name}: {result.stderr}"
                )
                if temp_output.exists():
                    temp_output.unlink()
                return ProcessResult(
                    ProcessStatus.ERROR, result.stderr, original_size=original_size
                )

            output_size = temp_output.stat().st_size

            logger.info(
                f"[~] Transcoding complete in {elapsed:.1f}s: "
                f"{original_size / 1024 / 1024:.1f}MB -> {output_size / 1024 / 1024:.1f}MB "
                f"({(1 - output_size / original_size) * 100:.1f}% reduction)"
            )

            # Verify output size
            if self.verify_output_size and output_size > original_size:
                logger.warning(
                    f"[-] Output is larger than original "
                    f"({output_size} vs {original_size} bytes). "
                    f"Keeping original file and discarding transcoded output."
                )
                temp_output.unlink()
                return ProcessResult(
                    ProcessStatus.SKIPPED,
                    f"Output larger than original: {output_size} > {original_size}",
                    original_size=original_size,
                    output_size=output_size,
                )

            # Swap files (Replace original)
            if output_path is None:
                backup_path = input_path.with_suffix(
                    input_path.suffix + ".originalmedia"
                )
                input_path.rename(backup_path)
                temp_output.rename(input_path)
                logger.info(f"[Done] Processed: {input_path.name}")
                self.temp_file_list.append(Path(backup_path))

            return ProcessResult(
                ProcessStatus.SUCCESS,
                original_size=original_size,
                output_size=output_size,
            )

        except Exception as e:
            logger.error(f"[-] Unexpected error for {input_path.name}: {str(e)}")
            if temp_output.exists():
                temp_output.unlink()
            return ProcessResult(
                ProcessStatus.ERROR, str(e), original_size=original_size
            )

    def extract_subtitles(self, input_path: Path, output_dir: Path):
        """
        Detects and extracts all subtitle tracks from a video file into .srt files.

        Args:
            input_path (Path): Path object pointing to the source video file.
            output_dir (Path): Path object pointing to where .srt files should be saved.
        """
        # 1. Use ffprobe to find subtitle streams and their languages
        probe_command = [
            "ffprobe",
            "-v",
            "error",
            "-analyzeduration",
            "0",
            "-show_entries",
            "stream=index:tags=language",
            "-select_streams",
            "s",
            "-of",
            "json",
            "-i",
            str(input_path),
        ]

        try:
            start_time = time.perf_counter()
            result = subprocess.run(
                probe_command, capture_output=True, text=True, check=True
            )
            end_time = time.perf_counter()
            streams = json.loads(result.stdout).get("streams", [])

            if not streams:
                logger.debug(f"No subtitle streams found in: {input_path.name}")
                return
            else:
                logger.info(
                    f"Found {len(streams)} subtitle streams in {input_path.name} in {end_time - start_time:.2f}s"
                )

            # 2. Extract each subtitle stream
            for stream in streams:
                index = stream["index"]
                # Get language tag, default to 'und' (undefined) if not present
                lang = stream.get("tags", {}).get("language", f"track_{index}")

                # Construct output filename: movie_name.en.srt
                srt_filename = f"{input_path.stem}.{lang}.srt"
                srt_path = output_dir / srt_filename

                if srt_path.exists():
                    logger.debug(f"Skipping {srt_filename}: File already exists.")
                    continue  # Move to the next iteration

                logger.info(
                    f"Extracting subtitle stream #{index} ({lang}) to {srt_filename}..."
                )

                # FFmpeg command to extract a specific subtitle stream to SRT
                extract_command = [
                    "ffmpeg",
                    "-y",  # Overwrite output files
                    "-i",
                    str(input_path),  # Input file
                    "-map",
                    f"0:{index}",  # Map the specific subtitle stream
                    str(srt_path),  # Output path
                ]

                subprocess.run(extract_command, capture_output=True, check=True)

        except subprocess.CalledProcessError as e:
            logger.error(
                f"Error extracting subtitles from {input_path.name}: {e.stderr}"
            )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during subtitle extraction for {input_path.name}: {e}"
            )
