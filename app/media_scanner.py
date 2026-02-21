from pathlib import Path
from typing import List, Iterator, Optional


class MediaScanner:
    """
    A class to scan directories for media files and manage backup files.
    """

    extension_list = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"]

    def __init__(self):
        """
        Initialize the MediaScanner with a root directory.

        Args:
            root_dir (str): The path to the starting directory.
        """
        pass

    def get_extension_list(self) -> List[str]:
        """
        Retrieves the list of file extensions that the MediaScanner uses to identify media files.

        Returns:
            list: A list of file extensions.
        """
        return self.extension_list

    def set_extension_list(self, extensions: List[str]):
        """
        Sets the list of file extensions that the MediaScanner uses to identify media files.

        Args:
            extensions (list): A list of file extensions. Each extension must start with a dot.

        Raises:
            ValueError: If any extension does not start with a dot.
        """
        for ext in extensions:
            if not ext.startswith("."):
                raise ValueError(f"Extension '{ext}' must start with a dot.")
        self.extension_list = extensions

    def iter_media_files(
        self, root_dir: str, extensions: Optional[List[str]] = None
    ) -> Iterator[Path]:
        """
        Recursively scans a directory for media files with specific extensions.

        Args:
            root_dir (str): The path to the directory to scan.
            extensions (list): A list of file extensions to look for (e.g., ['.mp4', '.mkv']).
                               If None, it uses the default extensions set in the MediaScanner.

        Yields:
            Iterator[Path]: An iterator of pathlib.Path objects for the found files.
        """
        # Check if the provided path is a valid directory
        root_path = Path(root_dir)
        if not root_path.exists() or not root_path.is_dir():
            print(
                f"Error: The directory '{root_dir}' does not exist or is not a directory."
            )
            return []

        if extensions is None:
            extensions = self.extension_list

        # Normalize extensions to lowercase for case-insensitive comparison
        normalized_extensions = [ext.lower() for ext in extensions]

        # rglob('*') performs a recursive search through all subfolders
        for file_path in root_path.rglob("*"):
            # Check if it's a file and if its suffix (extension) is in our list
            if (
                file_path.is_file()
                and file_path.suffix.lower() in normalized_extensions
            ):
                yield Path(file_path)
