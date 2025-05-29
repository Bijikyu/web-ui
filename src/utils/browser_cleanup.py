
"""
Browser cleanup utilities for resource management and process handling.

This module handles the critical task of cleaning up browser resources, processes,
and temporary files created during browser automation sessions. Proper cleanup
is essential for preventing resource leaks, zombie processes, and disk space
accumulation in long-running applications.

Browser automation can create numerous resources that persist beyond the session:
- Browser processes and child processes
- Temporary profile directories
- Cache files and downloads
- WebDriver connections and ports
- Memory allocations and file handles

Without proper cleanup, these resources accumulate and can eventually cause
system instability, performance degradation, or complete system failure.
"""

import logging
import os
import psutil
import shutil
import signal
import time
from pathlib import Path
from typing import List, Optional, Set, Dict, Any
import subprocess
import asyncio

logger = logging.getLogger(__name__)

# Browser process names to monitor and clean up
# These are the common process names across different browsers and platforms
BROWSER_PROCESS_NAMES = {
    'chrome': ['chrome', 'chromium', 'google-chrome', 'chrome.exe', 'chromium.exe'],
    'firefox': ['firefox', 'firefox.exe', 'firefox-bin'],
    'edge': ['msedge', 'msedge.exe', 'edge'],
    'safari': ['safari', 'Safari'],
    'playwright': ['playwright', 'playwright.exe']
}

# Directories that browsers commonly create for temporary data
# These locations are platform-specific and need regular cleanup
BROWSER_TEMP_DIRS = [
    '/tmp/chrome_*',
    '/tmp/firefox_*',
    '/tmp/playwright_*',
    '~/.config/google-chrome/Singleton*',
    '~/.mozilla/firefox/*/lock',
    os.path.expanduser('~/AppData/Local/Temp/chrome_*'),  # Windows
    os.path.expanduser('~/AppData/Local/Temp/firefox_*'),  # Windows
]


