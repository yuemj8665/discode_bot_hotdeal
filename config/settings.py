# -*- coding: utf-8 -*-
"""
환경 변수 및 설정 관리
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 경로 설정
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    """애플리케이션 설정 클래스"""
    
    # Discord 봇 토큰
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
    
    # Discord 봇 설정
    COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')
    
    # 데이터베이스 설정 (PostgreSQL)
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://root:root@localhost:5432/studydb')
    
    # 크롤링 설정
    CRAWL_INTERVAL = int(os.getenv('CRAWL_INTERVAL', '3600'))  # 기본 1시간 (초 단위)
    
    # 로깅 설정
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'hotdeal_bot.log')

    # AI 분석 설정 (선택사항 — 없으면 AI 분석 기능 비활성화)
    # GEMINI_API_KEY_1,2,3 중 하나라도 있으면 활성화. 없으면 단일 GEMINI_API_KEY 폴백
    GEMINI_API_KEYS = [
        key for key in [
            os.getenv('GEMINI_API_KEY_1', ''),
            os.getenv('GEMINI_API_KEY_2', ''),
            os.getenv('GEMINI_API_KEY_3', ''),
        ] if key
    ] or ([os.getenv('GEMINI_API_KEY', '')] if os.getenv('GEMINI_API_KEY') else [])
    AI_ANALYSIS_DELAY_HOURS = int(os.getenv('AI_ANALYSIS_DELAY_HOURS', '3'))
