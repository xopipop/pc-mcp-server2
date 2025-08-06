"""
Excel MCP Server - Полнофункциональный MCP сервер для управления Microsoft Excel
"""

__version__ = "1.0.0"
__author__ = "Excel MCP Team"
__description__ = "MCP Server for Microsoft Excel automation"

from .server import ExcelMCPServer
from .excel_controller import ExcelController

__all__ = ["ExcelMCPServer", "ExcelController"] 