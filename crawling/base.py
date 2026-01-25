# -*- coding: utf-8 -*-
"""
기본 크롤러 클래스
"""
from abc import ABC, abstractmethod
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """크롤러 기본 클래스"""
    
    def __init__(self, name: str):
        """
        Args:
            name: 크롤러 이름
        """
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    async def fetch(self) -> List[Dict[str, Any]]:
        """
        데이터를 가져오는 추상 메서드
        
        Returns:
            List[Dict[str, Any]]: 크롤링된 데이터 리스트
        """
        pass
    
    @abstractmethod
    def parse(self, data: Any) -> List[Dict[str, Any]]:
        """
        데이터를 파싱하는 추상 메서드
        
        Args:
            data: 파싱할 원본 데이터
            
        Returns:
            List[Dict[str, Any]]: 파싱된 데이터 리스트
        """
        pass
    
    async def crawl(self) -> List[Dict[str, Any]]:
        """
        크롤링 실행 메서드
        
        Returns:
            List[Dict[str, Any]]: 크롤링된 데이터 리스트
        """
        try:
            self.logger.info(f"{self.name} 크롤링 시작")
            data = await self.fetch()
            parsed_data = self.parse(data)
            self.logger.info(f"{self.name} 크롤링 완료: {len(parsed_data)}개 항목")
            return parsed_data
        except Exception as e:
            self.logger.error(f"{self.name} 크롤링 오류: {e}", exc_info=True)
            return []
