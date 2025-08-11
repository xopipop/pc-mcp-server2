"""
File operation tools for PC Control MCP Server.
"""

import os
import shutil
import hashlib
import asyncio
import aiofiles
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, AsyncIterator
from datetime import datetime
import mimetypes
import stat

from ..core import (
    StructuredLogger,
    SecurityManager,
    Operation,
    FileOperationException,
    ValidationException,
    get_config
)
from ..utils.platform_utils import normalize_path, is_windows

log = StructuredLogger(__name__)


class FileInfo:
    """File information container."""
    
    def __init__(self, path: Path):
        self.path = path
        self._stat = None
    
    def get_info(self) -> Dict[str, Any]:
        """Get file information."""
        try:
            if not self._stat:
                self._stat = self.path.stat()
            
            # Get file type
            if self.path.is_file():
                file_type = "file"
            elif self.path.is_dir():
                file_type = "directory"
            elif self.path.is_symlink():
                file_type = "symlink"
            else:
                file_type = "other"
            
            # Get MIME type for files
            mime_type = None
            if file_type == "file":
                mime_type, _ = mimetypes.guess_type(str(self.path))
            
            return {
                'path': str(self.path),
                'name': self.path.name,
                'type': file_type,
                'size': self._stat.st_size if file_type == "file" else None,
                'mime_type': mime_type,
                'created': datetime.fromtimestamp(self._stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(self._stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(self._stat.st_atime).isoformat(),
                'permissions': self._get_permissions(),
                'owner': self._get_owner(),
                'is_hidden': self.path.name.startswith('.'),
                'is_readonly': not os.access(str(self.path), os.W_OK),
                'extension': self.path.suffix.lower() if file_type == "file" else None
            }
        except Exception as e:
            raise FileOperationException(f"Failed to get file info: {str(e)}")
    
    def _get_permissions(self) -> Dict[str, Any]:
        """Get file permissions."""
        mode = self._stat.st_mode
        return {
            'octal': oct(stat.S_IMODE(mode)),
            'owner': {
                'read': bool(mode & stat.S_IRUSR),
                'write': bool(mode & stat.S_IWUSR),
                'execute': bool(mode & stat.S_IXUSR)
            },
            'group': {
                'read': bool(mode & stat.S_IRGRP),
                'write': bool(mode & stat.S_IWGRP),
                'execute': bool(mode & stat.S_IXGRP)
            },
            'others': {
                'read': bool(mode & stat.S_IROTH),
                'write': bool(mode & stat.S_IWOTH),
                'execute': bool(mode & stat.S_IXOTH)
            }
        }
    
    def _get_owner(self) -> Dict[str, Any]:
        """Get file owner information."""
        try:
            if is_windows():
                # Windows doesn't have UID/GID
                return {
                    'uid': None,
                    'gid': None,
                    'user': None,
                    'group': None
                }
            else:
                import pwd
                import grp
                
                uid = self._stat.st_uid
                gid = self._stat.st_gid
                
                try:
                    user = pwd.getpwuid(uid).pw_name
                except KeyError:
                    user = str(uid)
                
                try:
                    group = grp.getgrgid(gid).gr_name
                except KeyError:
                    group = str(gid)
                
                return {
                    'uid': uid,
                    'gid': gid,
                    'user': user,
                    'group': group
                }
        except Exception:
            return {
                'uid': getattr(self._stat, 'st_uid', None),
                'gid': getattr(self._stat, 'st_gid', None),
                'user': None,
                'group': None
            }


class FileTools:
    """File operation tools."""
    
    def __init__(self, security_manager: Optional[SecurityManager] = None):
        self.security = security_manager
        self.config = get_config()
    
    async def read_file(self, path: str, encoding: str = 'utf-8', 
                       max_size: Optional[int] = None) -> Dict[str, Any]:
        """Read file contents.
        
        Args:
            path: File path
            encoding: Text encoding (default: utf-8)
            max_size: Maximum file size to read (bytes)
            
        Returns:
            Dictionary with file contents and metadata
        """
        try:
            # Normalize and validate path
            normalized_path = normalize_path(path)
            if self.security:
                validated_path = self.security.validate_input('path', normalized_path)
                if not self.security.check_path_access(validated_path, 'read'):
                    raise FileOperationException(f"Access denied to path: {validated_path}")
            else:
                validated_path = normalized_path
            
            file_path = Path(validated_path)
            
            # Check if file exists
            if not file_path.exists():
                raise FileOperationException(f"File not found: {validated_path}")
            
            if not file_path.is_file():
                raise FileOperationException(f"Path is not a file: {validated_path}")
            
            # Check file size
            file_size = file_path.stat().st_size
            max_allowed_size = max_size or self.config.get('file_operations.max_file_size', 104857600)
            
            if file_size > max_allowed_size:
                raise FileOperationException(
                    f"File too large: {file_size} bytes (max: {max_allowed_size} bytes)"
                )
            
            # Check file extension
            blocked_extensions = self.config.get('file_operations.blocked_extensions', [])
            if file_path.suffix.lower() in blocked_extensions:
                raise FileOperationException(
                    f"File extension '{file_path.suffix}' is blocked"
                )
            
            # Read file
            try:
                async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                    content = await f.read()
                
                # Calculate hash
                file_hash = hashlib.sha256(content.encode(encoding)).hexdigest()
                
                return {
                    'path': str(file_path),
                    'content': content,
                    'size': file_size,
                    'encoding': encoding,
                    'hash': file_hash,
                    'lines': content.count('\n') + 1 if content else 0
                }
                
            except UnicodeDecodeError:
                # Try reading as binary
                async with aiofiles.open(file_path, 'rb') as f:
                    binary_content = await f.read()
                
                return {
                    'path': str(file_path),
                    'content': binary_content.hex(),
                    'size': file_size,
                    'encoding': 'binary',
                    'hash': hashlib.sha256(binary_content).hexdigest(),
                    'is_binary': True
                }
                
        except FileOperationException:
            raise
        except Exception as e:
            log.error(f"Failed to read file '{path}': {e}", exception=e)
            raise FileOperationException(f"Failed to read file: {str(e)}")
    
    async def write_file(self, path: str, content: str, 
                        encoding: str = 'utf-8', 
                        create_dirs: bool = False,
                        append: bool = False) -> Dict[str, Any]:
        """Write content to a file.
        
        Args:
            path: File path
            content: Content to write
            encoding: Text encoding (default: utf-8)
            create_dirs: Create parent directories if they don't exist
            append: Append to file instead of overwriting
            
        Returns:
            Dictionary with operation result
        """
        log.debug(f"Writing file: {path}", append=append, create_dirs=create_dirs)
        
        try:
            # Normalize and validate path
            normalized_path = normalize_path(path)
            if self.security:
                validated_path = self.security.validate_input('path', normalized_path)
                if not self.security.check_path_access(validated_path, 'write'):
                    raise FileOperationException(f"Access denied to path: {validated_path}")
            else:
                validated_path = normalized_path
            
            file_path = Path(validated_path)
            
            # Check file extension
            blocked_extensions = self.config.get('file_operations.blocked_extensions', [])
            if file_path.suffix.lower() in blocked_extensions:
                raise FileOperationException(
                    f"File extension '{file_path.suffix}' is blocked"
                )
            
            # Create directories if needed
            if create_dirs and not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if parent directory exists
            if not file_path.parent.exists():
                raise FileOperationException(
                    f"Parent directory does not exist: {file_path.parent}"
                )
            
            # Write file
            mode = 'a' if append else 'w'
            async with aiofiles.open(file_path, mode, encoding=encoding) as f:
                await f.write(content)
            
            # Get file info
            stat_info = file_path.stat()
            
            return {
                'path': str(file_path),
                'size': stat_info.st_size,
                'mode': mode,
                'encoding': encoding,
                'created': not append and not file_path.exists(),
                'appended': append,
                'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            }
            
        except FileOperationException:
            raise
        except Exception as e:
            log.error(f"Failed to write file '{path}': {e}", exception=e)
            raise FileOperationException(f"Failed to write file: {str(e)}")
    
    async def delete_file(self, path: str, force: bool = False) -> Dict[str, Any]:
        """Delete a file.
        
        Args:
            path: File path
            force: Force deletion even if file is readonly
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Normalize and validate path
            normalized_path = normalize_path(path)
            if self.security:
                validated_path = self.security.validate_input('path', normalized_path)
                if not self.security.check_path_access(validated_path, 'delete'):
                    raise FileOperationException(f"Access denied to path: {validated_path}")
            else:
                validated_path = normalized_path
            
            file_path = Path(validated_path)
            
            # Check if file exists
            if not file_path.exists():
                raise FileOperationException(f"File not found: {validated_path}")
            
            if not file_path.is_file():
                raise FileOperationException(f"Path is not a file: {validated_path}")
            
            # Get file info before deletion
            file_info = FileInfo(file_path).get_info()
            
            # Handle readonly files
            if force and file_info['is_readonly']:
                # Remove readonly attribute
                file_path.chmod(stat.S_IWRITE)
            
            # Delete file
            file_path.unlink()
            
            return {
                'path': str(file_path),
                'deleted': True,
                'file_info': file_info
            }
            
        except FileOperationException:
            raise
        except Exception as e:
            log.error(f"Failed to delete file '{path}': {e}", exception=e)
            raise FileOperationException(f"Failed to delete file: {str(e)}")
    
    async def copy_file(self, source: str, destination: str,
                       overwrite: bool = False,
                       preserve_metadata: bool = True) -> Dict[str, Any]:
        """Copy a file.
        
        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Overwrite if destination exists
            preserve_metadata: Preserve file metadata
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Normalize and validate paths
            source_path = Path(normalize_path(source))
            dest_path = Path(normalize_path(destination))
            
            if self.security:
                source_validated = self.security.validate_input('path', str(source_path))
                dest_validated = self.security.validate_input('path', str(dest_path))
                
                if not self.security.check_path_access(source_validated, 'read'):
                    raise FileOperationException(f"Read access denied: {source_validated}")
                
                if not self.security.check_path_access(dest_validated, 'write'):
                    raise FileOperationException(f"Write access denied: {dest_validated}")
                
                source_path = Path(source_validated)
                dest_path = Path(dest_validated)
            
            # Check source
            if not source_path.exists():
                raise FileOperationException(f"Source file not found: {source_path}")
            
            if not source_path.is_file():
                raise FileOperationException(f"Source is not a file: {source_path}")
            
            # Check destination
            if dest_path.exists() and not overwrite:
                raise FileOperationException(f"Destination already exists: {dest_path}")
            
            # Copy file
            if preserve_metadata:
                shutil.copy2(source_path, dest_path)
            else:
                shutil.copy(source_path, dest_path)
            
            # Get file info
            dest_info = FileInfo(dest_path).get_info()
            
            return {
                'source': str(source_path),
                'destination': str(dest_path),
                'size': dest_info['size'],
                'overwritten': dest_path.exists(),
                'metadata_preserved': preserve_metadata
            }
            
        except FileOperationException:
            raise
        except Exception as e:
            log.error(f"Failed to copy file '{source}' to '{destination}': {e}", exception=e)
            raise FileOperationException(f"Failed to copy file: {str(e)}")
    
    async def move_file(self, source: str, destination: str,
                       overwrite: bool = False) -> Dict[str, Any]:
        """Move a file.
        
        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Overwrite if destination exists
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Normalize and validate paths
            source_path = Path(normalize_path(source))
            dest_path = Path(normalize_path(destination))
            
            if self.security:
                source_validated = self.security.validate_input('path', str(source_path))
                dest_validated = self.security.validate_input('path', str(dest_path))
                
                if not self.security.check_path_access(source_validated, 'delete'):
                    raise FileOperationException(f"Delete access denied: {source_validated}")
                
                if not self.security.check_path_access(dest_validated, 'write'):
                    raise FileOperationException(f"Write access denied: {dest_validated}")
                
                source_path = Path(source_validated)
                dest_path = Path(dest_validated)
            
            # Check source
            if not source_path.exists():
                raise FileOperationException(f"Source file not found: {source_path}")
            
            if not source_path.is_file():
                raise FileOperationException(f"Source is not a file: {source_path}")
            
            # Check destination
            if dest_path.exists() and not overwrite:
                raise FileOperationException(f"Destination already exists: {dest_path}")
            
            # Get source info before move
            source_info = FileInfo(source_path).get_info()
            
            # Move file
            shutil.move(str(source_path), str(dest_path))
            
            return {
                'source': str(source_path),
                'destination': str(dest_path),
                'size': source_info['size'],
                'overwritten': dest_path.exists()
            }
            
        except FileOperationException:
            raise
        except Exception as e:
            log.error(f"Failed to move file '{source}' to '{destination}': {e}", exception=e)
            raise FileOperationException(f"Failed to move file: {str(e)}")
    
    async def list_directory(self, path: str, recursive: bool = False,
                           pattern: Optional[str] = None,
                           include_hidden: bool = True,
                           max_depth: Optional[int] = None) -> List[Dict[str, Any]]:
        """List directory contents.
        
        Args:
            path: Directory path
            recursive: List recursively
            pattern: File pattern filter (glob syntax)
            include_hidden: Include hidden files
            max_depth: Maximum recursion depth
            
        Returns:
            List of file/directory information
        """
        try:
            # Normalize and validate path
            normalized_path = normalize_path(path)
            if self.security:
                validated_path = self.security.validate_input('path', normalized_path)
                if not self.security.check_path_access(validated_path, 'read'):
                    raise FileOperationException(f"Access denied to path: {validated_path}")
            else:
                validated_path = normalized_path
            
            dir_path = Path(validated_path)
            
            # Check if directory exists
            if not dir_path.exists():
                raise FileOperationException(f"Directory not found: {validated_path}")
            
            if not dir_path.is_dir():
                raise FileOperationException(f"Path is not a directory: {validated_path}")
            
            entries = []
            
            if recursive:
                # Recursive listing
                for root, dirs, files in os.walk(dir_path):
                    # Check depth
                    depth = len(Path(root).relative_to(dir_path).parts)
                    if max_depth is not None and depth > max_depth:
                        dirs.clear()  # Don't recurse deeper
                        continue
                    
                    # Process directories
                    for dir_name in dirs:
                        if not include_hidden and dir_name.startswith('.'):
                            continue
                        
                        if pattern and not glob.fnmatch.fnmatch(dir_name, pattern):
                            continue
                        
                        dir_full_path = Path(root) / dir_name
                        try:
                            entries.append(FileInfo(dir_full_path).get_info())
                        except Exception:
                            continue
                    
                    # Process files
                    for file_name in files:
                        if not include_hidden and file_name.startswith('.'):
                            continue
                        
                        if pattern and not glob.fnmatch.fnmatch(file_name, pattern):
                            continue
                        
                        file_full_path = Path(root) / file_name
                        try:
                            entries.append(FileInfo(file_full_path).get_info())
                        except Exception:
                            continue
            else:
                # Non-recursive listing
                for entry in dir_path.iterdir():
                    if not include_hidden and entry.name.startswith('.'):
                        continue
                    
                    if pattern and not glob.fnmatch.fnmatch(entry.name, pattern):
                        continue
                    
                    try:
                        entries.append(FileInfo(entry).get_info())
                    except Exception:
                        continue
            
            # Sort entries
            entries.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
            
            return entries
            
        except FileOperationException:
            raise
        except Exception as e:
            log.error(f"Failed to list directory '{path}': {e}", exception=e)
            raise FileOperationException(f"Failed to list directory: {str(e)}")
    
    async def create_directory(self, path: str, parents: bool = True,
                             exist_ok: bool = True) -> Dict[str, Any]:
        """Create a directory.
        
        Args:
            path: Directory path
            parents: Create parent directories if needed
            exist_ok: Don't raise error if directory exists
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Normalize and validate path
            normalized_path = normalize_path(path)
            if self.security:
                validated_path = self.security.validate_input('path', normalized_path)
                if not self.security.check_path_access(validated_path, 'write'):
                    raise FileOperationException(f"Access denied to path: {validated_path}")
            else:
                validated_path = normalized_path
            
            dir_path = Path(validated_path)
            
            # Check if already exists
            if dir_path.exists():
                if not exist_ok:
                    raise FileOperationException(f"Directory already exists: {validated_path}")
                
                if not dir_path.is_dir():
                    raise FileOperationException(f"Path exists but is not a directory: {validated_path}")
                
                created = False
            else:
                # Create directory
                dir_path.mkdir(parents=parents, exist_ok=exist_ok)
                created = True
            
            # Get directory info
            dir_info = FileInfo(dir_path).get_info()
            
            return {
                'path': str(dir_path),
                'created': created,
                'parents_created': parents and created,
                'info': dir_info
            }
            
        except FileOperationException:
            raise
        except Exception as e:
            log.error(f"Failed to create directory '{path}': {e}", exception=e)
            raise FileOperationException(f"Failed to create directory: {str(e)}")
    
    async def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get detailed file information.
        
        Args:
            path: File path
            
        Returns:
            Dictionary with file information
        """
        try:
            # Normalize and validate path
            normalized_path = normalize_path(path)
            if self.security:
                validated_path = self.security.validate_input('path', normalized_path)
                if not self.security.check_path_access(validated_path, 'read'):
                    raise FileOperationException(f"Access denied to path: {validated_path}")
            else:
                validated_path = normalized_path
            
            file_path = Path(validated_path)
            
            # Check if exists
            if not file_path.exists():
                raise FileOperationException(f"Path not found: {validated_path}")
            
            # Get file info
            info = FileInfo(file_path).get_info()
            
            # Add additional info for files
            if file_path.is_file():
                # Calculate hash for small files
                if info['size'] and info['size'] < 10485760:  # 10MB
                    try:
                        with open(file_path, 'rb') as f:
                            info['md5'] = hashlib.md5(f.read()).hexdigest()
                            f.seek(0)
                            info['sha256'] = hashlib.sha256(f.read()).hexdigest()
                    except Exception:
                        pass
            
            return info
            
        except FileOperationException:
            raise
        except Exception as e:
            log.error(f"Failed to get file info for '{path}': {e}", exception=e)
            raise FileOperationException(f"Failed to get file info: {str(e)}")
    
    async def search_files(self, pattern: str, directory: str,
                         recursive: bool = True,
                         case_sensitive: bool = False,
                         file_type: Optional[str] = None) -> List[str]:
        """Search for files matching pattern.
        
        Args:
            pattern: Search pattern (glob or regex)
            directory: Directory to search in
            recursive: Search recursively
            case_sensitive: Case-sensitive search
            file_type: Filter by file type ('file', 'directory')
            
        Returns:
            List of matching file paths
        """
        try:
            # Normalize and validate directory
            normalized_dir = normalize_path(directory)
            if self.security:
                validated_dir = self.security.validate_input('path', normalized_dir)
                if not self.security.check_path_access(validated_dir, 'read'):
                    raise FileOperationException(f"Access denied to directory: {validated_dir}")
            else:
                validated_dir = normalized_dir
            
            search_dir = Path(validated_dir)
            
            # Check if directory exists
            if not search_dir.exists():
                raise FileOperationException(f"Directory not found: {validated_dir}")
            
            if not search_dir.is_dir():
                raise FileOperationException(f"Path is not a directory: {validated_dir}")
            
            matches = []
            
            # Determine if pattern is regex or glob
            is_regex = any(c in pattern for c in ['(', ')', '[', ']', '{', '}', '^', '$', '+', '?'])
            
            if is_regex:
                import re
                flags = 0 if case_sensitive else re.IGNORECASE
                regex = re.compile(pattern, flags)
            
            # Search function
            def match_pattern(name: str) -> bool:
                if is_regex:
                    return bool(regex.search(name))
                else:
                    if case_sensitive:
                        return glob.fnmatch.fnmatch(name, pattern)
                    else:
                        return glob.fnmatch.fnmatch(name.lower(), pattern.lower())
            
            # Search files
            if recursive:
                for root, dirs, files in os.walk(search_dir):
                    # Filter by type and pattern
                    if file_type != 'file':
                        for dir_name in dirs:
                            if match_pattern(dir_name):
                                matches.append(str(Path(root) / dir_name))
                    
                    if file_type != 'directory':
                        for file_name in files:
                            if match_pattern(file_name):
                                matches.append(str(Path(root) / file_name))
            else:
                for entry in search_dir.iterdir():
                    if file_type == 'file' and not entry.is_file():
                        continue
                    if file_type == 'directory' and not entry.is_dir():
                        continue
                    
                    if match_pattern(entry.name):
                        matches.append(str(entry))
            
            # Sort results
            matches.sort()
            
            return matches
            
        except FileOperationException:
            raise
        except Exception as e:
            log.error(f"Failed to search files with pattern '{pattern}': {e}", exception=e)
            raise FileOperationException(f"Failed to search files: {str(e)}")
    
    async def get_disk_usage(self, path: str) -> Dict[str, Any]:
        """Get disk usage for a path.
        
        Args:
            path: Path to check
            
        Returns:
            Dictionary with disk usage information
        """
        try:
            # Normalize and validate path
            normalized_path = normalize_path(path)
            if self.security:
                validated_path = self.security.validate_input('path', normalized_path)
            else:
                validated_path = normalized_path
            
            check_path = Path(validated_path)
            
            # Get disk usage
            if check_path.is_file():
                # File size
                size = check_path.stat().st_size
                disk_usage = shutil.disk_usage(check_path.parent)
            else:
                # Directory size
                size = sum(f.stat().st_size for f in check_path.rglob('*') if f.is_file())
                disk_usage = shutil.disk_usage(check_path)
            
            return {
                'path': str(check_path),
                'size': size,
                'size_human': self._format_size(size),
                'disk': {
                    'total': disk_usage.total,
                    'used': disk_usage.used,
                    'free': disk_usage.free,
                    'percent': (disk_usage.used / disk_usage.total) * 100
                }
            }
            
        except Exception as e:
            log.error(f"Failed to get disk usage for '{path}': {e}", exception=e)
            raise FileOperationException(f"Failed to get disk usage: {str(e)}")
    
    def _format_size(self, size: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"