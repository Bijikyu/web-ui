
"""
File utility functions for browser automation and data management.

This module provides robust file handling utilities that are essential for
browser automation workflows. These functions handle common file operations
with proper error handling, cross-platform compatibility, and consideration
for the specific needs of browser automation scenarios.

Key functionality areas:
- Safe file reading/writing with encoding handling
- Directory management and cleanup
- File type detection and validation
- Temporary file management
- File monitoring and change detection
- Cross-platform path handling
- Atomic file operations for data integrity

Browser automation generates various types of files (screenshots, downloads,
reports, logs) that need careful handling to ensure data integrity and
prevent file system conflicts.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Iterator, Tuple
import json
import logging
import hashlib
import mimetypes
from contextlib import contextmanager
import fcntl  # Unix file locking (will handle Windows separately)

logger = logging.getLogger(__name__)

# Common file extensions and their purposes in browser automation
FILE_TYPE_MAPPING = {
    '.html': 'web_page',
    '.pdf': 'document',
    '.png': 'screenshot',
    '.jpg': 'screenshot',
    '.jpeg': 'screenshot',
    '.webp': 'screenshot',
    '.mp4': 'recording',
    '.webm': 'recording',
    '.json': 'data',
    '.csv': 'data',
    '.txt': 'text',
    '.log': 'log',
    '.zip': 'archive',
    '.har': 'network_trace'
}

# Maximum file sizes for different operation types (in bytes)
# These limits prevent memory issues and provide safety boundaries
MAX_FILE_SIZES = {
    'text_read': 10 * 1024 * 1024,     # 10MB for text files
    'json_read': 50 * 1024 * 1024,     # 50MB for JSON files
    'binary_read': 100 * 1024 * 1024,  # 100MB for binary files
    'upload': 500 * 1024 * 1024,       # 500MB for file uploads
}


class FileOperationError(Exception):
    """
    Custom exception for file operation failures.
    
    This exception provides detailed information about file operation failures,
    making it easier to debug issues and provide meaningful error messages
    to users. It includes context about what operation was attempted and why
    it failed.
    """
    
    def __init__(self, message: str, file_path: str = "", operation: str = "", 
                 original_error: Optional[Exception] = None):
        """
        Initialize file operation error with detailed context.
        
        Args:
            message: Human-readable error description
            file_path: Path of file involved in the operation
            operation: Type of operation that failed
            original_error: Original exception that caused the failure
        """
        self.message = message
        self.file_path = file_path
        self.operation = operation
        self.original_error = original_error
        
        # Create comprehensive error message
        full_message = f"File operation '{operation}' failed"
        if file_path:
            full_message += f" for '{file_path}'"
        full_message += f": {message}"
        if original_error:
            full_message += f" (Original error: {original_error})"
        
        super().__init__(full_message)


def ensure_directory_exists(directory_path: Union[str, Path], 
                          create_parents: bool = True,
                          mode: int = 0o755) -> Path:
    """
    Ensures a directory exists, creating it if necessary.
    
    This function provides safe directory creation with proper error handling
    and permission setting. It's essential for automation workflows that need
    to create output directories for screenshots, downloads, or reports.
    
    Args:
        directory_path: Path to the directory to ensure exists
        create_parents: Whether to create parent directories if they don't exist
        mode: Permission mode for created directories (Unix-style)
        
    Returns:
        Path: Pathlib Path object for the directory
        
    Raises:
        FileOperationError: If directory creation fails
        
    Why this function is necessary:
    - Prevents crashes when trying to write files to non-existent directories
    - Handles permission issues gracefully
    - Provides consistent directory creation across the application
    - Supports both relative and absolute paths
    - Cross-platform compatibility
    
    Design decisions:
    - Returns Path object for modern path handling
    - Uses 755 permissions by default (owner read/write/execute, others read/execute)
    - Creates parent directories by default for convenience
    - Validates the result to ensure the directory actually exists
    """
    path_obj = Path(directory_path)
    
    try:
        # Create directory with parents if it doesn't exist
        path_obj.mkdir(parents=create_parents, exist_ok=True)
        
        # Set permissions on Unix-like systems
        if hasattr(os, 'chmod') and os.name != 'nt':  # Not Windows
            try:
                path_obj.chmod(mode)
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not set permissions on {path_obj}: {e}")
        
        # Verify the directory actually exists and is accessible
        if not path_obj.exists():
            raise FileOperationError(
                "Directory was not created successfully",
                str(path_obj),
                "directory_creation"
            )
        
        if not path_obj.is_dir():
            raise FileOperationError(
                "Path exists but is not a directory",
                str(path_obj),
                "directory_validation"
            )
        
        logger.debug(f"Ensured directory exists: {path_obj}")
        return path_obj
        
    except Exception as e:
        if isinstance(e, FileOperationError):
            raise
        raise FileOperationError(
            f"Failed to create directory",
            str(directory_path),
            "directory_creation",
            e
        )


def safe_read_text_file(file_path: Union[str, Path], 
                       encoding: str = 'utf-8',
                       max_size: Optional[int] = None,
                       fallback_encodings: List[str] = None) -> str:
    """
    Safely reads a text file with encoding detection and size limits.
    
    Text file reading in automation contexts can be problematic due to
    encoding issues, large file sizes, and various text formats. This
    function provides robust text reading with fallback options.
    
    Args:
        file_path: Path to the text file
        encoding: Primary encoding to try
        max_size: Maximum file size to read (bytes)
        fallback_encodings: Alternative encodings to try if primary fails
        
    Returns:
        str: Content of the file
        
    Raises:
        FileOperationError: If file cannot be read
        
    Why encoding handling is complex:
    - Web-generated files may use various encodings
    - Browser downloads can have unexpected encoding
    - Log files may contain mixed encoding
    - Cross-platform text files have different line endings
    
    Safety features:
    - Size limit prevents memory exhaustion
    - Encoding fallback handles various text formats
    - Error handling provides detailed failure information
    - Line ending normalization for cross-platform compatibility
    """
    if fallback_encodings is None:
        fallback_encodings = ['latin-1', 'cp1252', 'iso-8859-1']
    
    path_obj = Path(file_path)
    
    # Validate file exists and is readable
    if not path_obj.exists():
        raise FileOperationError(
            "File does not exist",
            str(file_path),
            "text_read"
        )
    
    if not path_obj.is_file():
        raise FileOperationError(
            "Path is not a file",
            str(file_path),
            "text_read"
        )
    
    # Check file size if limit specified
    max_size = max_size or MAX_FILE_SIZES['text_read']
    file_size = path_obj.stat().st_size
    
    if file_size > max_size:
        raise FileOperationError(
            f"File size ({file_size} bytes) exceeds maximum ({max_size} bytes)",
            str(file_path),
            "text_read"
        )
    
    # Try to read with primary encoding first, then fallbacks
    encodings_to_try = [encoding] + fallback_encodings
    last_error = None
    
    for enc in encodings_to_try:
        try:
            with open(path_obj, 'r', encoding=enc, errors='replace') as f:
                content = f.read()
                
            # Normalize line endings for cross-platform compatibility
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            logger.debug(f"Successfully read {file_size} bytes from {file_path} using {enc} encoding")
            return content
            
        except UnicodeDecodeError as e:
            last_error = e
            logger.debug(f"Failed to read {file_path} with {enc} encoding: {e}")
            continue
        except Exception as e:
            raise FileOperationError(
                f"Failed to read file",
                str(file_path),
                "text_read",
                e
            )
    
    # If all encodings failed
    raise FileOperationError(
        f"Could not read file with any encoding (tried: {encodings_to_try})",
        str(file_path),
        "text_read",
        last_error
    )


def safe_write_text_file(file_path: Union[str, Path], 
                        content: str,
                        encoding: str = 'utf-8',
                        atomic: bool = True,
                        backup: bool = False) -> Path:
    """
    Safely writes text content to a file with atomic operations.
    
    Writing files in automation contexts requires careful handling to prevent
    data corruption, especially when multiple processes might access the same
    files or when operations might be interrupted.
    
    Args:
        file_path: Path where to write the file
        content: Text content to write
        encoding: Text encoding to use
        atomic: Whether to use atomic write (write to temp file, then rename)
        backup: Whether to create a backup of existing file
        
    Returns:
        Path: Path object for the written file
        
    Raises:
        FileOperationError: If write operation fails
        
    Why atomic writes matter:
    - Prevents partial file corruption if process is interrupted
    - Ensures other processes don't read partially written files
    - Provides transaction-like behavior for file operations
    - Essential for configuration files and important data
    
    Atomic write process:
    1. Write content to temporary file in same directory
    2. Flush and sync the temporary file to disk
    3. Atomically rename temporary file to target filename
    4. This ensures the target file is never in a partially written state
    """
    path_obj = Path(file_path)
    
    # Ensure parent directory exists
    ensure_directory_exists(path_obj.parent)
    
    # Create backup if requested and file exists
    if backup and path_obj.exists():
        backup_path = path_obj.with_suffix(path_obj.suffix + '.backup')
        try:
            shutil.copy2(path_obj, backup_path)
            logger.debug(f"Created backup: {backup_path}")
        except Exception as e:
            logger.warning(f"Could not create backup of {file_path}: {e}")
    
    try:
        if atomic:
            # Atomic write using temporary file
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.tmp',
                prefix=path_obj.name + '_',
                dir=path_obj.parent
            )
            
            try:
                with os.fdopen(temp_fd, 'w', encoding=encoding) as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                
                # Atomically replace target file
                os.replace(temp_path, path_obj)
                logger.debug(f"Atomically wrote {len(content)} characters to {file_path}")
                
            except Exception:
                # Clean up temporary file if something went wrong
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
        else:
            # Direct write (non-atomic)
            with open(path_obj, 'w', encoding=encoding) as f:
                f.write(content)
            logger.debug(f"Wrote {len(content)} characters to {file_path}")
        
        return path_obj
        
    except Exception as e:
        raise FileOperationError(
            f"Failed to write file",
            str(file_path),
            "text_write",
            e
        )


def safe_read_json_file(file_path: Union[str, Path], 
                       max_size: Optional[int] = None) -> Dict[str, Any]:
    """
    Safely reads and parses a JSON file with size and format validation.
    
    JSON files are commonly used in browser automation for configuration,
    data storage, and API responses. This function provides robust JSON
    reading with proper error handling and validation.
    
    Args:
        file_path: Path to the JSON file
        max_size: Maximum file size to read
        
    Returns:
        Dict[str, Any]: Parsed JSON data
        
    Raises:
        FileOperationError: If file cannot be read or parsed
        
    JSON-specific considerations:
    - Large JSON files can consume significant memory
    - Malformed JSON can crash parsers
    - JSON files may contain sensitive configuration data
    - Different systems may generate JSON with varying formatting
    
    Validation steps:
    1. Check file existence and size
    2. Read content with encoding handling
    3. Parse JSON with detailed error reporting
    4. Validate basic structure (must be dict or list)
    """
    max_size = max_size or MAX_FILE_SIZES['json_read']
    
    try:
        # Read the file content first
        content = safe_read_text_file(file_path, max_size=max_size)
        
        # Parse JSON with detailed error handling
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise FileOperationError(
                f"Invalid JSON format: {e.msg} at line {e.lineno}, column {e.colno}",
                str(file_path),
                "json_parse",
                e
            )
        
        # Validate that we got a reasonable data structure
        if not isinstance(data, (dict, list)):
            raise FileOperationError(
                f"JSON must contain an object or array, got {type(data).__name__}",
                str(file_path),
                "json_validation"
            )
        
        logger.debug(f"Successfully parsed JSON from {file_path}")
        return data
        
    except FileOperationError:
        raise
    except Exception as e:
        raise FileOperationError(
            f"Failed to read JSON file",
            str(file_path),
            "json_read",
            e
        )


def safe_write_json_file(file_path: Union[str, Path], 
                        data: Any,
                        indent: int = 2,
                        atomic: bool = True,
                        backup: bool = False) -> Path:
    """
    Safely writes data to a JSON file with formatting and validation.
    
    This function provides robust JSON writing with proper formatting,
    validation, and atomic operations to prevent data corruption.
    
    Args:
        file_path: Path where to write the JSON file
        data: Data to serialize to JSON
        indent: Indentation for pretty formatting (None for compact)
        atomic: Whether to use atomic write operations
        backup: Whether to create backup of existing file
        
    Returns:
        Path: Path object for the written file
        
    Raises:
        FileOperationError: If data cannot be serialized or file cannot be written
        
    JSON serialization considerations:
    - Not all Python objects are JSON serializable
    - Large data structures can cause memory issues
    - Formatting affects file size and readability
    - Atomic writes prevent corruption during serialization
    
    Serialization process:
    1. Validate data is JSON serializable
    2. Serialize to JSON string with error handling
    3. Write using atomic text file operations
    4. Verify file was written correctly
    """
    try:
        # Test serialization first to catch errors early
        json_content = json.dumps(data, indent=indent, ensure_ascii=False)
        
        # Write the JSON content
        result_path = safe_write_text_file(
            file_path, 
            json_content, 
            atomic=atomic, 
            backup=backup
        )
        
        logger.debug(f"Successfully wrote JSON to {file_path}")
        return result_path
        
    except (TypeError, ValueError) as e:
        raise FileOperationError(
            f"Data is not JSON serializable: {e}",
            str(file_path),
            "json_serialize",
            e
        )
    except FileOperationError:
        raise
    except Exception as e:
        raise FileOperationError(
            f"Failed to write JSON file",
            str(file_path),
            "json_write",
            e
        )


@contextmanager
def temporary_directory(prefix: str = 'automation_', 
                       cleanup: bool = True) -> Iterator[Path]:
    """
    Context manager for creating and cleaning up temporary directories.
    
    Browser automation often needs temporary directories for downloads,
    screenshots, extracted files, etc. This context manager ensures
    proper cleanup even if operations fail.
    
    Args:
        prefix: Prefix for temporary directory name
        cleanup: Whether to remove directory when context exits
        
    Yields:
        Path: Path to the temporary directory
        
    Usage:
        with temporary_directory() as temp_dir:
            # Use temp_dir for operations
            screenshot_path = temp_dir / "screenshot.png"
            # Directory is automatically cleaned up
    
    Why context managers are ideal for temporary resources:
    - Guaranteed cleanup even if exceptions occur
    - Clear scope for resource lifetime
    - Prevents resource leaks in long-running applications
    - Makes temporary resource usage explicit in code
    """
    temp_dir = None
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        logger.debug(f"Created temporary directory: {temp_dir}")
        yield temp_dir
    finally:
        if cleanup and temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get comprehensive information about a file.
    
    This function provides detailed file metadata that's useful for
    automation workflows, logging, and file management decisions.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        Dict[str, Any]: Comprehensive file information
        
    Raises:
        FileOperationError: If file cannot be accessed
        
    Information collected:
    - Basic metadata (size, timestamps, permissions)
    - File type classification
    - Content type detection
    - Hash for integrity checking
    - Readability and writeability status
    
    Use cases:
    - Logging file operations
    - Validating downloaded files
    - File management and cleanup decisions
    - Security and integrity checking
    """
    path_obj = Path(file_path)
    
    if not path_obj.exists():
        raise FileOperationError(
            "File does not exist",
            str(file_path),
            "file_info"
        )
    
    try:
        stat_info = path_obj.stat()
        
        # Basic file information
        info = {
            'path': str(path_obj.absolute()),
            'name': path_obj.name,
            'stem': path_obj.stem,
            'suffix': path_obj.suffix,
            'size_bytes': stat_info.st_size,
            'created_time': stat_info.st_ctime,
            'modified_time': stat_info.st_mtime,
            'accessed_time': stat_info.st_atime,
            'is_file': path_obj.is_file(),
            'is_directory': path_obj.is_dir(),
            'is_symlink': path_obj.is_symlink(),
        }
        
        # File type classification
        extension = path_obj.suffix.lower()
        info['file_type'] = FILE_TYPE_MAPPING.get(extension, 'unknown')
        
        # MIME type detection
        mime_type, encoding = mimetypes.guess_type(str(path_obj))
        info['mime_type'] = mime_type
        info['encoding'] = encoding
        
        # Permission checking
        info['readable'] = os.access(path_obj, os.R_OK)
        info['writable'] = os.access(path_obj, os.W_OK)
        info['executable'] = os.access(path_obj, os.X_OK)
        
        # Size-based classifications
        if info['size_bytes'] == 0:
            info['size_category'] = 'empty'
        elif info['size_bytes'] < 1024:
            info['size_category'] = 'tiny'
        elif info['size_bytes'] < 1024 * 1024:
            info['size_category'] = 'small'
        elif info['size_bytes'] < 100 * 1024 * 1024:
            info['size_category'] = 'medium'
        else:
            info['size_category'] = 'large'
        
        # Hash for integrity checking (for reasonable-sized files)
        if info['is_file'] and info['size_bytes'] < 10 * 1024 * 1024:  # 10MB limit
            try:
                with open(path_obj, 'rb') as f:
                    content = f.read()
                    info['md5_hash'] = hashlib.md5(content).hexdigest()
                    info['sha256_hash'] = hashlib.sha256(content).hexdigest()
            except Exception as e:
                logger.debug(f"Could not calculate hash for {file_path}: {e}")
                info['md5_hash'] = None
                info['sha256_hash'] = None
        else:
            info['md5_hash'] = None
            info['sha256_hash'] = None
        
        return info
        
    except Exception as e:
        raise FileOperationError(
            f"Failed to get file information",
            str(file_path),
            "file_info",
            e
        )


