# transcoder.py
import json
import re
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


from app.config import BackupStrategy
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


@dataclass
class VideoInfo:
    video_codec: Optional[str] = None
    audio_codec: Optional[List[str]] = None
    duration: Optional[float] = None
    needs_transcoding: bool = False


class Transcoder(ABC):
    """
    Base class for transcoding operations.
    """

    def __init__(self):
        """Initialize the Transcoder base class."""
        self.name = "base_empty"
        self.temp_file_list = []
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
    def process_video(self,
                      input_path: Path,
                      output_path: Path = None) -> ProcessResult:
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

    def __init__(self):
        """Initialize the FfmpegTranscoder class."""
        self.name = "ffmpeg"
        self._best_hevc_encoder = "libx265"
        super().__init__()
        tool_list = self.list_tools()
        logger.debug(f"Tools to be used: {tool_list}")
        tool_availability = self.check_availability()
        for tool in tool_list:
            logger.debug(
                f"Tool [{tool}] available={tool_availability[tool]['available']} && path={tool_availability[tool]['path']}"
            )
            if not tool_availability[tool]["available"]:
                raise RuntimeError(
                    f"[FfmpegTranscoder] Cannot initialize, transcoder listed tool {tool} is not available in system"
                )
        self._best_hevc_encoder = self._get_best_hevc_encoder()
        logger.info(
            f"[FfmpegTranscoder] Best HEVC encoder: {self._best_hevc_encoder}")

    def list_tools(self) -> list:
        return ["ffmpeg", "ffprobe"]

    def check_availability(self) -> dict:
        """
        Checks if ffmpeg and ffprobe are installed and accessible in the system PATH.
        Returns a dictionary with the status and paths.
        """
        tools = ["ffmpeg", "ffprobe"]
        results = {}

        for tool in tools:
            path = shutil.which(tool)
            if path:
                # Optionally verify by running --version to ensure it's not a dummy file
                try:
                    subprocess.run([tool, "-version"],
                                   capture_output=True,
                                   text=True,
                                   check=True)
                    results[tool] = {"available": True, "path": path}
                except (subprocess.CalledProcessError, FileNotFoundError):
                    results[tool] = {"available": False, "path": None}
            else:
                results[tool] = {"available": False, "path": None}

        return results

    def get_video_info(self, input_path: Path) -> Optional[VideoInfo]:
        """
        Uses ffprobe to extract video and audio codec information.

        Args:
            input_path (Path): Path to the media file.

        Returns:
            VideoInfo: A dataclass containing 'video_codec', 'audio_codec', 'duration',
                and 'needs_transcoding', or None if the file cannot be parsed.
        """
        # ffprobe command to extract stream information in JSON format
        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(input_path),
        ]

        try:
            # Execute the command and capture the output
            result = subprocess.run(command,
                                    capture_output=True,
                                    text=True,
                                    check=True)
            data = json.loads(result.stdout)

            video_codec = None
            audio_codec = []
            duration = float(data.get("format", {}).get("duration", 0))

            for stream in data.get("streams", []):
                codec_type = stream.get("codec_type")
                codec_name = stream.get("codec_name")

                if codec_type == "video" and not video_codec:
                    video_codec = codec_name
                elif codec_type == "audio":
                    audio_codec.append(codec_name)

            needs_transcoding = True
            # Logic check: If already HEVC (h265) and AAC, we might want to skip it
            if video_codec == "hevc" and "aac" in audio_codec:
                needs_transcoding = False

            return VideoInfo(video_codec, audio_codec, duration,
                             needs_transcoding)
        except Exception:
            return None

    def _is_encoder_functional(self, encoder_name):
        """Checks if a specific FFmpeg encoder can actually run."""
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=640x480",  # Tiny fake input
            "-t",
            "0.5",  # Only 0.5 seconds
            "-c:v",
            encoder_name,
            "-f",
            "null",
            "-",  # Output to nowhere
        ]

        try:
            # Run command, capturing output to keep logs clean
            result = subprocess.run(cmd,
                                    capture_output=True,
                                    text=True,
                                    timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _get_best_hevc_encoder(self) -> str:
        """
        Detects the best available HEVC encoder based on hardware availability.
        Priority: VideoToolbox (Mac) > NVENC (NVIDIA) > QSV (Intel) > libx265 (CPU)
        """
        try:
            # Get list of all encoders supported by the installed FFmpeg
            result = subprocess.run(["ffmpeg", "-encoders"],
                                    capture_output=True,
                                    text=True,
                                    check=True)
            output = result.stdout

            # Define priority list for HEVC hardware encoders
            # hevc_videotoolbox: macOS (Apple Silicon / Intel Mac)
            # hevc_nvenc: NVIDIA GPUs
            # hevc_qsv: Intel Quick Sync
            # hevc_amf: AMD GPUs
            hardware_encoders = [
                "hevc_videotoolbox",
                "hevc_nvenc",
                "hevc_qsv",
                "hevc_amf",
            ]

            for encoder in hardware_encoders:
                # Look for the encoder name in the output (ensuring it's a video encoder 'V')
                if re.search(rf"V.....\s+{encoder}", output):
                    if self._is_encoder_functional(encoder):
                        return encoder
                    else:
                        continue

            # Fallback to software (CPU) if no hardware encoder found
            return "libx265"

        except subprocess.CalledProcessError:
            return "Error: FFmpeg not found or failed to run."

    def process_video(self, input_path: Path, output_path: Path = None) -> ProcessResult:
        """
        Intelligently transcodes or copies streams based on existing codecs.
        """
        # 1. Get metadata first (using the function we wrote earlier)
        info = self.get_video_info(input_path)
        if not info:
            return ProcessResult(ProcessStatus.FILE_NOT_FOUND, "Could not extract video info")
        if info.needs_transcoding is False:
            return ProcessResult(ProcessStatus.SKIPPED)

        # 2. Determine paths
        temp_output = input_path.with_suffix(".transcoding.mp4")

        # 3. Build Intelligent Command
        # Start with base command
        command = ["ffmpeg", "-y", "-i", str(input_path)]

        # VIDEO LOGIC: Skip transcoding if already HEVC (h265)
        if info.video_codec == "hevc":
            logger.info(f"[~] {input_path.name}: Video is already H.265. Copying stream...")
            command += ["-c:v", "copy"]
        else:
            logger.info(
                f"[*] {input_path.name}: Transcoding video to H.265 using {self._best_hevc_encoder}..."
            )
            command += [
                "-c:v",
                self._best_hevc_encoder,
                "-crf",
                "23",
                "-preset",
                "medium",
            ]

        # AUDIO LOGIC: Skip transcoding if already AAC
        if "aac" in info.audio_codec:
            logger.info(f"[~] {input_path.name}: Audio is already AAC. Copying stream...")
            command += ["-c:a", "copy"]
        else:
            logger.info(f"[*] {input_path.name}: Transcoding audio to AAC...")
            command += ["-c:a", "aac", "-b:a", "128k"]

        # Add compatibility tag and output path
        command += ["-movflags", "+faststart"]
        command += ["-tag:v", "hvc1", str(temp_output)]

        # 4. Execute
        try:
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"[-] FFmpeg Failed for {input_path.name}: {result.stderr}")
                if temp_output.exists():
                    temp_output.unlink()
                return ProcessResult(ProcessStatus.ERROR, result.stderr)

            # 5. Swap files (Replace original)
            if output_path is None:
                backup_path = input_path.with_suffix(input_path.suffix +
                                                     ".originalmedia")
                input_path.rename(backup_path)
                temp_output.rename(input_path)
                logger.info(f"[Done] Processed: {input_path.name}")
                self.temp_file_list.append(Path(backup_path))
            
            return ProcessResult(ProcessStatus.SUCCESS)

        except Exception as e:
            logger.error(f"[-] Unexpected error for {input_path.name}: {str(e)}")
            if temp_output.exists():
                temp_output.unlink()
            return ProcessResult(ProcessStatus.ERROR, str(e))

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
            result = subprocess.run(probe_command,
                                    capture_output=True,
                                    text=True,
                                    check=True)
            end_time = time.perf_counter()
            streams = json.loads(result.stdout).get("streams", [])

            if not streams:
                logger.debug(f"No subtitle streams found in: {input_path.name}")
                return
            else:
                logger.info(
                    f"Found {len(streams)} subtitle streams in {input_path.name} in {end_time-start_time:.2f}s"
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

                subprocess.run(extract_command,
                               capture_output=True,
                               check=True)

        except subprocess.CalledProcessError as e:
            logger.error(f"Error extracting subtitles from {input_path.name}: {e.stderr}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during subtitle extraction for {input_path.name}: {e}")
