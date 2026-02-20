# transcoder.py
import subprocess
import json
import re
import shutil
import time
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List

class ProcessStatus(Enum):
    SUCCESS = 1
    SKIPPED = 2
    FILE_NOT_FOUND = 3
    ERROR = 4

class Transcoder:
    """
    Base class for transcoding operations.
    """
    name = "base_empty"
    
    def __init__(self):
        """Initialize the Transcoder base class."""
        pass

    def list_tools(self) -> Optional[List[str]]:
        raise NotImplementedError("Subclasses of Transcoder must implement list_tools().")
    
    def check_availability(self) -> Optional[Dict]:
        """
        Checks if tools are installed and accessible.
        Returns a dictionary with the status and paths of tools.
        """
        raise NotImplementedError("Subclasses of Transcoder must implement check_availability().")
    
    def get_video_info(self, input_path: Path) -> Optional[Dict]:
        """
        Uses ffprobe to extract video and audio codec information.
        
        Args:
            input_path (Path): Path to the media file.
            
        Returns:
            dict: A dictionary containing 'video_codec', 'audio_codec', and 'duration',
                or None if the file cannot be parsed.
        """
        raise NotImplementedError("Subclasses of Transcoder must implement get_video_info().")

    def extract_subtitles(self, input_path: Path, output_dir: Path):
        """
        Detects and extracts all subtitle tracks from a video file into .srt files.
        
        Args:
            input_path (Path): Path object pointing to the source video file.
            output_dir (Path): Path object pointing to where .srt files should be saved.
        """
        raise NotImplementedError("Subclasses of Transcoder must implement extract_subtitles().")

    def get_video_info(self, input_path: Path) -> Optional[Dict]:
        """
        Uses tool to extract video and audio codec information.
        
        Args:
            input_path (Path): Path to the media file.
            
        Returns:
            dict: A dictionary containing 'video_codec', 'audio_codec', and 'duration',
                  or None if the file cannot be parsed.
        """
        raise NotImplementedError("Subclasses of Transcoder must implement get_video_info().")