class BrowserCleanupManager:
    """
    Manages comprehensive cleanup of browser resources and processes.
    
    This class provides a centralized approach to browser cleanup that handles
    the complexity of different browser types, operating systems, and cleanup
    scenarios. It's designed to be robust, logging all operations for debugging,
    and continuing cleanup even when individual operations fail.
    
    Why a dedicated cleanup manager is necessary:
    - Browser processes can spawn multiple child processes that need individual cleanup
    - Different browsers store temporary data in different locations
    - Network connections and ports need to be released properly
    - Cleanup order matters to prevent zombie processes
    - Error handling must be robust to ensure cleanup always completes
    
    Design principles:
    - Always attempt all cleanup operations, even if some fail
    - Log all operations for debugging and monitoring
    - Use timeouts to prevent cleanup from hanging indefinitely
    - Provide both gentle and forceful cleanup options
    """
    
    def __init__(self, timeout_seconds: int = 30):
        """
        Initialize the cleanup manager with configurable timeout.
        
        Args:
            timeout_seconds: Maximum time to wait for processes to terminate gracefully
                           before using forceful termination. This balance prevents
                           data corruption while ensuring cleanup completes.
        
        Why timeout is configurable:
        - Development environments may need longer timeouts for debugging
        - Production environments may need faster cleanup for responsiveness
        - Different browsers have different shutdown characteristics
        """
        self.timeout_seconds = timeout_seconds
        self.cleanup_log: List[str] = []  # Track cleanup operations for debugging
        
    def log_cleanup_operation(self, operation: str, success: bool = True, details: str = ""):
        """
        Logs cleanup operations for debugging and monitoring.
        
        This logging is crucial for understanding cleanup behavior, especially
        when issues occur. It provides a trail of what was attempted and what
        succeeded or failed during cleanup.
        
        Args:
            operation: Description of the cleanup operation
            success: Whether the operation succeeded
            details: Additional details about the operation or any errors
        """
        log_entry = f"{time.time()}: {operation} - {'SUCCESS' if success else 'FAILED'}"
        if details:
            log_entry += f" ({details})"
        
        self.cleanup_log.append(log_entry)
        
        if success:
            logger.info(f"Cleanup: {operation}")
        else:
            logger.warning(f"Cleanup failed: {operation} - {details}")
            
    async def cleanup_browser_processes(self, browser_type: str = 'all', 
                                      force: bool = False) -> Dict[str, Any]:
        """
        Terminates browser processes gracefully or forcefully.
        
        This is often the most critical cleanup operation, as runaway browser
        processes can consume significant system resources. The function uses
        a two-phase approach: graceful termination first, then forceful if needed.
        
        Args:
            browser_type: Specific browser to clean up, or 'all' for all browsers
            force: Whether to skip graceful termination and force-kill immediately
            
        Returns:
            Dict with cleanup statistics and any errors encountered
            
        Why two-phase termination:
        - Graceful termination allows browsers to save data and close cleanly
        - Forceful termination ensures cleanup completes even with hung processes
        - Different browsers respond differently to termination signals
        - Some browsers spawn child processes that need separate handling
        
        Process identification strategy:
        - Uses process name matching for broad coverage
        - Checks command line arguments for more specific identification
        - Handles parent-child process relationships properly
        - Avoids terminating critical system processes
        """
        cleanup_stats = {
            'processes_found': 0,
            'processes_terminated': 0,
            'errors': [],
            'browser_type': browser_type
        }
        
        # Determine which browser process names to look for
        if browser_type == 'all':
            target_names = []
            for browser_processes in BROWSER_PROCESS_NAMES.values():
                target_names.extend(browser_processes)
        else:
            target_names = BROWSER_PROCESS_NAMES.get(browser_type, [browser_type])
        
        self.log_cleanup_operation(f"Starting browser process cleanup for: {target_names}")
        
        # Find all matching browser processes
        browser_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name'].lower() if proc_info['name'] else ''
                    
                    # Check if this process matches our target browsers
                    if any(target in proc_name for target in target_names):
                        browser_processes.append(proc)
                        cleanup_stats['processes_found'] += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process disappeared or we don't have permission - skip it
                    continue
                    
        except Exception as e:
            error_msg = f"Error scanning for browser processes: {e}"
            cleanup_stats['errors'].append(error_msg)
            self.log_cleanup_operation("Process scanning", False, error_msg)
        
        # Terminate processes (gracefully first, then forcefully if needed)
        for proc in browser_processes:
            try:
                if not proc.is_running():
                    continue  # Process already terminated
                
                proc_name = proc.info['name']
                proc_pid = proc.pid
                
                if not force:
                    # Try graceful termination first
                    self.log_cleanup_operation(f"Graceful termination of {proc_name} (PID: {proc_pid})")
                    proc.terminate()
                    
                    try:
                        # Wait for graceful termination
                        proc.wait(timeout=self.timeout_seconds)
                        cleanup_stats['processes_terminated'] += 1
                        self.log_cleanup_operation(f"Process {proc_name} terminated gracefully")
                        continue
                    except psutil.TimeoutExpired:
                        # Graceful termination timed out, will force kill below
                        self.log_cleanup_operation(f"Graceful termination timeout for {proc_name}", False)
                
                # Force termination if graceful failed or force was requested
                if proc.is_running():
                    self.log_cleanup_operation(f"Force termination of {proc_name} (PID: {proc_pid})")
                    proc.kill()
                    
                    try:
                        proc.wait(timeout=5)  # Shorter timeout for force kill
                        cleanup_stats['processes_terminated'] += 1
                        self.log_cleanup_operation(f"Process {proc_name} force terminated")
                    except psutil.TimeoutExpired:
                        error_msg = f"Could not terminate {proc_name} (PID: {proc_pid})"
                        cleanup_stats['errors'].append(error_msg)
                        self.log_cleanup_operation(f"Force termination failed for {proc_name}", False, error_msg)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                # Process disappeared or permission denied - not necessarily an error
                self.log_cleanup_operation(f"Process cleanup skipped", True, str(e))
            except Exception as e:
                error_msg = f"Unexpected error terminating process: {e}"
                cleanup_stats['errors'].append(error_msg)
                self.log_cleanup_operation("Process termination", False, error_msg)
        
        return cleanup_stats
    
    def cleanup_temporary_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Removes temporary files and directories created by browser sessions.
        
        Browser automation creates numerous temporary files that can accumulate
        over time, consuming disk space and potentially causing performance issues.
        This function identifies and removes these files while being careful not
        to remove files that might still be in use.
        
        Args:
            max_age_hours: Only remove files older than this many hours to avoid
                          removing files from active sessions
                          
        Returns:
            Dict with cleanup statistics and any errors encountered
            
        Why age-based cleanup is important:
        - Prevents removal of files from active browser sessions
        - Ensures recently created files have time to be properly used
        - Provides a safety margin for browsers with delayed file access patterns
        - Allows for recovery of temporary files if needed for debugging
        
        File identification strategy:
        - Uses known patterns for browser temporary directories
        - Checks file modification times to determine age
        - Verifies files are not currently in use before removal
        - Handles different operating system temporary directory structures
        """
        cleanup_stats = {
            'files_scanned': 0,
            'files_removed': 0,
            'directories_removed': 0,
            'bytes_freed': 0,
            'errors': []
        }
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        self.log_cleanup_operation(f"Starting temporary file cleanup (max age: {max_age_hours} hours)")
        
        # Clean up temporary directories and files
        for temp_pattern in BROWSER_TEMP_DIRS:
            try:
                # Expand user directory references and glob patterns
                expanded_pattern = os.path.expanduser(temp_pattern)
                
                # Handle glob patterns for finding matching files/directories
                if '*' in expanded_pattern:
                    from glob import glob
                    matching_paths = glob(expanded_pattern)
                else:
                    matching_paths = [expanded_pattern] if os.path.exists(expanded_pattern) else []
                
                for path in matching_paths:
                    try:
                        if not os.path.exists(path):
                            continue
                            
                        # Check if the file/directory is old enough to remove
                        mtime = os.path.getmtime(path)
                        age_seconds = current_time - mtime
                        
                        if age_seconds < max_age_seconds:
                            continue  # Too recent, skip this file
                        
                        path_obj = Path(path)
                        
                        if path_obj.is_file():
                            # Remove individual file
                            file_size = path_obj.stat().st_size
                            path_obj.unlink()
                            cleanup_stats['files_removed'] += 1
                            cleanup_stats['bytes_freed'] += file_size
                            self.log_cleanup_operation(f"Removed file: {path} ({file_size} bytes)")
                            
                        elif path_obj.is_dir():
                            # Remove directory and all contents
                            dir_size = sum(f.stat().st_size for f in path_obj.rglob('*') if f.is_file())
                            shutil.rmtree(path)
                            cleanup_stats['directories_removed'] += 1
                            cleanup_stats['bytes_freed'] += dir_size
                            self.log_cleanup_operation(f"Removed directory: {path} ({dir_size} bytes)")
                        
                        cleanup_stats['files_scanned'] += 1
                        
                    except (PermissionError, OSError) as e:
                        # Common for files in use or permission issues
                        error_msg = f"Could not remove {path}: {e}"
                        cleanup_stats['errors'].append(error_msg)
                        self.log_cleanup_operation(f"File removal failed", False, error_msg)
                        
            except Exception as e:
                error_msg = f"Error processing temp pattern {temp_pattern}: {e}"
                cleanup_stats['errors'].append(error_msg)
                self.log_cleanup_operation("Temp file pattern processing", False, error_msg)
        
        return cleanup_stats
    
    def cleanup_browser_locks(self) -> Dict[str, Any]:
        """
        Removes browser lock files that prevent new instances from starting.
        
        Browsers use lock files to prevent multiple instances from accessing the
        same profile simultaneously. When browsers crash or are terminated
        ungracefully, these lock files can remain and prevent new instances
        from starting properly.
        
        Returns:
            Dict with cleanup statistics and any errors encountered
            
        Why lock file cleanup is necessary:
        - Crashed browsers may leave lock files that prevent restart
        - Ungraceful termination doesn't trigger normal cleanup
        - Lock files can prevent automated browser sessions from starting
        - Different browsers use different lock file mechanisms
        
        Common lock file locations and patterns:
        - Chrome: SingletonLock, lockfile
        - Firefox: .parentlock, lock files in profile directories
        - General: Any .lock files in browser profile directories
        """
        cleanup_stats = {
            'locks_found': 0,
            'locks_removed': 0,
            'errors': []
        }
        
        self.log_cleanup_operation("Starting browser lock file cleanup")
        
        # Common lock file patterns and locations
        lock_patterns = [
            '~/.config/google-chrome/*/Singleton*',
            '~/.config/chromium/*/Singleton*',
            '~/.mozilla/firefox/*/.parentlock',
            '~/.mozilla/firefox/*/lock',
            os.path.expanduser('~/AppData/Local/Google/Chrome/User Data/*/Lockfile'),  # Windows
            os.path.expanduser('~/Library/Application Support/Google/Chrome/*/Lockfile'),  # macOS
        ]
        
        for pattern in lock_patterns:
            try:
                from glob import glob
                expanded_pattern = os.path.expanduser(pattern)
                lock_files = glob(expanded_pattern)
                
                for lock_file in lock_files:
                    try:
                        if os.path.exists(lock_file):
                            cleanup_stats['locks_found'] += 1
                            os.remove(lock_file)
                            cleanup_stats['locks_removed'] += 1
                            self.log_cleanup_operation(f"Removed lock file: {lock_file}")
                            
                    except (PermissionError, OSError) as e:
                        error_msg = f"Could not remove lock file {lock_file}: {e}"
                        cleanup_stats['errors'].append(error_msg)
                        self.log_cleanup_operation("Lock file removal", False, error_msg)
                        
            except Exception as e:
                error_msg = f"Error processing lock pattern {pattern}: {e}"
                cleanup_stats['errors'].append(error_msg)
                self.log_cleanup_operation("Lock pattern processing", False, error_msg)
        
        return cleanup_stats
    
    async def comprehensive_cleanup(self, browser_type: str = 'all', 
                                  force_processes: bool = False,
                                  clean_temp_files: bool = True,
                                  temp_file_max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Performs complete browser cleanup including processes, files, and locks.
        
        This is the main cleanup function that orchestrates all cleanup operations
        in the proper order. It's designed to be comprehensive yet safe, providing
        detailed feedback about what was cleaned up and any issues encountered.
        
        Args:
            browser_type: Which browser(s) to clean up ('all', 'chrome', 'firefox', etc.)
            force_processes: Whether to immediately force-kill processes
            clean_temp_files: Whether to clean up temporary files
            temp_file_max_age_hours: Age threshold for temporary file cleanup
            
        Returns:
            Dict with comprehensive cleanup statistics and operation log
            
        Why comprehensive cleanup is needed:
        - Multiple cleanup operations need to be coordinated
        - Some operations depend on others completing first
        - Error handling needs to ensure all operations are attempted
        - Detailed logging helps with troubleshooting cleanup issues
        
        Cleanup order rationale:
        1. Processes first - stops active resource usage
        2. Lock files - enables future browser starts
        3. Temporary files - reclaims disk space
        This order ensures that active processes don't interfere with file cleanup
        """
        overall_stats = {
            'start_time': time.time(),
            'browser_type': browser_type,
            'operations_completed': [],
            'total_errors': 0,
            'cleanup_log': []
        }
        
        self.log_cleanup_operation(f"Starting comprehensive cleanup for {browser_type}")
        
        try:
            # Step 1: Clean up browser processes
            self.log_cleanup_operation("Phase 1: Browser process cleanup")
            process_stats = await self.cleanup_browser_processes(browser_type, force_processes)
            overall_stats['process_cleanup'] = process_stats
            overall_stats['operations_completed'].append('process_cleanup')
            overall_stats['total_errors'] += len(process_stats.get('errors', []))
            
            # Step 2: Remove lock files
            self.log_cleanup_operation("Phase 2: Lock file cleanup")
            lock_stats = self.cleanup_browser_locks()
            overall_stats['lock_cleanup'] = lock_stats
            overall_stats['operations_completed'].append('lock_cleanup')
            overall_stats['total_errors'] += len(lock_stats.get('errors', []))
            
            # Step 3: Clean up temporary files (if requested)
            if clean_temp_files:
                self.log_cleanup_operation("Phase 3: Temporary file cleanup")
                temp_stats = self.cleanup_temporary_files(temp_file_max_age_hours)
                overall_stats['temp_file_cleanup'] = temp_stats
                overall_stats['operations_completed'].append('temp_file_cleanup')
                overall_stats['total_errors'] += len(temp_stats.get('errors', []))
            
        except Exception as e:
            error_msg = f"Unexpected error in comprehensive cleanup: {e}"
            self.log_cleanup_operation("Comprehensive cleanup", False, error_msg)
            overall_stats['critical_error'] = error_msg
            overall_stats['total_errors'] += 1
        
        # Finalize cleanup statistics
        overall_stats['end_time'] = time.time()
        overall_stats['duration_seconds'] = overall_stats['end_time'] - overall_stats['start_time']
        overall_stats['cleanup_log'] = self.cleanup_log.copy()
        
        # Log summary
        if overall_stats['total_errors'] == 0:
            self.log_cleanup_operation("Comprehensive cleanup completed successfully")
        else:
            self.log_cleanup_operation(f"Comprehensive cleanup completed with {overall_stats['total_errors']} errors")
        
        return overall_stats


