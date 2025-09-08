"""
구조화된 로깅 모듈
로컬 개발과 AWS 환경 모두 지원
"""
import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
from .config import get_config, Environment


# 요청 컨텍스트 변수들
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class StructuredFormatter(logging.Formatter):
    """구조화된 JSON 로그 포맷터"""
    
    def format(self, record: logging.LogRecord) -> str:
        config = get_config()
        
        # 기본 로그 엔트리
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'service': config.service_name,
            'version': config.service_version,
            'environment': config.environment.value,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 컨텍스트 정보 추가
        if correlation_id_var.get():
            log_entry['correlation_id'] = correlation_id_var.get()
        if user_id_var.get():
            log_entry['user_id'] = user_id_var.get()
        if request_id_var.get():
            log_entry['request_id'] = request_id_var.get()
        
        # 추가 필드들 (record에 있는 커스텀 속성들)
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        # 예외 정보 추가
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class SimpleFormatter(logging.Formatter):
    """로컬 개발용 간단한 포맷터"""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        correlation_id = correlation_id_var.get()
        correlation_part = f" [{correlation_id}]" if correlation_id else ""
        
        return f"{timestamp} {record.levelname:8} {record.name:20} {record.getMessage()}{correlation_part}"


class StructuredLogger:
    """구조화된 로거 클래스"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """로거 설정"""
        config = get_config()
        
        # 로그 레벨 설정
        level = getattr(logging, config.log_level.upper(), logging.INFO)
        self.logger.setLevel(level)
        
        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 핸들러 생성
        handler = logging.StreamHandler(sys.stdout)
        
        # 포맷터 설정
        if config.environment == Environment.LOCAL and config.log_format != "json":
            formatter = SimpleFormatter()
        else:
            formatter = StructuredFormatter()
        
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # 중복 로그 방지
        self.logger.propagate = False
    
    def debug(self, message: str, **kwargs):
        """디버그 로그"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """정보 로그"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """경고 로그"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, error: Exception = None, **kwargs):
        """에러 로그"""
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)
            self.logger.error(message, exc_info=error, extra=kwargs)
        else:
            self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, error: Exception = None, **kwargs):
        """치명적 에러 로그"""
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)
            self.logger.critical(message, exc_info=error, extra=kwargs)
        else:
            self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """내부 로그 메서드"""
        self.logger.log(level, message, extra=kwargs)


# 로거 팩토리
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str = None) -> StructuredLogger:
    """로거 인스턴스 반환"""
    if name is None:
        # 호출자의 모듈명 사용
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    
    return _loggers[name]


# 컨텍스트 관리 함수들
def set_correlation_id(correlation_id: str):
    """상관관계 ID 설정"""
    correlation_id_var.set(correlation_id)


def set_user_id(user_id: str):
    """사용자 ID 설정"""
    user_id_var.set(user_id)


def set_request_id(request_id: str):
    """요청 ID 설정"""
    request_id_var.set(request_id)


def get_correlation_id() -> Optional[str]:
    """상관관계 ID 반환"""
    return correlation_id_var.get()


def clear_context():
    """컨텍스트 초기화"""
    correlation_id_var.set(None)
    user_id_var.set(None)
    request_id_var.set(None)


# 로깅 데코레이터
def log_function_call(logger: StructuredLogger = None):
    """함수 호출을 로깅하는 데코레이터"""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            
            function_name = f"{func.__module__}.{func.__name__}"
            
            logger.debug(
                f"Function call started: {function_name}",
                function=function_name,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys())
            )
            
            try:
                result = func(*args, **kwargs)
                logger.debug(
                    f"Function call completed: {function_name}",
                    function=function_name,
                    success=True
                )
                return result
            except Exception as e:
                logger.error(
                    f"Function call failed: {function_name}",
                    error=e,
                    function=function_name,
                    success=False
                )
                raise
        
        return wrapper
    return decorator