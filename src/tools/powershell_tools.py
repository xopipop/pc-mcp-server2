"""
PowerShell tools with safety guards for PC Control MCP Server.
"""

import asyncio
import re
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..core import (
    StructuredLogger,
    SecurityManager,
    SystemException,
    ValidationException,
)
from ..utils.platform_utils import is_windows


log = StructuredLogger(__name__)


class PowerShellTools:
    """Safe PowerShell execution helpers.

    Provides guarded invocation of PowerShell with basic allow/deny checks
    and timeouts. Designed for Windows environments.
    """

    def __init__(self, security_manager: Optional[SecurityManager] = None):
        self.security = security_manager

        # Simple denylist for dangerous tokens/cmdlets (case-insensitive)
        # NOTE: This is a best-effort filter; enforce allowlists in config for production.
        self._forbidden_patterns = [
            r"\bInvoke-Expression\b",
            r"\bIEX\b",
            r"\bAdd-Type\b",
            r"\bNew-Object\s+System\.Net\.WebClient\b",
            r"\bStart-Process\b",
            r"\bSet-ExecutionPolicy\b",
            r"\bInvoke-WebRequest\b",
            r"\bInvoke-RestMethod\b",
            r"\bImport-Module\s+\S+\b",  # disallow arbitrary imports by default
        ]

    def _validate_script_safe(self, script: str, safe_mode: bool) -> None:
        if not safe_mode:
            return
        for pattern in self._forbidden_patterns:
            if re.search(pattern, script, flags=re.IGNORECASE):
                raise ValidationException(f"PowerShell script contains forbidden construct: {pattern}")

    async def invoke(self,
                     script: str,
                     timeout: Optional[int] = 30,
                     safe_mode: bool = True) -> Dict[str, Any]:
        """Invoke a PowerShell script block safely.

        Args:
            script: PowerShell code to execute (script block)
            timeout: Seconds to wait before terminating
            safe_mode: Apply denylist checks to the script

        Returns:
            Dict with stdout, stderr, return_code, timings
        """
        if not is_windows():
            raise SystemException("PowerShell is only supported on Windows")

        # Security validation/sanitization
        if self.security:
            script = self.security.sanitize_input(script)
        self._validate_script_safe(script, safe_mode)

        # Compose PowerShell invocation
        # Use -NoProfile and -NonInteractive to reduce side effects
        # Avoid ExecutionPolicy changes; rely on system policy
        args = [
            'powershell',
            '-NoProfile',
            '-NonInteractive',
            '-Command',
            script,
        ]

        started_at = datetime.now(timezone.utc)
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                timed_out = False
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                stdout, stderr = b"", b"Execution timed out"
                timed_out = True

            finished_at = datetime.now(timezone.utc)

            return {
                'action': 'invoke_powershell',
                'safe_mode': safe_mode,
                'timeout_seconds': timeout,
                'timed_out': timed_out,
                'return_code': process.returncode,
                'stdout': stdout.decode('utf-8', errors='replace'),
                'stderr': stderr.decode('utf-8', errors='replace'),
                'started_at': started_at.isoformat(),
                'finished_at': finished_at.isoformat(),
                'duration_seconds': (finished_at - started_at).total_seconds(),
                'success': (process.returncode == 0) and not timed_out,
            }

        except Exception as e:
            log.error(f"Failed to invoke PowerShell: {e}", exception=e)
            raise SystemException(f"Failed to invoke PowerShell: {str(e)}")