class FfmpegTranscoder(Transcoder):
    """
    FFmpeg-based transcoder implementation.
    """
    name = "ffmpeg"
    _best_hevc_encoder = 'libx265'
    
    def __init__(self):
        """Initialize the FfmpegTranscoder class."""
        super().__init__()
        tool_list = self.list_tools()
        print(f"Tools to be used: {tool_list}")
        tool_availability = self.check_availability()
        for tool in tool_list:
            print(f"Tool [{tool}] available={tool_availability[tool]["available"]} && path={tool_availability[tool]["path"]}")
            if not tool_availability[tool]["available"]:
                raise RuntimeError(f"[FfmpegTranscoder] Cannot initialize, transcoder listed tool {tool} is not available in system")
        self._best_hevc_encoder = self._get_best_hevc_encoder()
        print(f"[FfmpegTranscoder] Best HEVC encoder: {self._best_hevc_encoder}")

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
                    subprocess.run([tool, "-version"], capture_output=True, text=True, check=True)
                    results[tool] = {"available": True, "path": path}
                except (subprocess.CalledProcessError, FileNotFoundError):
                    results[tool] = {"available": False, "path": None}
            else:
                results[tool] = {"available": False, "path": None}

        return results
    
    def get_video_info(self, input_path: Path) -> Optional[Dict]:
        """
        Uses ffprobe to extract video and audio codec information.
        
        Args:
            input_path (Path): Path to the media file.
            
        Returns:
            dict: A dictionary containing 'video_codec', 'audio_codec', and 'duration',
                or None if the file cannot be parsed.
        """
        # ffprobe command to extract stream information in JSON format
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-show_format',
            str(input_path)
        ]

        try:
            # Execute the command and capture the output
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            info = {
                "video_codec": None,
                "audio_codec": [],
                "duration": float(data.get('format', {}).get('duration', 0)),
                "needs_transcoding": True
            }

            for stream in data.get('streams', []):
                codec_type = stream.get('codec_type')
                codec_name = stream.get('codec_name')

                if codec_type == 'video' and not info["video_codec"]:
                    info["video_codec"] = codec_name
                elif codec_type == 'audio':
                    info["audio_codec"].append(codec_name)

            # Logic check: If already HEVC (h265) and AAC, we might want to skip it
            if info["video_codec"] == 'hevc' and 'aac' in info["audio_codec"]:
                info["needs_transcoding"] = False

            return info

        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
            print(f"[-] Could not probe file {input_path.name}: {e}")
            return None

    def _is_encoder_functional(self, encoder_name):
        """Checks if a specific FFmpeg encoder can actually run."""
        cmd = [
            'ffmpeg', '-y', 
            '-f', 'lavfi', '-i', 'color=c=black:s=640x480', # Tiny fake input
            '-t', '0.5',                                   # Only 0.5 seconds
            '-c:v', encoder_name, 
            '-f', 'null', '-'                              # Output to nowhere
        ]
        
        try:
            # Run command, capturing output to keep logs clean
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
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
            result = subprocess.run(
                ['ffmpeg', '-encoders'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            output = result.stdout

            # Define priority list for HEVC hardware encoders
            # hevc_videotoolbox: macOS (Apple Silicon / Intel Mac)
            # hevc_nvenc: NVIDIA GPUs
            # hevc_qsv: Intel Quick Sync
            # hevc_amf: AMD GPUs
            hardware_encoders = [
                'hevc_videotoolbox', 
                'hevc_nvenc', 
                'hevc_qsv', 
                'hevc_amf'
            ]

            for encoder in hardware_encoders:
                # Look for the encoder name in the output (ensuring it's a video encoder 'V')
                if re.search(rf'V.....\s+{encoder}', output):
                    if self._is_encoder_functional(encoder):
                        return encoder
                    else:
                        continue

            # Fallback to software (CPU) if no hardware encoder found
            return 'libx265'

        except subprocess.CalledProcessError:
            return "Error: FFmpeg not found or failed to run."
        
    def process_video(self, input_path: Path, output_path: Path = None):
        """
        Intelligently transcodes or copies streams based on existing codecs.
        """
        # 1. Get metadata first (using the function we wrote earlier)
        info = self.get_video_info(input_path)
        if not info:
            return ProcessStatus.FILE_NOT_FOUND
        if info["needs_transcoding"] is False:
            return ProcessStatus.SKIPPED

        # 2. Determine paths
        temp_output = input_path.with_suffix(".transcoding.mp4")
        
        # 3. Build Intelligent Command
        # Start with base command
        command = ['ffmpeg', '-y', '-i', str(input_path)]

        # VIDEO LOGIC: Skip transcoding if already HEVC (h265)
        if info["video_codec"] == 'hevc':
            print(f"[~] Video is already H.265. Copying stream...")
            command += ['-c:v', 'copy']
        else:
            print(f"[*] Transcoding video to H.265 using {self._best_hevc_encoder}...")
            command += ['-c:v', self._best_hevc_encoder, '-crf', '23', '-preset', 'medium']

        # AUDIO LOGIC: Skip transcoding if already AAC
        if 'aac' in info["audio_codec"]:
            print(f"[~] Audio is already AAC. Copying stream...")
            command += ['-c:a', 'copy']
        else:
            print(f"[*] Transcoding audio to AAC...")
            command += ['-c:a', 'aac', '-b:a', '128k']

        # Add compatibility tag and output path
        command += ['-movflags', '+faststart']
        command += ['-tag:v', 'hvc1', str(temp_output)]

        # 4. Execute
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            
            # 5. Swap files (Replace original)
            if output_path is None:
                backup_path = input_path.with_suffix(input_path.suffix + ".originalmedia")
                input_path.rename(backup_path)
                temp_output.rename(input_path)
                print(f"[Done] Processed: {input_path.name}")
            return ProcessStatus.SUCCESS
            
        except subprocess.CalledProcessError as e:
            print(f"[-] FFmpeg Failed: {e.stderr}")
            if temp_output.exists():
                temp_output.unlink()
            return ProcessStatus.ERROR
        
    def extract_subtitles(self, input_path: Path, output_dir: Path):
        """
        Detects and extracts all subtitle tracks from a video file into .srt files.
        
        Args:
            input_path (Path): Path object pointing to the source video file.
            output_dir (Path): Path object pointing to where .srt files should be saved.
        """
        # 1. Use ffprobe to find subtitle streams and their languages
        probe_command = [
            'ffprobe', 
            '-v', 'error',
            '-show_entries', 'stream=index:tags=language', 
            '-select_streams', 's', 
            '-of', 'json', 
            '-i', str(input_path)
        ]
        
        try:
            start_time = time.perf_counter()
            result = subprocess.run(probe_command, capture_output=True, text=True, check=True)
            end_time = time.perf_counter()
            streams = json.loads(result.stdout).get('streams', [])
            
            if not streams:
                print(f"No subtitle streams found in: {input_path.name}")
                return
            else:
                print(f"Found {len(streams)} subtitle streams in file in {end_time-start_time}s")

            # 2. Extract each subtitle stream
            for stream in streams:
                index = stream['index']
                # Get language tag, default to 'und' (undefined) if not present
                lang = stream.get('tags', {}).get('language', f'track_{index}')
                
                # Construct output filename: movie_name.en.srt
                srt_filename = f"{input_path.stem}.{lang}.srt"
                srt_path = output_dir / srt_filename

                if srt_path.exists():
                    print(f"Skipping {srt_filename}: File already exists.")
                    continue  # Move to the next iteration

                print(f"Extracting subtitle stream #{index} ({lang}) to {srt_filename}...")

                # FFmpeg command to extract a specific subtitle stream to SRT
                extract_command = [
                    'ffmpeg',
                    '-y',                   # Overwrite output files
                    '-i', str(input_path),  # Input file
                    '-map', f'0:{index}',   # Map the specific subtitle stream
                    str(srt_path)           # Output path
                ]
                
                subprocess.run(extract_command, capture_output=True, check=True)
                
        except subprocess.CalledProcessError as e:
            print(f"Error processing {input_path.name}: {e.stderr}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")