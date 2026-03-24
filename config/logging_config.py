# -*- coding: utf-8 -*-
"""
로깅 설정 모듈
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from .settings import Settings


def setup_logging():
    """
    로깅 설정 초기화
    - 매일 00시에 로그 파일을 백업
    - 백업된 로그는 7일 동안만 보관 후 자동 삭제
    
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    # 로그 디렉토리 생성
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # 로그 파일 경로
    log_file = log_dir / Settings.LOG_FILE
    
    # 로그 레벨 설정
    log_level = getattr(logging, Settings.LOG_LEVEL.upper(), logging.INFO)
    
    # 로깅 포맷 설정
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 포맷터 생성
    formatter = logging.Formatter(log_format, date_format)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # 파일 핸들러 (매일 자정에 회전, 7일 보관)
    # when='midnight': 매일 자정에 로그 회전
    # interval=1: 1일마다
    # backupCount=7: 최대 7개의 백업 파일 보관 (7일)
    # encoding='utf-8': UTF-8 인코딩
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(log_file),
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8',
        delay=False
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()  # 기존 핸들러 제거
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # SDK 내부 재시도 로그 활성화 (Gemini 실제 호출 횟수 추적용)
    logging.getLogger('google_genai').setLevel(logging.DEBUG)
    logging.getLogger('tenacity').setLevel(logging.DEBUG)
    
    # 로거 생성
    logger = logging.getLogger(__name__)
    logger.info(f"로깅 설정 완료 - 레벨: {Settings.LOG_LEVEL}, 파일: {log_file}")
    logger.info(f"로그 백업 설정: 매일 00시 자동 백업, 7일간 보관 후 자동 삭제")
    
    return logger
