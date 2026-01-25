# -*- coding: utf-8 -*-
"""
데이터베이스 모델
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Hotdeal:
    """핫딜 데이터 모델"""
    id: Optional[int] = None
    title: str = ""
    price: str = ""
    url: str = ""
    source: str = ""
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "title": self.title,
            "price": self.price,
            "url": self.url,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Hotdeal':
        """딕셔너리에서 생성"""
        return cls(
            id=data.get("id"),
            title=data.get("title", ""),
            price=data.get("price", ""),
            url=data.get("url", ""),
            source=data.get("source", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


@dataclass
class User:
    """사용자 데이터 모델"""
    user_id: int
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """딕셔너리에서 생성"""
        return cls(
            user_id=data.get("user_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


@dataclass
class Keyword:
    """키워드 데이터 모델"""
    id: Optional[int] = None
    user_id: int = 0
    keyword: str = ""
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "keyword": self.keyword,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Keyword':
        """딕셔너리에서 생성"""
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", 0),
            keyword=data.get("keyword", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )
