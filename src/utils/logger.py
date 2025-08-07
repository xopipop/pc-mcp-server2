"""
Модуль логирования для Excel MCP Server
"""

import sys
import os
from pathlib import Path
from loguru import logger
from typing import Optional


def setup_logger(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days"
) -> None:
    """
    Настройка логирования для Excel MCP Server
    
    Args:
        level: Уровень логирования
        log_file: Путь к файлу логов
        rotation: Ротация логов
        retention: Время хранения логов
    """
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Добавляем обработчик для консоли
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )
    
    # Добавляем обработчик для файла
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip"
        )
    
    # Добавляем обработчик для системного журнала Windows
    try:
        logger.add(
            "excel_mcp_{time}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip"
        )
    except Exception as e:
        logger.warning(f"Не удалось настроить системный журнал: {e}")


def get_logger(name: str = __name__):
    """
    Получить логгер с указанным именем
    
    Args:
        name: Имя логгера
        
    Returns:
        Logger instance
    """
    return logger.bind(name=name) 