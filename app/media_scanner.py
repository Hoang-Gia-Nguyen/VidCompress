import shutil
from enum import Enum
from pathlib import Path
from typing import List

class BackupStrategy(Enum):
    ARCHIVE=1
    DELETE=2
    DO_NOTHING=3

class MediaScanner:
    """
    A class to scan directories for media files and manage backup files.
    """
    
    def __init__(self, root_dir: str):
        """
        Initialize the MediaScanner with a root directory.
        
        Args:
            root_dir (str): The path to the starting directory.
        """
        self.root_dir = root_dir
        self.root_path = Path(root_dir)
        # 1. Kiểm tra tồn tại
        if not self.root_path.exists():
            raise FileNotFoundError(f"Path does not exist: '{root_dir}'")
            
        # 2. Kiểm tra xem có phải là thư mục không (tránh trường hợp truyền vào đường dẫn file)
        if not self.root_path.is_dir():
            raise NotADirectoryError(f"Path is not dir: '{root_dir}'")
        
    def list_media_files(self, extensions: List[str]=['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']) -> List[Path]:
        """
        Recursively scans a directory for media files with specific extensions.
        
        Args:
            extensions (list): A list of file extensions to look for (e.g., ['.mp4', '.mkv']).
            
        Returns:
            list: A list of pathlib.Path objects for the found files.
        """
        media_files = []
        
        # Check if the provided path is a valid directory
        if not self.root_path.exists() or not self.root_path.is_dir():
            print(f"Error: The directory '{self.root_dir}' does not exist or is not a directory.")
            return []

        # Normalize extensions to lowercase for case-insensitive comparison
        normalized_extensions = [ext.lower() for ext in extensions]

        # rglob('*') performs a recursive search through all subfolders
        for file_path in self.root_path.rglob('*'):
            # Check if it's a file and if its suffix (extension) is in our list
            if file_path.is_file() and file_path.suffix.lower() in normalized_extensions:
                media_files.append(Path(file_path))
                
        return media_files

    def manage_backups(self, action:BackupStrategy, archive_dest: str = None):
        """
        Finds all .originalmedia files and either deletes them or moves them to an archive.
        
        Args:
            action (str): Either 'delete' or 'archive'. Defaults to 'archive'.
            archive_dest (str): The folder to move files to if action is 'archive'.
        """
        if action == BackupStrategy.DO_NOTHING:
            print("Backup strategy 'DO_NOTHING' used. Return immediately!")
            return

        # Search for all files ending in .originalmedia recursively
        backup_files = list(self.root_path.rglob("*.originalmedia"))

        if not backup_files:
            print("No .originalmedia files found.")
            return

        print(f"Found {len(backup_files)} backup files.")

        if action == BackupStrategy.ARCHIVE:
            if not archive_dest:
                print("Error: archive_dest must be provided for archive action.")
                return
            
            dest_path = Path(archive_dest)
            dest_path.mkdir(parents=True, exist_ok=True)
            
            for file in backup_files:
                try:
                    # Move file to the archive folder
                    # Note: If duplicate filenames exist in different subfolders, 
                    # we use the full name to avoid overwriting.
                    target = dest_path / file.name
                    shutil.move(str(file), str(target))
                    print(f"[Moved] {file.name} -> {archive_dest}")
                except Exception as e:
                    print(f"[Error] Could not move {file.name}: {e}")

        elif action == BackupStrategy.DELETE:
            for file in backup_files:
                try:
                    file.unlink()
                    print(f"[Deleted] {file.name}")
                except Exception as e:
                    print(f"[Error] Could not delete {file.name}: {e}")

        else:
            print("Invalid action. Please choose 'delete' or 'archive'.")