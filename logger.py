#!/usr/bin/env python3
"""
PaperTracer 日志管理
提供统一的日志记录功能
"""

import logging
import os
from datetime import datetime
from papertracer_config import Config

class LogManager:
    """日志管理器"""
    
    def __init__(self, name="papertracer", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 文件处理器
        Config.ensure_output_directory()
        log_filename = Config.get_timestamped_filename(
            prefix="papertracer", 
            suffix="log", 
            extension="log"
        )
        log_path = Config.get_output_path(log_filename)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 格式化器
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        self.logger.info(f"日志文件: {log_path}")
    
    def info(self, message):
        """记录信息日志"""
        self.logger.info(message)
    
    def debug(self, message):
        """记录调试日志"""
        self.logger.debug(message)
    
    def warning(self, message):
        """记录警告日志"""
        self.logger.warning(message)
    
    def error(self, message):
        """记录错误日志"""
        self.logger.error(message)
    
    def critical(self, message):
        """记录严重错误日志"""
        self.logger.critical(message)

# 全局日志实例
logger = LogManager()

def get_logger():
    """获取全局日志实例"""
    return logger
