"""
GUI automation tools for PC Control MCP Server.
"""

import asyncio
import base64
import io
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime, timezone

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None
    
from PIL import Image, ImageDraw, ImageGrab
import numpy as np

from ..core import (
    StructuredLogger,
    SecurityManager,
    Operation,
    AutomationException,
    ValidationException,
    get_config
)

log = StructuredLogger(__name__)

# Configure pyautogui safety features
if PYAUTOGUI_AVAILABLE:
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1


def require_pyautogui(func):
    """Decorator to check if pyautogui is available."""
    async def wrapper(*args, **kwargs):
        if not PYAUTOGUI_AVAILABLE:
            raise AutomationException("PyAutoGUI is not available. Please install tkinter and pyautogui.")
        return await func(*args, **kwargs)
    return wrapper


class AutomationTools:
    """GUI automation tools using pyautogui."""
    
    def __init__(self, security_manager: Optional[SecurityManager] = None):
        if not PYAUTOGUI_AVAILABLE:
            log.warning("PyAutoGUI is not available. GUI automation features will be disabled.")
            
        self.security = security_manager
        self.config = get_config()
        
        # Configure from config (handle Pydantic model or dict)
        settings = self.config.get('gui_automation', None)
        if PYAUTOGUI_AVAILABLE and settings is not None:
            try:
                # Pydantic model attributes in our config: min_delay, failsafe
                pause_val = getattr(settings, 'min_delay', None)
                failsafe_val = getattr(settings, 'failsafe', None)
                if pause_val is None or failsafe_val is None:
                    # Fallback if settings is a dict-like
                    try:
                        pause_val = settings.get('min_delay', 0.1)  # type: ignore[attr-defined]
                        failsafe_val = settings.get('failsafe', True)  # type: ignore[attr-defined]
                    except Exception:
                        pause_val = 0.1
                        failsafe_val = True
                pyautogui.PAUSE = 0.0 if pause_val is None else float(pause_val)
                pyautogui.FAILSAFE = True if failsafe_val is None else bool(failsafe_val)
            except Exception:
                # Safe defaults
                pyautogui.PAUSE = 0.1
                pyautogui.FAILSAFE = True
        
        # Screen size cache
        self._screen_size = None
        self._screen_size_time = None
        self._screen_cache_ttl = 60  # 60 seconds
        
    def _check_availability(self):
        """Check if PyAutoGUI is available."""
        if not PYAUTOGUI_AVAILABLE:
            raise AutomationException("PyAutoGUI is not available. Please install tkinter and pyautogui.")
    
    def _get_screen_size(self) -> Tuple[int, int]:
        """Get cached screen size."""
        if not PYAUTOGUI_AVAILABLE:
            return (1920, 1080)  # Default fallback size
            
        now = time.time()
        if (self._screen_size is None or 
            self._screen_size_time is None or 
            now - self._screen_size_time > self._screen_cache_ttl):
            self._screen_size = pyautogui.size()
            self._screen_size_time = now
        return self._screen_size
    
    def _validate_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Validate and clamp coordinates to screen bounds."""
        width, height = self._get_screen_size()
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        return x, y
    
    async def get_screen_info(self) -> Dict[str, Any]:
        """Get screen information.
        
        Returns:
            Dictionary with screen information
        """
        try:
            width, height = self._get_screen_size()
            
            # Get mouse position
            if PYAUTOGUI_AVAILABLE:
                mouse_x, mouse_y = pyautogui.position()
            else:
                mouse_x, mouse_y = 0, 0
            
            # Get monitor info if available
            monitors = []
            try:
                import screeninfo
                for monitor in screeninfo.get_monitors():
                    monitors.append({
                        'name': monitor.name,
                        'x': monitor.x,
                        'y': monitor.y,
                        'width': monitor.width,
                        'height': monitor.height,
                        'is_primary': monitor.is_primary
                    })
            except ImportError:
                log.debug("screeninfo not available, using single monitor info")
                monitors = [{
                    'name': 'Primary',
                    'x': 0,
                    'y': 0,
                    'width': width,
                    'height': height,
                    'is_primary': True
                }]
            
            return {
                'primary_size': {'width': width, 'height': height},
                'monitors': monitors,
                'mouse_position': {'x': mouse_x, 'y': mouse_y},
                'pyautogui_version': pyautogui.__version__ if PYAUTOGUI_AVAILABLE else 'Not available'
            }
            
        except Exception as e:
            log.error(f"Failed to get screen info: {e}", exception=e)
            raise AutomationException(f"Failed to get screen info: {str(e)}")
    
    async def move_mouse(self, x: int, y: int, duration: float = 0.0,
                        relative: bool = False) -> Dict[str, Any]:
        """Move mouse to specified position.
        
        Args:
            x: X coordinate (or delta if relative)
            y: Y coordinate (or delta if relative)
            duration: Movement duration in seconds
            relative: Move relative to current position
            
        Returns:
            Dictionary with operation result
        """
        self._check_availability()
        
        try:
            if relative:
                # Get current position for relative movement
                current_x, current_y = pyautogui.position()
                target_x = current_x + x
                target_y = current_y + y
            else:
                target_x, target_y = x, y
            
            # Validate coordinates
            target_x, target_y = self._validate_coordinates(target_x, target_y)
            
            # Move mouse
            await asyncio.get_event_loop().run_in_executor(
                None, pyautogui.moveTo, target_x, target_y, duration
            )
            
            # Get final position
            final_x, final_y = pyautogui.position()
            
            return {
                'action': 'move_mouse',
                'target': {'x': target_x, 'y': target_y},
                'final': {'x': final_x, 'y': final_y},
                'relative': relative,
                'duration': duration,
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to move mouse: {e}", exception=e)
            raise AutomationException(f"Failed to move mouse: {str(e)}")
    
    async def click_mouse(self, x: Optional[int] = None, y: Optional[int] = None,
                         button: str = 'left', clicks: int = 1,
                         interval: float = 0.0) -> Dict[str, Any]:
        """Click mouse at specified position.
        
        Args:
            x: X coordinate (None for current position)
            y: Y coordinate (None for current position)
            button: Mouse button ('left', 'right', 'middle')
            clicks: Number of clicks
            interval: Interval between clicks
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Validate button
            valid_buttons = ['left', 'right', 'middle']
            if button not in valid_buttons:
                raise ValidationException(f"Invalid mouse button: {button}")
            
            # Get position
            if x is not None and y is not None:
                x, y = self._validate_coordinates(x, y)
            else:
                x, y = pyautogui.position()
            
            # Perform click
            await asyncio.get_event_loop().run_in_executor(
                None, pyautogui.click, x, y, clicks, interval, button
            )
            
            return {
                'action': 'click_mouse',
                'position': {'x': x, 'y': y},
                'button': button,
                'clicks': clicks,
                'interval': interval,
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to click mouse: {e}", exception=e)
            raise AutomationException(f"Failed to click mouse: {str(e)}")
    
    async def double_click(self, x: Optional[int] = None, 
                          y: Optional[int] = None) -> Dict[str, Any]:
        """Double-click at specified position.
        
        Args:
            x: X coordinate (None for current position)
            y: Y coordinate (None for current position)
            
        Returns:
            Dictionary with operation result
        """
        return await self.click_mouse(x, y, button='left', clicks=2, interval=0.1)
    
    async def right_click(self, x: Optional[int] = None, 
                         y: Optional[int] = None) -> Dict[str, Any]:
        """Right-click at specified position.
        
        Args:
            x: X coordinate (None for current position)
            y: Y coordinate (None for current position)
            
        Returns:
            Dictionary with operation result
        """
        return await self.click_mouse(x, y, button='right', clicks=1)
    
    async def drag_mouse(self, start_x: int, start_y: int,
                        end_x: int, end_y: int,
                        duration: float = 0.5,
                        button: str = 'left') -> Dict[str, Any]:
        """Drag mouse from start to end position.
        
        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Drag duration in seconds
            button: Mouse button to hold
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Validate coordinates
            start_x, start_y = self._validate_coordinates(start_x, start_y)
            end_x, end_y = self._validate_coordinates(end_x, end_y)
            
            # Perform drag
            await asyncio.get_event_loop().run_in_executor(
                None, pyautogui.dragTo, end_x, end_y, duration, button=button
            )
            
            return {
                'action': 'drag_mouse',
                'start': {'x': start_x, 'y': start_y},
                'end': {'x': end_x, 'y': end_y},
                'duration': duration,
                'button': button,
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to drag mouse: {e}", exception=e)
            raise AutomationException(f"Failed to drag mouse: {str(e)}")
    
    async def scroll_mouse(self, clicks: int, x: Optional[int] = None,
                          y: Optional[int] = None) -> Dict[str, Any]:
        """Scroll mouse wheel.
        
        Args:
            clicks: Number of scroll clicks (positive=up, negative=down)
            x: X coordinate (None for current position)
            y: Y coordinate (None for current position)
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Move to position if specified
            if x is not None and y is not None:
                x, y = self._validate_coordinates(x, y)
                await self.move_mouse(x, y)
            else:
                x, y = pyautogui.position()
            
            # Perform scroll
            await asyncio.get_event_loop().run_in_executor(
                None, pyautogui.scroll, clicks
            )
            
            return {
                'action': 'scroll_mouse',
                'position': {'x': x, 'y': y},
                'clicks': clicks,
                'direction': 'up' if clicks > 0 else 'down',
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to scroll mouse: {e}", exception=e)
            raise AutomationException(f"Failed to scroll mouse: {str(e)}")
    
    async def type_text(self, text: str, interval: float = 0.0) -> Dict[str, Any]:
        """Type text using keyboard.
        
        Args:
            text: Text to type
            interval: Interval between keystrokes
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Security check for dangerous text
            if self.security:
                text = self.security.validate_input('command', text)
            
            # Type text
            await asyncio.get_event_loop().run_in_executor(
                None, pyautogui.typewrite, text, interval
            )
            
            return {
                'action': 'type_text',
                'text_length': len(text),
                'interval': interval,
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to type text: {e}", exception=e)
            raise AutomationException(f"Failed to type text: {str(e)}")
    
    async def press_key(self, key: Union[str, List[str]]) -> Dict[str, Any]:
        """Press a key or key combination.
        
        Args:
            key: Key name or list of keys for combination
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Handle key combinations
            if isinstance(key, list):
                # Press keys in sequence
                await asyncio.get_event_loop().run_in_executor(
                    None, pyautogui.hotkey, *key
                )
                key_str = '+'.join(key)
            else:
                # Press single key
                await asyncio.get_event_loop().run_in_executor(
                    None, pyautogui.press, key
                )
                key_str = key
            
            return {
                'action': 'press_key',
                'key': key_str,
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to press key: {e}", exception=e)
            raise AutomationException(f"Failed to press key: {str(e)}")
    
    async def hotkey(self, *keys) -> Dict[str, Any]:
        """Press a hotkey combination.
        
        Args:
            *keys: Keys to press together (e.g., 'ctrl', 'c')
            
        Returns:
            Dictionary with operation result
        """
        return await self.press_key(list(keys))
    
    async def take_screenshot(self, region: Optional[Tuple[int, int, int, int]] = None,
                            save_path: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot.
        
        Args:
            region: Region to capture (x, y, width, height) or None for full screen
            save_path: Path to save screenshot or None to return base64
            
        Returns:
            Dictionary with screenshot information
        """
        try:
            # Take screenshot
            if region:
                # Validate region
                x, y, width, height = region
                x, y = self._validate_coordinates(x, y)
                screen_width, screen_height = self._get_screen_size()
                width = min(width, screen_width - x)
                height = min(height, screen_height - y)
                
                screenshot = await asyncio.get_event_loop().run_in_executor(
                    None, pyautogui.screenshot, region=(x, y, width, height)
                )
            else:
                screenshot = await asyncio.get_event_loop().run_in_executor(
                    None, pyautogui.screenshot
                )
            
            result = {
                'action': 'take_screenshot',
                'size': {'width': screenshot.width, 'height': screenshot.height},
                'mode': screenshot.mode,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            if save_path:
                # Validate path
                if self.security:
                    save_path = self.security.validate_input('path', save_path)
                
                # Save to file
                screenshot.save(save_path)
                result['saved_to'] = save_path
                result['file_size'] = Path(save_path).stat().st_size
            else:
                # Convert to base64
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                buffer.seek(0)
                result['image_data'] = base64.b64encode(buffer.read()).decode('utf-8')
                result['format'] = 'base64_png'
            
            result['success'] = True
            return result
            
        except Exception as e:
            log.error(f"Failed to take screenshot: {e}", exception=e)
            raise AutomationException(f"Failed to take screenshot: {str(e)}")
    
    async def find_image_on_screen(self, image_path: str, 
                                 confidence: float = 0.8,
                                 grayscale: bool = False,
                                 region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """Find an image on the screen.
        
        Args:
            image_path: Path to image file to find
            confidence: Match confidence (0.0-1.0)
            grayscale: Convert to grayscale for matching
            region: Region to search in
            
        Returns:
            Dictionary with found positions
        """
        try:
            # Validate image path
            if self.security:
                image_path = self.security.validate_input('path', image_path)
            
            if not Path(image_path).exists():
                raise ValidationException(f"Image file not found: {image_path}")
            
            # Find image
            locations = await asyncio.get_event_loop().run_in_executor(
                None, pyautogui.locateAllOnScreen, image_path,
                confidence=confidence, grayscale=grayscale, region=region
            )
            
            # Convert generator to list
            found_locations = []
            for loc in locations:
                found_locations.append({
                    'x': loc.left,
                    'y': loc.top,
                    'width': loc.width,
                    'height': loc.height,
                    'center': {
                        'x': loc.left + loc.width // 2,
                        'y': loc.top + loc.height // 2
                    }
                })
            
            return {
                'action': 'find_image',
                'image_path': image_path,
                'found': len(found_locations) > 0,
                'count': len(found_locations),
                'locations': found_locations,
                'confidence': confidence,
                'grayscale': grayscale,
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to find image: {e}", exception=e)
            raise AutomationException(f"Failed to find image: {str(e)}")
    
    async def wait_for_image(self, image_path: str, timeout: float = 10.0,
                           confidence: float = 0.8,
                           interval: float = 0.5) -> Dict[str, Any]:
        """Wait for an image to appear on screen.
        
        Args:
            image_path: Path to image file to wait for
            timeout: Maximum wait time in seconds
            confidence: Match confidence
            interval: Check interval in seconds
            
        Returns:
            Dictionary with found position
        """
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                result = await self.find_image_on_screen(image_path, confidence)
                
                if result['found']:
                    return {
                        'action': 'wait_for_image',
                        'image_path': image_path,
                        'found': True,
                        'location': result['locations'][0],
                        'wait_time': time.time() - start_time,
                        'success': True
                    }
                
                await asyncio.sleep(interval)
            
            return {
                'action': 'wait_for_image',
                'image_path': image_path,
                'found': False,
                'timeout': timeout,
                'success': False
            }
            
        except Exception as e:
            log.error(f"Failed to wait for image: {e}", exception=e)
            raise AutomationException(f"Failed to wait for image: {str(e)}")
    
    async def click_image(self, image_path: str, confidence: float = 0.8,
                         button: str = 'left') -> Dict[str, Any]:
        """Find and click on an image.
        
        Args:
            image_path: Path to image file to click
            confidence: Match confidence
            button: Mouse button to use
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Find image
            result = await self.find_image_on_screen(image_path, confidence)
            
            if not result['found']:
                return {
                    'action': 'click_image',
                    'image_path': image_path,
                    'found': False,
                    'success': False
                }
            
            # Click on first found location's center
            location = result['locations'][0]
            center_x = location['center']['x']
            center_y = location['center']['y']
            
            click_result = await self.click_mouse(center_x, center_y, button=button)
            
            return {
                'action': 'click_image',
                'image_path': image_path,
                'found': True,
                'clicked_at': {'x': center_x, 'y': center_y},
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to click image: {e}", exception=e)
            raise AutomationException(f"Failed to click image: {str(e)}")
    
    async def get_pixel_color(self, x: int, y: int) -> Dict[str, Any]:
        """Get color of pixel at specified position.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Dictionary with pixel color information
        """
        try:
            # Validate coordinates
            x, y = self._validate_coordinates(x, y)
            
            # Get pixel color
            screenshot = await asyncio.get_event_loop().run_in_executor(
                None, pyautogui.screenshot, region=(x, y, 1, 1)
            )
            
            r, g, b = screenshot.getpixel((0, 0))
            
            return {
                'action': 'get_pixel_color',
                'position': {'x': x, 'y': y},
                'color': {
                    'rgb': (r, g, b),
                    'hex': f'#{r:02x}{g:02x}{b:02x}',
                    'r': r,
                    'g': g,
                    'b': b
                },
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to get pixel color: {e}", exception=e)
            raise AutomationException(f"Failed to get pixel color: {str(e)}")
    
    async def alert_box(self, text: str, title: str = 'Alert',
                       button: str = 'OK') -> Dict[str, Any]:
        """Show an alert box.
        
        Args:
            text: Alert message
            title: Alert title
            button: Button text
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Show alert
            result = await asyncio.get_event_loop().run_in_executor(
                None, pyautogui.alert, text, title, button
            )
            
            return {
                'action': 'alert_box',
                'text': text,
                'title': title,
                'button_clicked': result,
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to show alert: {e}", exception=e)
            raise AutomationException(f"Failed to show alert: {str(e)}")
    
    async def confirm_box(self, text: str, title: str = 'Confirm',
                         buttons: List[str] = None) -> Dict[str, Any]:
        """Show a confirmation box.
        
        Args:
            text: Confirmation message
            title: Box title
            buttons: List of button texts
            
        Returns:
            Dictionary with user response
        """
        try:
            if buttons is None:
                buttons = ['OK', 'Cancel']
            
            # Show confirm box
            result = await asyncio.get_event_loop().run_in_executor(
                None, pyautogui.confirm, text, title, buttons
            )
            
            return {
                'action': 'confirm_box',
                'text': text,
                'title': title,
                'buttons': buttons,
                'button_clicked': result,
                'confirmed': result == buttons[0],
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to show confirm box: {e}", exception=e)
            raise AutomationException(f"Failed to show confirm box: {str(e)}")
    
    async def prompt_box(self, text: str, title: str = 'Prompt',
                        default: str = '') -> Dict[str, Any]:
        """Show a prompt box for user input.
        
        Args:
            text: Prompt message
            title: Box title
            default: Default value
            
        Returns:
            Dictionary with user input
        """
        try:
            # Show prompt
            result = await asyncio.get_event_loop().run_in_executor(
                None, pyautogui.prompt, text, title, default
            )
            
            return {
                'action': 'prompt_box',
                'text': text,
                'title': title,
                'user_input': result,
                'cancelled': result is None,
                'success': True
            }
            
        except Exception as e:
            log.error(f"Failed to show prompt: {e}", exception=e)
            raise AutomationException(f"Failed to show prompt: {str(e)}")