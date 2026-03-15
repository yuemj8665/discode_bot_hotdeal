# -*- coding: utf-8 -*-
"""
데이터베이스 연결 및 작업 (비동기)
"""
import asyncpg
import logging
from typing import List, Optional
from datetime import datetime
from urllib.parse import urlparse
from .models import Hotdeal, User, Keyword, Category
from config.settings import Settings

logger = logging.getLogger(__name__)


class Database:
    """데이터베이스 클래스 (비동기)"""
    
    def __init__(self, db_url: str = None):
        """
        Args:
            db_url: PostgreSQL 데이터베이스 URL (기본값: Settings.DATABASE_URL)
        """
        self.db_url = db_url or Settings.DATABASE_URL
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """데이터베이스 연결 풀 생성"""
        if self._pool is None:
            try:
                # URL 파싱
                parsed = urlparse(self.db_url)
                self._pool = await asyncpg.create_pool(
                    host=parsed.hostname,
                    port=parsed.port or 5432,
                    user=parsed.username,
                    password=parsed.password,
                    database=parsed.path.lstrip('/'),
                    min_size=1,
                    max_size=10
                )
                await self._init_db()
            except Exception as e:
                logger.error(f"데이터베이스 연결 오류: {e}", exc_info=True)
                raise
    
    async def close(self):
        """데이터베이스 연결 풀 종료"""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def _init_db(self):
        """데이터베이스 초기화 (테이블 생성)"""
        try:
            async with self._pool.acquire() as conn:
                # users 테이블 생성
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # keywords 테이블 생성
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS keywords (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        keyword TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                        UNIQUE(user_id, keyword)
                    )
                ''')
                
                # 키워드 인덱스 생성
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_keywords_user_id ON keywords(user_id)
                ''')
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword)
                ''')
                
                # hotdeals 테이블 생성
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS hotdeals (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        price TEXT,
                        url TEXT UNIQUE NOT NULL,
                        source TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # URL에 대한 인덱스 생성 (중복 체크용)
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_url ON hotdeals(url)
                ''')
                
                # crawl_state 테이블 생성 (크롤러별 마지막 게시글 정보 저장)
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS crawl_state (
                        crawler_name TEXT PRIMARY KEY,
                        last_post_id TEXT,
                        last_post_url TEXT,
                        last_post_datetime TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 기존 테이블에 컬럼 추가 (마이그레이션)
                try:
                    await conn.execute('''
                        ALTER TABLE crawl_state 
                        ADD COLUMN IF NOT EXISTS last_post_url TEXT
                    ''')
                except Exception as e:
                    logger.debug(f"crawl_state 테이블 마이그레이션 (last_post_url): {e}")
                
                try:
                    await conn.execute('''
                        ALTER TABLE crawl_state 
                        ADD COLUMN IF NOT EXISTS last_post_datetime TIMESTAMP
                    ''')
                except Exception as e:
                    logger.debug(f"crawl_state 테이블 마이그레이션 (last_post_datetime): {e}")
                
                # user_categories 테이블 생성 (카테고리 구독 저장)
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS user_categories (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        category TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                        UNIQUE(user_id, category)
                    )
                ''')

                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_user_categories_user_id ON user_categories(user_id)
                ''')
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_user_categories_category ON user_categories(category)
                ''')

                # notification_channels 테이블 생성 (알림 채널 저장)
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS notification_channels (
                        guild_id BIGINT PRIMARY KEY,
                        channel_id BIGINT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                logger.info("데이터베이스 초기화 완료")
        except Exception as e:
            logger.error(f"데이터베이스 초기화 오류: {e}", exc_info=True)
            raise
    
    # ==================== 핫딜 관련 메서드 ====================
    
    async def add_hotdeal(self, hotdeal: Hotdeal) -> bool:
        """
        핫딜 추가
        
        Args:
            hotdeal: 핫딜 객체
            
        Returns:
            bool: 성공 여부
        """
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    INSERT INTO hotdeals (title, price, url, source, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (url) DO NOTHING
                ''', hotdeal.title, hotdeal.price, hotdeal.url, hotdeal.source, hotdeal.created_at or datetime.now())
                
                inserted = result == "INSERT 0 1"
                return inserted
        except Exception as e:
            logger.error(f"핫딜 추가 오류: {e}", exc_info=True)
            return False
    
    async def get_hotdeals(self, limit: int = 10) -> List[Hotdeal]:
        """
        핫딜 목록 조회
        
        Args:
            limit: 조회할 개수
            
        Returns:
            List[Hotdeal]: 핫딜 리스트
        """
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM hotdeals
                    ORDER BY created_at DESC
                    LIMIT $1
                ''', limit)
                
                hotdeals = []
                for row in rows:
                    hotdeal = Hotdeal(
                        id=row['id'],
                        title=row['title'],
                        price=row['price'],
                        url=row['url'],
                        source=row['source'],
                        created_at=row['created_at']
                    )
                    hotdeals.append(hotdeal)
                
                return hotdeals
        except Exception as e:
            logger.error(f"핫딜 조회 오류: {e}", exc_info=True)
            return []
    
    async def get_latest_post_id_from_hotdeals(self) -> Optional[str]:
        """
        hotdeals 테이블에서 가장 최신 게시글의 ID를 URL에서 추출
        
        Returns:
            Optional[str]: 가장 최신 게시글 ID 또는 None
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT url FROM hotdeals
                    ORDER BY created_at DESC
                    LIMIT 1
                ''')
                
                if row and row['url']:
                    # URL에서 게시글 ID 추출 (예: /b/hotdeal/160432774?p=1)
                    import re
                    match = re.search(r'/b/hotdeal/(\d+)', row['url'])
                    if match:
                        return match.group(1)
                return None
        except Exception as e:
            logger.error(f"최신 게시글 ID 조회 오류: {e}", exc_info=True)
            return None
    
    async def cleanup_old_hotdeals(self, hours: int = 24) -> int:
        """
        24시간이 지난 핫딜 삭제
        
        Args:
            hours: 삭제할 기준 시간 (기본값: 24시간)
            
        Returns:
            int: 삭제된 레코드 수
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM hotdeals
                    WHERE created_at < $1
                ''', cutoff_time)
                
                # DELETE 결과에서 삭제된 행 수 추출
                deleted_count = int(result.split()[-1]) if result.startswith("DELETE") else 0
                return deleted_count
        except Exception as e:
            logger.error(f"오래된 핫딜 삭제 오류: {e}", exc_info=True)
            return 0
    
    async def get_hotdeal_by_url(self, url: str) -> Optional[Hotdeal]:
        """
        URL로 핫딜 조회
        
        Args:
            url: 핫딜 URL
            
        Returns:
            Optional[Hotdeal]: 핫딜 객체 또는 None
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM hotdeals
                    WHERE url = $1
                ''', url)
                
                if row:
                    return Hotdeal(
                        id=row['id'],
                        title=row['title'],
                        price=row['price'],
                        url=row['url'],
                        source=row['source'],
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error(f"핫딜 조회 오류: {e}", exc_info=True)
            return None
    
    # ==================== 사용자 관련 메서드 ====================
    
    async def add_user(self, user_id: int) -> bool:
        """
        사용자 추가
        
        Args:
            user_id: Discord 사용자 ID
            
        Returns:
            bool: 성공 여부 (이미 존재하면 False)
        """
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    INSERT INTO users (user_id)
                    VALUES ($1)
                    ON CONFLICT (user_id) DO NOTHING
                ''', user_id)
                
                inserted = result == "INSERT 0 1"
                return inserted
        except Exception as e:
            logger.error(f"사용자 추가 오류: {e}", exc_info=True)
            return False
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """
        사용자 조회
        
        Args:
            user_id: Discord 사용자 ID
            
        Returns:
            Optional[User]: 사용자 객체 또는 None
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM users
                    WHERE user_id = $1
                ''', user_id)
                
                if row:
                    return User(
                        user_id=row['user_id'],
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error(f"사용자 조회 오류: {e}", exc_info=True)
            return None
    
    async def delete_user(self, user_id: int) -> bool:
        """
        사용자 삭제 (CASCADE로 키워드도 함께 삭제됨)
        
        Args:
            user_id: Discord 사용자 ID
            
        Returns:
            bool: 성공 여부
        """
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM users
                    WHERE user_id = $1
                ''', user_id)
                
                deleted = result == "DELETE 1"
                return deleted
        except Exception as e:
            logger.error(f"사용자 삭제 오류: {e}", exc_info=True)
            return False
    
    # ==================== 키워드 관련 메서드 ====================
    
    async def add_keyword(self, user_id: int, keyword: str) -> bool:
        """
        키워드 추가
        
        Args:
            user_id: Discord 사용자 ID
            keyword: 추가할 키워드
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 사용자가 없으면 먼저 추가
            await self.add_user(user_id)
            
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    INSERT INTO keywords (user_id, keyword)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id, keyword) DO NOTHING
                ''', user_id, keyword.strip())
                
                inserted = result == "INSERT 0 1"
                return inserted
        except Exception as e:
            logger.error(f"키워드 추가 오류: {e}", exc_info=True)
            return False
    
    async def get_keywords(self, user_id: int) -> List[Keyword]:
        """
        사용자의 키워드 목록 조회
        
        Args:
            user_id: Discord 사용자 ID
            
        Returns:
            List[Keyword]: 키워드 리스트
        """
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM keywords
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                ''', user_id)
                
                keywords = []
                for row in rows:
                    keyword = Keyword(
                        id=row['id'],
                        user_id=row['user_id'],
                        keyword=row['keyword'],
                        created_at=row['created_at']
                    )
                    keywords.append(keyword)
                
                return keywords
        except Exception as e:
            logger.error(f"키워드 조회 오류: {e}", exc_info=True)
            return []
    
    async def delete_keyword(self, user_id: int, keyword: str) -> bool:
        """
        키워드 삭제
        
        Args:
            user_id: Discord 사용자 ID
            keyword: 삭제할 키워드
            
        Returns:
            bool: 성공 여부
        """
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM keywords
                    WHERE user_id = $1 AND keyword = $2
                ''', user_id, keyword.strip())
                
                deleted = result == "DELETE 1"
                return deleted
        except Exception as e:
            logger.error(f"키워드 삭제 오류: {e}", exc_info=True)
            return False
    
    async def delete_all_keywords(self, user_id: int) -> int:
        """
        사용자의 모든 키워드 삭제
        
        Args:
            user_id: Discord 사용자 ID
            
        Returns:
            int: 삭제된 키워드 개수
        """
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM keywords
                    WHERE user_id = $1
                ''', user_id)
                
                # DELETE 결과에서 삭제된 행 수 추출
                deleted_count = int(result.split()[-1]) if result.startswith("DELETE") else 0
                return deleted_count
        except Exception as e:
            logger.error(f"키워드 전체 삭제 오류: {e}", exc_info=True)
            return 0
    
    async def get_users_by_keyword(self, keyword: str) -> List[int]:
        """
        특정 키워드를 가진 사용자 ID 목록 조회
        
        Args:
            keyword: 검색할 키워드
            
        Returns:
            List[int]: 사용자 ID 리스트
        """
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT DISTINCT user_id FROM keywords
                    WHERE keyword = $1
                ''', keyword.strip())
                
                return [row['user_id'] for row in rows]
        except Exception as e:
            logger.error(f"키워드로 사용자 조회 오류: {e}", exc_info=True)
            return []
    
    # ==================== 크롤 상태 관리 메서드 ====================
    
    async def get_last_post_id(self, crawler_name: str) -> Optional[str]:
        """
        크롤러의 마지막 게시글 ID 조회
        
        Args:
            crawler_name: 크롤러 이름
            
        Returns:
            Optional[str]: 마지막 게시글 ID 또는 None
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT last_post_id FROM crawl_state
                    WHERE crawler_name = $1
                ''', crawler_name)
                
                return row['last_post_id'] if row else None
        except Exception as e:
            logger.error(f"마지막 게시글 ID 조회 오류: {e}", exc_info=True)
            return None
    
    async def get_last_post_url(self, crawler_name: str) -> Optional[str]:
        """
        크롤러의 마지막 게시글 URL 조회
        
        Args:
            crawler_name: 크롤러 이름
            
        Returns:
            Optional[str]: 마지막 게시글 URL 또는 None
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT last_post_url FROM crawl_state
                    WHERE crawler_name = $1
                ''', crawler_name)
                
                return row['last_post_url'] if row else None
        except Exception as e:
            logger.error(f"마지막 게시글 URL 조회 오류: {e}", exc_info=True)
            return None
    
    async def get_last_post_datetime(self, crawler_name: str) -> Optional[datetime]:
        """
        크롤러의 마지막 게시글 작성 시간 조회
        
        Args:
            crawler_name: 크롤러 이름
            
        Returns:
            Optional[datetime]: 마지막 게시글 작성 시간 (timezone-naive) 또는 None
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT last_post_datetime FROM crawl_state
                    WHERE crawler_name = $1
                ''', crawler_name)
                
                if row and row['last_post_datetime']:
                    dt = row['last_post_datetime']
                    # timezone-aware면 timezone-naive로 변환
                    if isinstance(dt, datetime) and dt.tzinfo is not None:
                        return dt.replace(tzinfo=None)
                    return dt
                return None
        except Exception as e:
            logger.error(f"마지막 게시글 작성 시간 조회 오류: {e}", exc_info=True)
            return None
    
    async def update_last_post_id(self, crawler_name: str, post_id: str, post_url: str = None, post_datetime: datetime = None) -> bool:
        """
        크롤러의 마지막 게시글 정보 업데이트
        
        Args:
            crawler_name: 크롤러 이름
            post_id: 게시글 ID
            post_url: 게시글 URL (선택사항)
            post_datetime: 게시글 작성 시간 (선택사항, timezone-naive)
            
        Returns:
            bool: 성공 여부
        """
        try:
            async with self._pool.acquire() as conn:
                # datetime이 timezone-aware면 timezone-naive로 변환
                datetime_to_save = None
                if post_datetime:
                    if post_datetime.tzinfo is not None:
                        datetime_to_save = post_datetime.replace(tzinfo=None)
                    else:
                        datetime_to_save = post_datetime
                
                if post_url and datetime_to_save:
                    await conn.execute('''
                        INSERT INTO crawl_state (crawler_name, last_post_id, last_post_url, last_post_datetime, updated_at)
                        VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                        ON CONFLICT (crawler_name) 
                        DO UPDATE SET last_post_id = $2, last_post_url = $3, last_post_datetime = $4, updated_at = CURRENT_TIMESTAMP
                    ''', crawler_name, post_id, post_url, datetime_to_save)
                elif post_url:
                    await conn.execute('''
                        INSERT INTO crawl_state (crawler_name, last_post_id, last_post_url, updated_at)
                        VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                        ON CONFLICT (crawler_name) 
                        DO UPDATE SET last_post_id = $2, last_post_url = $3, updated_at = CURRENT_TIMESTAMP
                    ''', crawler_name, post_id, post_url)
                else:
                    await conn.execute('''
                        INSERT INTO crawl_state (crawler_name, last_post_id, updated_at)
                        VALUES ($1, $2, CURRENT_TIMESTAMP)
                        ON CONFLICT (crawler_name) 
                        DO UPDATE SET last_post_id = $2, updated_at = CURRENT_TIMESTAMP
                    ''', crawler_name, post_id)
                
                return True
        except Exception as e:
            logger.error(f"마지막 게시글 정보 업데이트 오류: {e}", exc_info=True)
            return False
    
    async def get_all_keywords(self) -> List[str]:
        """
        모든 키워드 목록 조회 (중복 제거)
        
        Returns:
            List[str]: 키워드 리스트
        """
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT DISTINCT keyword FROM keywords
                    ORDER BY keyword
                ''')
                
                return [row['keyword'] for row in rows]
        except Exception as e:
            logger.error(f"모든 키워드 조회 오류: {e}", exc_info=True)
            return []
    
    # ==================== 카테고리 관련 메서드 ====================

    async def add_category(self, user_id: int, category: str) -> bool:
        """
        카테고리 구독 추가

        Args:
            user_id: Discord 사용자 ID
            category: 추가할 카테고리 이름 (예: '식품', 'PC/하드웨어')

        Returns:
            bool: 성공 여부 (이미 존재하면 False)
        """
        try:
            await self.add_user(user_id)
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    INSERT INTO user_categories (user_id, category)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id, category) DO NOTHING
                ''', user_id, category.strip())
                return result == "INSERT 0 1"
        except Exception as e:
            logger.error(f"카테고리 추가 오류: {e}", exc_info=True)
            return False

    async def get_categories(self, user_id: int) -> List[Category]:
        """
        사용자의 카테고리 구독 목록 조회

        Args:
            user_id: Discord 사용자 ID

        Returns:
            List[Category]: 카테고리 리스트
        """
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM user_categories
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                ''', user_id)
                return [
                    Category(
                        id=row['id'],
                        user_id=row['user_id'],
                        category=row['category'],
                        created_at=row['created_at']
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"카테고리 조회 오류: {e}", exc_info=True)
            return []

    async def delete_category(self, user_id: int, category: str) -> bool:
        """
        카테고리 구독 삭제

        Args:
            user_id: Discord 사용자 ID
            category: 삭제할 카테고리 이름

        Returns:
            bool: 성공 여부
        """
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM user_categories
                    WHERE user_id = $1 AND category = $2
                ''', user_id, category.strip())
                return result == "DELETE 1"
        except Exception as e:
            logger.error(f"카테고리 삭제 오류: {e}", exc_info=True)
            return False

    async def get_all_categories(self) -> List[str]:
        """
        구독 중인 모든 카테고리 목록 조회 (중복 제거)

        Returns:
            List[str]: 카테고리 리스트
        """
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT DISTINCT category FROM user_categories
                    ORDER BY category
                ''')
                return [row['category'] for row in rows]
        except Exception as e:
            logger.error(f"모든 카테고리 조회 오류: {e}", exc_info=True)
            return []

    async def get_users_by_category(self, category: str) -> List[int]:
        """
        특정 카테고리를 구독한 사용자 ID 목록 조회

        Args:
            category: 카테고리 이름

        Returns:
            List[int]: 사용자 ID 리스트
        """
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT DISTINCT user_id FROM user_categories
                    WHERE category = $1
                ''', category.strip())
                return [row['user_id'] for row in rows]
        except Exception as e:
            logger.error(f"카테고리로 사용자 조회 오류: {e}", exc_info=True)
            return []

    # ==================== 알림 채널 관리 메서드 ====================
    
    async def set_notification_channel(self, guild_id: int, channel_id: int) -> bool:
        """
        서버의 알림 채널 설정
        
        Args:
            guild_id: 서버 ID
            channel_id: 채널 ID
            
        Returns:
            bool: 성공 여부
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO notification_channels (guild_id, channel_id, updated_at)
                    VALUES ($1, $2, CURRENT_TIMESTAMP)
                    ON CONFLICT (guild_id) 
                    DO UPDATE SET channel_id = $2, updated_at = CURRENT_TIMESTAMP
                ''', guild_id, channel_id)
                
                return True
        except Exception as e:
            logger.error(f"알림 채널 설정 오류: {e}", exc_info=True)
            return False
    
    async def get_notification_channel(self, guild_id: int) -> Optional[int]:
        """
        서버의 알림 채널 조회
        
        Args:
            guild_id: 서버 ID
            
        Returns:
            Optional[int]: 채널 ID 또는 None
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT channel_id FROM notification_channels
                    WHERE guild_id = $1
                ''', guild_id)
                
                return row['channel_id'] if row else None
        except Exception as e:
            logger.error(f"알림 채널 조회 오류: {e}", exc_info=True)
            return None