def clean_filename(filename: str, 
                  replacement: str = '_',
                  max_length: int = 255) -> str:
    """
    Cleans a filename to be safe for filesystem operations.
    
    Browser automation often needs to create filenames from web content,
    which can contain characters that are invalid or problematic for
    file systems. This function creates safe, valid filenames.
    
    Args:
        filename: Original filename to clean
        replacement: Character to replace invalid characters with
        max_length: Maximum filename length
        
    Returns:
        str: Cleaned filename safe for filesystem use
        
    Cleaning operations:
    - Remove or replace invalid filesystem characters
    - Handle reserved names (CON, PRN, etc. on Windows)
    - Limit length to filesystem constraints
    - Preserve file extension when possible
    - Ensure filename is not empty after cleaning
    
    Cross-platform considerations:
    - Windows has more filename restrictions than Unix
    - Case sensitivity varies by filesystem
    - Unicode handling differs across systems
    - Reserved names are platform-specific
    """
    import re
    import string
    
    if not filename:
        return "unnamed_file"
    
    # Remove or replace invalid characters
    # Windows forbidden characters: < > : " | ? * \ /
    # Also remove control characters and ensure ASCII-safe
    invalid_chars = '<>:"|?*\\/'
    for char in invalid_chars:
        filename = filename.replace(char, replacement)
    
    # Remove control characters and excessive whitespace
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', replacement, filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    
    # Handle Windows reserved names
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_part = Path(filename).stem.upper()
    if name_part in reserved_names:
        filename = f"file_{filename}"
    
    # Limit length while preserving extension
    if len(filename) > max_length:
        path_obj = Path(filename)
        extension = path_obj.suffix
        stem = path_obj.stem
        
        # Calculate how much room we have for the stem
        available_length = max_length - len(extension)
        if available_length > 10:  # Minimum reasonable stem length
            truncated_stem = stem[:available_length]
            filename = truncated_stem + extension
        else:
            # Extension is too long, truncate everything
            filename = filename[:max_length]
    
    # Ensure we don't end up with empty filename
    if not filename or filename.isspace():
        filename = "unnamed_file"
    
    # Remove trailing dots and spaces (Windows requirement)
    filename = filename.rstrip('. ')
    
    return filename


