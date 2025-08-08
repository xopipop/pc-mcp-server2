"""
Windows Task Scheduler tools for PC Control MCP Server.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..core import (
    StructuredLogger,
    SecurityManager,
    SystemException,
    ValidationException,
)
from ..utils.platform_utils import is_windows, is_admin


log = StructuredLogger(__name__)


class SchedulerTools:
    """Windows Task Scheduler management.

    Uses schtasks.exe for compatibility without extra dependencies.
    """

    def __init__(self, security_manager: Optional[SecurityManager] = None):
        self.security = security_manager

    def _ensure_windows_admin(self) -> None:
        if not is_windows():
            raise SystemException("Task Scheduler is supported on Windows only")
        if not is_admin():
            raise SystemException("Administrator privileges are required for Task Scheduler operations")

    async def create_task(self,
                          name: str,
                          command: str,
                          schedule: str = 'ONCE',
                          start_time: Optional[str] = None,
                          start_date: Optional[str] = None,
                          run_as: Optional[str] = None,
                          password: Optional[str] = None) -> Dict[str, Any]:
        """Create a scheduled task.

        Args:
            name: Task name (e.g., \\MyTask)
            command: Command to run
            schedule: ONEVENT|MINUTE|HOURLY|DAILY|WEEKLY|MONTHLY|ONCE|ONLOGON|ONIDLE|ONSTART
            start_time: HH:MM (24h) if applicable
            start_date: yyyy/mm/dd if applicable
            run_as: username (optional)
            password: password (optional; if omitted, /RU will run with no password prompt for some accounts)
        """
        self._ensure_windows_admin()

        if self.security:
            name = self.security.sanitize_input(name)
            command = self.security.sanitize_input(command)

        args = ['schtasks', '/Create', '/TN', name, '/TR', command, '/SC', schedule]
        if start_time:
            args += ['/ST', start_time]
        if start_date:
            args += ['/SD', start_date]
        if run_as:
            args += ['/RU', run_as]
            if password is not None:
                args += ['/RP', password]

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        return {
            'action': 'create_task',
            'name': name,
            'return_code': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
            'success': process.returncode == 0,
        }

    async def run_task(self, name: str) -> Dict[str, Any]:
        """Run an existing task immediately."""
        self._ensure_windows_admin()
        if self.security:
            name = self.security.sanitize_input(name)

        process = await asyncio.create_subprocess_exec(
            'schtasks', '/Run', '/TN', name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return {
            'action': 'run_task',
            'name': name,
            'return_code': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
            'success': process.returncode == 0,
        }

    async def delete_task(self, name: str, force: bool = False) -> Dict[str, Any]:
        """Delete a task."""
        self._ensure_windows_admin()
        if self.security:
            name = self.security.sanitize_input(name)

        args = ['schtasks', '/Delete', '/TN', name]
        if force:
            args += ['/F']

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return {
            'action': 'delete_task',
            'name': name,
            'return_code': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
            'success': process.returncode == 0,
        }

    async def query_task(self, name: str) -> Dict[str, Any]:
        """Query task status and last run result."""
        self._ensure_windows_admin()
        if self.security:
            name = self.security.sanitize_input(name)

        process = await asyncio.create_subprocess_exec(
            'schtasks', '/Query', '/TN', name, '/V', '/FO', 'LIST',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        output = stdout.decode('utf-8', errors='replace')
        info: Dict[str, Any] = {'raw': output}
        # Minimal parse of key fields
        for line in output.splitlines():
            if ':' in line:
                key, val = line.split(':', 1)
                info[key.strip()] = val.strip()
        return {
            'action': 'query_task',
            'name': name,
            'info': info,
            'return_code': process.returncode,
            'stderr': stderr.decode('utf-8', errors='replace'),
            'success': process.returncode == 0,
        }


