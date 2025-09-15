import logging
import os
import sys
from typing import Optional

class GlobalLogger:
    """全局日志工具类，支持日志文件覆盖模式"""
    _instance = None
    _logger_name = "global_app_logger"

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            # 新增：支持通过参数控制是否覆盖日志（默认覆盖）
            cls._instance.overwrite_log = kwargs.get('overwrite_log', True)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        self.logger = logging.getLogger(self._logger_name)
        
        if self.logger.handlers:
            return
        
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # 日志格式
        fmt = "%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt=datefmt)

        # 控制台输出（带颜色）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self._get_colored_formatter())
        self.logger.addHandler(console_handler)

        # 文件输出（核心修改：支持覆盖模式）
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/app.log"
        
        # 根据 overwrite_log 决定模式：'w' 覆盖，'a' 追加
        file_mode = 'w' if self.overwrite_log else 'a'
        
        # 使用基础 FileHandler 而非 RotatingFileHandler（如果不需要轮转）
        file_handler = logging.FileHandler(
            log_file,
            mode=file_mode,  # 关键：设置写入模式
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def _get_colored_formatter(self) -> logging.Formatter:
        # 保持原有颜色格式化逻辑不变
        COLORS = {
            'DEBUG': '\033[0;36m',
            'INFO': '\033[0;32m',
            'WARNING': '\033[0;33m',
            'ERROR': '\033[0;31m',
            'CRITICAL': '\033[1;31m',
            'RESET': '\033[0m'
        }

        def colored_format(record):
            level_name = record.levelname
            color = COLORS.get(level_name, COLORS['RESET'])
            fmt = f"{color}%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s{COLORS['RESET']}"
            return logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S").format(record)

        class ColoredFormatter(logging.Formatter):
            def format(self, record):
                return colored_format(record)
        
        return ColoredFormatter()

    # 日志方法保持不变
    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str, exc_info: bool = False):
        self.logger.error(msg, exc_info=exc_info)

    def critical(self, msg: str, exc_info: bool = False):
        self.logger.critical(msg, exc_info=exc_info)

    def set_level(self, level: str):
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        self.logger.setLevel(level_map.get(level.upper(), logging.INFO))


# 默认创建覆盖模式的日志实例
logger = GlobalLogger(overwrite_log=True)

# 如果需要追加模式，可这样创建（但全局建议保持唯一实例）：
# logger = GlobalLogger(overwrite_log=False)