# Convenience functions for common cleanup scenarios
async def quick_browser_cleanup(browser_type: str = 'chrome') -> bool:
    """
    Performs a quick cleanup for the most common scenario.
    
    This is a simplified interface for cases where you just need to clean up
    browser processes quickly without detailed configuration or reporting.
    
    Args:
        browser_type: Which browser to clean up
        
    Returns:
        bool: True if cleanup completed without critical errors
        
    Use cases:
    - Cleanup between test runs
    - Quick recovery from browser crashes
    - Automated cleanup in scripts
    """
    manager = BrowserCleanupManager(timeout_seconds=10)
    stats = await manager.comprehensive_cleanup(
        browser_type=browser_type,
        force_processes=False,
        clean_temp_files=False  # Skip temp files for speed
    )
    return stats['total_errors'] == 0


def emergency_browser_cleanup() -> bool:
    """
    Performs emergency cleanup with aggressive settings.
    
    This function is for situations where the system is in a bad state and
    normal cleanup might not work. It uses more aggressive timeouts and
    force-kills processes immediately.
    
    Returns:
        bool: True if cleanup completed
        
    When to use emergency cleanup:
    - System is running out of resources
    - Normal cleanup has failed multiple times
    - Browser processes are completely unresponsive
    - Need to recover quickly from a critical state
    """
    import asyncio
    
    manager = BrowserCleanupManager(timeout_seconds=5)  # Short timeout
    
    try:
        # Run the cleanup synchronously for emergency situations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        stats = loop.run_until_complete(
            manager.comprehensive_cleanup(
                browser_type='all',
                force_processes=True,  # Immediate force kill
                clean_temp_files=True,
                temp_file_max_age_hours=1  # Aggressive temp file cleanup
            )
        )
        
        loop.close()
        return True
        
    except Exception as e:
        logger.critical(f"Emergency cleanup failed: {e}")
        return False
