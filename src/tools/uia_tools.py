"""
Windows UI Automation tools using uiautomation/pywinauto.
"""

from typing import Dict, Any, Optional, List

from ..core import (
    StructuredLogger,
    SecurityManager,
    SystemException,
    ValidationException,
)
from ..utils.platform_utils import is_windows

log = StructuredLogger(__name__)

# Optional imports guarded
try:
    import uiautomation as uia
    _HAS_UIA = True
except Exception:
    _HAS_UIA = False
    uia = None  # type: ignore

try:
    from pywinauto import Application
    _HAS_PYWIN = True
except Exception:
    _HAS_PYWIN = False
    Application = None  # type: ignore


class UIATools:
    """High-level wrappers for UI Automation on Windows."""

    def __init__(self, security_manager: Optional[SecurityManager] = None):
        self.security = security_manager
        if not is_windows():
            log.warning("UI Automation tools are only available on Windows")

    def _require(self):
        if not is_windows():
            raise SystemException("UI Automation is supported on Windows only")
        if not _HAS_UIA:
            raise SystemException("uiautomation package is not available")

    async def focus_window(self, name: Optional[str] = None, class_name: Optional[str] = None) -> Dict[str, Any]:
        """Focus window by name or class."""
        self._require()
        try:
            conds = []
            if name:
                conds.append(uia.NameProperty == name)
            if class_name:
                conds.append(uia.ClassNameProperty == class_name)
            condition = conds[0] if len(conds) == 1 else uia.AndCondition(*conds) if conds else uia.TrueCondition()

            win = uia.WindowControl(searchDepth=1, RegexName=name if name else None)
            target = win if win.Exists(0, 0) else uia.ControlFromHandle(uia.GetForegroundWindow())
            if name or class_name:
                target = uia.Control(condition)
            if not target.Exists(0, 0):
                return {"focused": False, "success": False}
            target.SetTopmost(True)
            target.SetFocus()
            return {"focused": True, "name": target.Name, "class": target.ClassName, "success": True}
        except Exception as e:
            log.error(f"Failed to focus window: {e}")
            raise SystemException(f"Failed to focus window: {str(e)}")

    async def click(self, name: Optional[str] = None, control_type: Optional[str] = None) -> Dict[str, Any]:
        """Click a UI element by name and/or control type."""
        self._require()
        try:
            ctrl = None
            if name and control_type:
                ctrl = uia.Control(uia.AndCondition(uia.NameProperty == name, uia.ControlTypeProperty == getattr(uia.ControlType, control_type, None)))
            elif name:
                ctrl = uia.Control(uia.NameProperty == name)
            else:
                return {"success": False, "error": "name or control_type required"}

            if not ctrl.Exists(3, 0.2):
                return {"clicked": False, "success": False}
            ctrl.Click()
            return {"clicked": True, "name": ctrl.Name, "control_type": control_type, "success": True}
        except Exception as e:
            log.error(f"Failed to click control: {e}")
            raise SystemException(f"Failed to click control: {str(e)}")

    async def type_text(self, text: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Type text into the focused element or element by name."""
        self._require()
        try:
            if self.security:
                text = self.security.validate_input('command', text)
            if name:
                ctrl = uia.Control(uia.NameProperty == name)
                if not ctrl.Exists(3, 0.2):
                    return {"typed": False, "success": False}
                ctrl.SetFocus()
            uia.SendKeys(text, waitTime=0.01)
            return {"typed": True, "length": len(text), "success": True}
        except Exception as e:
            log.error(f"Failed to type text: {e}")
            raise SystemException(f"Failed to type text: {str(e)}")


