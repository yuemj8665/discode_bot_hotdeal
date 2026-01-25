# -*- coding: utf-8 -*-
"""
유틸리티 함수
"""
from datetime import datetime
from typing import Any, Dict


def format_datetime(dt: datetime) -> str:
    """
    datetime을 읽기 쉬운 형식으로 변환
    
    Args:
        dt: datetime 객체
        
    Returns:
        str: "YYYY-MM-DD HH:MM" 형식의 문자열
    """
    return dt.strftime("%Y-%m-%d %H:%M")


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    텍스트를 지정된 길이로 자르기
    
    Args:
        text: 원본 텍스트
        max_length: 최대 길이
        
    Returns:
        str: 잘린 텍스트
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def create_hotdeal_embed(hotdeal: Dict[str, Any]) -> Dict[str, Any]:
    """
    핫딜 정보를 Discord Embed 형식으로 변환
    
    Args:
        hotdeal: 핫딜 딕셔너리
        
    Returns:
        Dict[str, Any]: Embed 형식의 딕셔너리
    """
    return {
        "title": hotdeal.get("title", "제목 없음"),
        "description": f"가격: {hotdeal.get('price', 'N/A')}",
        "url": hotdeal.get("url", ""),
        "color": 0xFF0000,  # 빨간색
        "footer": {
            "text": f"출처: {hotdeal.get('source', 'N/A')}"
        }
    }