def monitor_file_changes(file_path: Union[str, Path], 
                        callback: callable,
                        check_interval: float = 1.0,
                        max_duration: Optional[float] = None) -> bool:
    """
    Monitor a file for changes and call a callback when changes are detected.
    
    This function is useful for monitoring log files, configuration files,
    or output files that are being written by browser automation processes.
    
    Args:
        file_path: Path to file to monitor
        callback: Function to call when file changes (receives file_path as argument)
        check_interval: How often to check for changes (seconds)
        max_duration: Maximum time to monitor (seconds, None for indefinite)
        
    Returns:
        bool: True if monitoring completed normally, False if stopped early
        
    Monitoring approach:
    - Uses file modification time to detect changes
    - Handles cases where file doesn't exist initially
    - Provides timeout to prevent infinite monitoring
    - Graceful handling of file system errors
    
    Use cases:
    - Monitoring browser log files for specific events
    - Watching for completion of download operations
    - Tracking changes to configuration files
    - Monitoring output files from automation processes
    """
    path_obj = Path(file_path)
    last_mtime = 0
    start_time = time.time()
    
    logger.debug(f"Starting file monitoring for {file_path}")
    
    try:
        while True:
            # Check timeout
            if max_duration and (time.time() - start_time) > max_duration:
                logger.debug(f"File monitoring timed out after {max_duration} seconds")
                return False
            
            try:
                if path_obj.exists():
                    current_mtime = path_obj.stat().st_mtime
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        logger.debug(f"File change detected: {file_path}")
                        
                        # Call the callback function
                        try:
                            callback(path_obj)
                        except Exception as e:
                            logger.error(f"Error in file change callback: {e}")
                
            except (OSError, IOError) as e:
                logger.debug(f"File system error while monitoring {file_path}: {e}")
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        logger.info("File monitoring stopped by user")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in file monitoring: {e}")
        return False
