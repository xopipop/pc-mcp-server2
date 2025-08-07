"""
Модуль кэширования для Excel MCP Server
"""

import time
import threading
from typing import Any, Dict, Optional, Union
from collections import OrderedDict
from .logger import get_logger

logger = get_logger(__name__)


class Cache:
    """
    Кэш для хранения COM объектов и результатов операций
    """
    
    def __init__(self, max_size: int = 100, ttl: int = 300):
        """
        Инициализация кэша
        
        Args:
            max_size: Максимальное количество элементов
            ttl: Время жизни элементов в секундах
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.RLock()
        
    def get(self, key: str) -> Optional[Any]:
        """
        Получить значение из кэша
        
        Args:
            key: Ключ
            
        Returns:
            Значение или None если не найдено или истекло время
        """
        with self._lock:
            if key not in self._cache:
                return None
                
            item = self._cache[key]
            if time.time() - item['timestamp'] > self.ttl:
                del self._cache[key]
                logger.debug(f"Элемент кэша {key} истек и удален")
                return None
                
            # Перемещаем в конец (LRU)
            self._cache.move_to_end(key)
            return item['value']
    
    def set(self, key: str, value: Any) -> None:
        """
        Установить значение в кэш
        
        Args:
            key: Ключ
            value: Значение
        """
        with self._lock:
            # Удаляем старый элемент если он существует
            if key in self._cache:
                del self._cache[key]
            
            # Проверяем размер кэша
            if len(self._cache) >= self.max_size:
                # Удаляем самый старый элемент
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"Удален старый элемент кэша: {oldest_key}")
            
            # Добавляем новый элемент
            self._cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
            logger.debug(f"Добавлен элемент в кэш: {key}")
    
    def delete(self, key: str) -> bool:
        """
        Удалить элемент из кэша
        
        Args:
            key: Ключ
            
        Returns:
            True если элемент был удален, False если не найден
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Удален элемент кэша: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """Очистить весь кэш"""
        with self._lock:
            self._cache.clear()
            logger.info("Кэш очищен")
    
    def size(self) -> int:
        """Получить размер кэша"""
        with self._lock:
            return len(self._cache)
    
    def cleanup(self) -> int:
        """
        Очистить истекшие элементы
        
        Returns:
            Количество удаленных элементов
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, item in self._cache.items()
                if current_time - item['timestamp'] > self.ttl
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Удалено {len(expired_keys)} истекших элементов кэша")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику кэша
        
        Returns:
            Словарь со статистикой
        """
        with self._lock:
            current_time = time.time()
            expired_count = sum(
                1 for item in self._cache.values()
                if current_time - item['timestamp'] > self.ttl
            )
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'ttl': self.ttl,
                'expired_count': expired_count,
                'utilization': len(self._cache) / self.max_size if self.max_size > 0 else 0
            }


# Глобальный экземпляр кэша
excel_cache = Cache()


class ExcelObjectCache:
    """
    Специализированный кэш для Excel COM объектов
    """
    
    def __init__(self):
        self.workbooks_cache = Cache(max_size=10, ttl=600)  # 10 минут для рабочих книг
        self.worksheets_cache = Cache(max_size=50, ttl=300)  # 5 минут для листов
        self.range_cache = Cache(max_size=200, ttl=60)  # 1 минута для диапазонов
        
    def get_workbook_key(self, file_path: str) -> str:
        """Генерирует ключ для рабочей книги"""
        return f"workbook:{file_path.lower()}"
    
    def get_worksheet_key(self, file_path: str, sheet_name: str) -> str:
        """Генерирует ключ для листа"""
        return f"worksheet:{file_path.lower()}:{sheet_name.lower()}"
    
    def get_range_key(self, file_path: str, sheet_name: str, range_address: str) -> str:
        """Генерирует ключ для диапазона"""
        return f"range:{file_path.lower()}:{sheet_name.lower()}:{range_address.lower()}"
    
    def cache_workbook(self, file_path: str, workbook) -> None:
        """Кэшировать рабочую книгу"""
        key = self.get_workbook_key(file_path)
        self.workbooks_cache.set(key, workbook)
    
    def get_cached_workbook(self, file_path: str):
        """Получить кэшированную рабочую книгу"""
        key = self.get_workbook_key(file_path)
        return self.workbooks_cache.get(key)
    
    def cache_worksheet(self, file_path: str, sheet_name: str, worksheet) -> None:
        """Кэшировать лист"""
        key = self.get_worksheet_key(file_path, sheet_name)
        self.worksheets_cache.set(key, worksheet)
    
    def get_cached_worksheet(self, file_path: str, sheet_name: str):
        """Получить кэшированный лист"""
        key = self.get_worksheet_key(file_path, sheet_name)
        return self.worksheets_cache.get(key)
    
    def cache_range(self, file_path: str, sheet_name: str, range_address: str, range_data) -> None:
        """Кэшировать данные диапазона"""
        key = self.get_range_key(file_path, sheet_name, range_address)
        self.range_cache.set(key, range_data)
    
    def get_cached_range(self, file_path: str, sheet_name: str, range_address: str):
        """Получить кэшированные данные диапазона"""
        key = self.get_range_key(file_path, sheet_name, range_address)
        return self.range_cache.get(key)
    
    def clear_workbook_cache(self, file_path: str) -> None:
        """Очистить кэш для конкретной рабочей книги"""
        workbook_key = self.get_workbook_key(file_path)
        self.workbooks_cache.delete(workbook_key)
        
        # Очищаем связанные листы и диапазоны
        keys_to_delete = []
        for key in self.worksheets_cache._cache:
            if file_path.lower() in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            self.worksheets_cache.delete(key)
        
        keys_to_delete = []
        for key in self.range_cache._cache:
            if file_path.lower() in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            self.range_cache.delete(key)
        
        logger.info(f"Очищен кэш для рабочей книги: {file_path}")


# Глобальный экземпляр кэша Excel объектов
excel_object_cache = ExcelObjectCache() 