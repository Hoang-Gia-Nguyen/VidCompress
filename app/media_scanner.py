import shutil
from pathlib import Path
from typing import List

def list_media_files(root_dir: str, extensions: List[str]) -> List[Path]:
    """
    Recursively scans a directory for media files with specific extensions.
    
    Args:
        root_dir (str): The path to the starting directory.
        extensions (list): A list of file extensions to look for (e.g., ['.mp4', '.mkv']).
        
    Returns:
        list: A list of pathlib.Path objects for the found files.
    """
    media_files = []
    path_obj = Path(root_dir)
    
    # Check if the provided path is a valid directory
    if not path_obj.exists() or not path_obj.is_dir():
        print(f"Error: The directory '{root_dir}' does not exist or is not a directory.")
        return []

    # Normalize extensions to lowercase for case-insensitive comparison
    normalized_extensions = [ext.lower() for ext in extensions]

    # rglob('*') performs a recursive search through all subfolders
    for file_path in path_obj.rglob('*'):
        # Check if it's a file and if its suffix (extension) is in our list
        if file_path.is_file() and file_path.suffix.lower() in normalized_extensions:
            media_files.append(file_path)
            
    return media_files

def manage_backups(root_dir: str, action: str = 'archive', archive_dest: str = None):
    """
    Finds all .originalmedia files and either deletes them or moves them to an archive.
    
    Args:
        root_dir (str): The directory to scan.
        action (str): Either 'delete' or 'archive'. Defaults to 'archive'.
        archive_dest (str): The folder to move files to if action is 'archive'.
    """
    path_obj = Path(root_dir)
    # Search for all files ending in .originalmedia recursively
    backup_files = list(path_obj.rglob("*.originalmedia"))

    if not backup_files:
        print("No .originalmedia files found.")
        return

    print(f"Found {len(backup_files)} backup files.")

    if action == 'archive':
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

    elif action == 'delete':
        for file in backup_files:
            try:
                file.unlink()
                print(f"[Deleted] {file.name}")
            except Exception as e:
                print(f"[Error] Could not delete {file.name}: {e}")

    else:
        print("Invalid action. Please choose 'delete' or 'archive'.")