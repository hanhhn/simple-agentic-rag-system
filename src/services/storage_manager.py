"""
Storage manager for file operations.
"""
import shutil
import time
from pathlib import Path
from typing import Optional

from src.core.logging import get_logger
from src.core.exceptions import FileStorageError, FileNotFoundError as CoreFileNotFoundError
from src.core.config import get_config


logger = get_logger(__name__)


class StorageManager:
    """
    Manager for file storage operations.
    
    This class handles all file storage operations including saving,
    retrieving, deleting, and managing uploaded documents.
    
    Attributes:
        storage_path: Base directory for file storage
        
    Example:
        >>> manager = StorageManager()
        >>> manager.save_file(content, "document.txt", "collection1")
        >>> content = manager.get_file("document.txt", "collection1")
    """
    
    def __init__(self, storage_path: Optional[Path | str] = None) -> None:
        """
        Initialize storage manager.
        
        Args:
            storage_path: Base storage directory (uses config default if None)
        """
        config = get_config()
        default_path = config.storage.storage_path if config.storage.storage_path else Path("./data/documents")
        self.storage_path = Path(storage_path or default_path)
        
        # Ensure storage_path is not None
        if not self.storage_path:
            raise ValueError("Storage path cannot be None")
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Storage manager initialized", storage_path=str(self.storage_path))
    
    def _get_collection_path(self, collection_name: str) -> Path:
        """
        Get path for a collection directory.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Path to collection directory
        """
        from src.utils.validators import CollectionValidator
        
        validator = CollectionValidator()
        validator.validate_collection_name(collection_name)
        
        collection_path = self.storage_path / collection_name
        collection_path.mkdir(parents=True, exist_ok=True)
        
        return collection_path
    
    def save_file(
        self,
        content: bytes,
        filename: str,
        collection_name: str,
        overwrite: bool = False
    ) -> str:
        """
        Save a file to storage.
        
        Args:
            content: File content as bytes
            filename: Name of the file
            collection_name: Collection to store file in
            overwrite: Whether to overwrite existing file
            
        Returns:
            Full path to saved file
            
        Raises:
            FileStorageError: If save fails
            
        Example:
            >>> manager = StorageManager()
            >>> path = manager.save_file(b"content", "doc.txt", "my_collection")
        """
        start_time = time.time()
        
        try:
            logger.info(
                "Starting file save",
                filename=filename,
                collection=collection_name,
                size_bytes=len(content),
                size_mb=f"{len(content) / (1024 * 1024):.2f}",
                overwrite=overwrite
            )
            
            collection_path = self._get_collection_path(collection_name)
            filepath = collection_path / filename
            
            # Check if file exists
            check_start = time.time()
            if filepath.exists() and not overwrite:
                elapsed = time.time() - start_time
                logger.warning(
                    "File already exists",
                    filepath=str(filepath),
                    elapsed_time=f"{elapsed:.4f}s"
                )
                raise FileStorageError(
                    f"File already exists: {filename}",
                    details={"filename": filename, "collection": collection_name}
                )
            check_elapsed = time.time() - check_start
            
            # Save file
            write_start = time.time()
            filepath.write_bytes(content)
            write_elapsed = time.time() - write_start
            
            total_elapsed = time.time() - start_time
            
            logger.info(
                "File saved successfully",
                filepath=str(filepath),
                filename=filename,
                collection=collection_name,
                size_bytes=len(content),
                size_mb=f"{len(content) / (1024 * 1024):.2f}",
                check_time=f"{check_elapsed:.6f}s",
                write_time=f"{write_elapsed:.4f}s",
                total_time=f"{total_elapsed:.4f}s",
                write_speed=f"{len(content) / write_elapsed / (1024 * 1024):.2f} MB/s" if write_elapsed > 0 else "0"
            )
            
            return str(filepath)
            
        except FileStorageError:
            elapsed = time.time() - start_time
            logger.error(
                "File save failed (FileStorageError)",
                filename=filename,
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Failed to save file",
                filename=filename,
                collection=collection_name,
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise FileStorageError(
                f"Failed to save file '{filename}': {str(e)}",
                details={
                    "filename": filename,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": f"{elapsed:.4f}s"
                }
            )
    
    def get_file(self, filename: str, collection_name: str) -> bytes:
        """
        Retrieve a file from storage.
        
        Args:
            filename: Name of the file
            collection_name: Collection containing the file
            
        Returns:
            File content as bytes
            
        Raises:
            CoreFileNotFoundError: If file doesn't exist
            FileStorageError: If retrieval fails
            
        Example:
            >>> manager = StorageManager()
            >>> content = manager.get_file("doc.txt", "my_collection")
        """
        try:
            collection_path = self._get_collection_path(collection_name)
            filepath = collection_path / filename
            
            if not filepath.exists():
                raise CoreFileNotFoundError(
                    f"File not found: {filename}",
                    details={"filename": filename, "collection": collection_name}
                )
            
            content = filepath.read_bytes()
            
            logger.info(
                "File retrieved successfully",
                filepath=str(filepath),
                size_bytes=len(content),
                collection=collection_name
            )
            
            return content
            
        except CoreFileNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to retrieve file", filename=filename, error=str(e))
            raise FileStorageError(
                f"Failed to retrieve file '{filename}': {str(e)}",
                details={"filename": filename, "error": str(e)}
            )
    
    def delete_file(self, filename: str, collection_name: str) -> None:
        """
        Delete a file from storage.
        
        Args:
            filename: Name of the file
            collection_name: Collection containing the file
            
        Raises:
            CoreFileNotFoundError: If file doesn't exist
            FileStorageError: If deletion fails
            
        Example:
            >>> manager = StorageManager()
            >>> manager.delete_file("doc.txt", "my_collection")
        """
        try:
            collection_path = self._get_collection_path(collection_name)
            filepath = collection_path / filename
            
            if not filepath.exists():
                raise CoreFileNotFoundError(
                    f"File not found: {filename}",
                    details={"filename": filename, "collection": collection_name}
                )
            
            filepath.unlink()
            
            logger.info(
                "File deleted successfully",
                filepath=str(filepath),
                collection=collection_name
            )
            
        except CoreFileNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete file", filename=filename, error=str(e))
            raise FileStorageError(
                f"Failed to delete file '{filename}': {str(e)}",
                details={"filename": filename, "error": str(e)}
            )
    
    def list_files(self, collection_name: str) -> list[str]:
        """
        List all files in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            List of filenames
            
        Example:
            >>> manager = StorageManager()
            >>> files = manager.list_files("my_collection")
            >>> print(files)  # ["doc1.txt", "doc2.pdf", ...]
        """
        try:
            collection_path = self._get_collection_path(collection_name)
            
            files = []
            for item in collection_path.iterdir():
                if item.is_file():
                    files.append(item.name)
            
            logger.info(
                "Listed files in collection",
                collection=collection_name,
                count=len(files)
            )
            
            return sorted(files)
            
        except Exception as e:
            logger.error("Failed to list files", collection=collection_name, error=str(e))
            raise FileStorageError(
                f"Failed to list files: {str(e)}",
                details={"collection": collection_name, "error": str(e)}
            )
    
    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection and all its files.
        
        Args:
            collection_name: Name of the collection
            
        Raises:
            FileStorageError: If deletion fails
            
        Example:
            >>> manager = StorageManager()
            >>> manager.delete_collection("my_collection")
        """
        try:
            collection_path = self._get_collection_path(collection_name)
            
            if collection_path.exists():
                shutil.rmtree(collection_path)
                
                logger.info(
                    "Collection deleted successfully",
                    collection=collection_name,
                    path=str(collection_path)
                )
            else:
                logger.warning(
                    "Collection does not exist",
                    collection=collection_name
                )
                
        except Exception as e:
            logger.error("Failed to delete collection", collection=collection_name, error=str(e))
            raise FileStorageError(
                f"Failed to delete collection '{collection_name}': {str(e)}",
                details={"collection": collection_name, "error": str(e)}
            )
    
    def list_collections(self) -> list[str]:
        """
        List all collections.
        
        Returns:
            List of collection names
            
        Example:
            >>> manager = StorageManager()
            >>> collections = manager.list_collections()
            >>> print(collections)  # ["collection1", "collection2", ...]
        """
        try:
            collections = []
            
            for item in self.storage_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    collections.append(item.name)
            
            logger.info(
                "Listed collections",
                count=len(collections)
            )
            
            return sorted(collections)
            
        except Exception as e:
            logger.error("Failed to list collections", error=str(e))
            raise FileStorageError(
                f"Failed to list collections: {str(e)}",
                details={"error": str(e)}
            )
    
    def get_storage_info(self) -> dict:
        """
        Get information about storage usage.
        
        Returns:
            Dictionary with storage statistics
            
        Example:
            >>> manager = StorageManager()
            >>> info = manager.get_storage_info()
            >>> print(info)  # {"collections": 5, "files": 25, "total_bytes": 10485760}
        """
        try:
            total_collections = 0
            total_files = 0
            total_bytes = 0
            
            for collection_dir in self.storage_path.iterdir():
                if collection_dir.is_dir():
                    total_collections += 1
                    
                    for item in collection_dir.rglob("*"):
                        if item.is_file():
                            total_files += 1
                            total_bytes += item.stat().st_size
            
            info = {
                "collections": total_collections,
                "files": total_files,
                "total_bytes": total_bytes,
                "total_mb": round(total_bytes / (1024 * 1024), 2),
                "storage_path": str(self.storage_path)
            }
            
            logger.info(
                "Storage info retrieved",
                **info
            )
            
            return info
            
        except Exception as e:
            logger.error("Failed to get storage info", error=str(e))
            raise FileStorageError(
                f"Failed to get storage info: {str(e)}",
                details={"error": str(e)}
            )
