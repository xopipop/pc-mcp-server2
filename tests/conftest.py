"""Pytest configuration file."""

import sys
import unittest.mock

# Mock modules that require tkinter
sys.modules['tkinter'] = unittest.mock.MagicMock()
sys.modules['mouseinfo'] = unittest.mock.MagicMock()
sys.modules['pyautogui'] = unittest.mock.MagicMock()
sys.modules['pygetwindow'] = unittest.mock.MagicMock()
sys.modules['pyscreeze'] = unittest.mock.MagicMock()
sys.modules['pymsgbox'] = unittest.mock.MagicMock()