# -*- coding: utf-8 -*-
"""
Database 통합 테스트 (hotdeal_test DB 사용)
실제 PostgreSQL 연결 — 운영 DB(studydb)와 완전히 분리
"""
import pytest
from database.db import Database
from database.models import Hotdeal
from tests.conftest import TEST_DATABASE_URL


@pytest.fixture
async def db():
    """각 테스트마다 독립된 DB 연결 (hotdeal_test DB 사용)"""
    database = Database(db_url=TEST_DATABASE_URL)
    await database.connect()
    yield database
    # 테스트 후 테이블 초기화
    async with database._pool.acquire() as conn:
        await conn.execute("DELETE FROM user_categories")
        await conn.execute("DELETE FROM keywords")
        await conn.execute("DELETE FROM hotdeals")
        await conn.execute("DELETE FROM crawl_state")
        await conn.execute("DELETE FROM notification_channels")
        await conn.execute("DELETE FROM users")
    await database.close()


# ==================== 사용자 ====================

class TestUser:
    @pytest.mark.asyncio
    async def test_add_user(self, db):
        result = await db.add_user(111)
        assert result is True

    @pytest.mark.asyncio
    async def test_add_duplicate_user_returns_false(self, db):
        await db.add_user(111)
        result = await db.add_user(111)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_user(self, db):
        await db.add_user(111)
        user = await db.get_user(111)
        assert user is not None
        assert user.user_id == 111

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_none(self, db):
        user = await db.get_user(999999)
        assert user is None

    @pytest.mark.asyncio
    async def test_delete_user(self, db):
        await db.add_user(111)
        result = await db.delete_user(111)
        assert result is True
        assert await db.get_user(111) is None


# ==================== 키워드 ====================

class TestKeyword:
    @pytest.mark.asyncio
    async def test_add_keyword(self, db):
        result = await db.add_keyword(111, "노트북")
        assert result is True

    @pytest.mark.asyncio
    async def test_add_duplicate_keyword_returns_false(self, db):
        await db.add_keyword(111, "노트북")
        result = await db.add_keyword(111, "노트북")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_keywords(self, db):
        await db.add_keyword(111, "노트북")
        await db.add_keyword(111, "맥북")
        keywords = await db.get_keywords(111)
        keyword_texts = [k.keyword for k in keywords]
        assert "노트북" in keyword_texts
        assert "맥북" in keyword_texts

    @pytest.mark.asyncio
    async def test_delete_keyword(self, db):
        await db.add_keyword(111, "노트북")
        result = await db.delete_keyword(111, "노트북")
        assert result is True
        keywords = await db.get_keywords(111)
        assert all(k.keyword != "노트북" for k in keywords)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_keyword_returns_false(self, db):
        result = await db.delete_keyword(111, "없는키워드")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_all_keywords(self, db):
        await db.add_keyword(111, "노트북")
        await db.add_keyword(111, "맥북")
        count = await db.delete_all_keywords(111)
        assert count == 2
        assert await db.get_keywords(111) == []

    @pytest.mark.asyncio
    async def test_get_users_by_keyword(self, db):
        await db.add_keyword(111, "노트북")
        await db.add_keyword(222, "노트북")
        await db.add_keyword(333, "맥북")
        users = await db.get_users_by_keyword("노트북")
        assert 111 in users
        assert 222 in users
        assert 333 not in users

    @pytest.mark.asyncio
    async def test_get_all_keywords_deduped(self, db):
        await db.add_keyword(111, "노트북")
        await db.add_keyword(222, "노트북")
        await db.add_keyword(111, "맥북")
        keywords = await db.get_all_keywords()
        assert keywords.count("노트북") == 1
        assert "맥북" in keywords

    @pytest.mark.asyncio
    async def test_keyword_cascade_deleted_with_user(self, db):
        await db.add_keyword(111, "노트북")
        await db.delete_user(111)
        keywords = await db.get_keywords(111)
        assert keywords == []


# ==================== 핫딜 ====================

class TestHotdeal:
    @pytest.fixture
    def hotdeal(self):
        return Hotdeal(
            title="테스트 핫딜",
            price="10,000원",
            url="https://arca.live/b/hotdeal/99999",
            source="Arca Live"
        )

    @pytest.mark.asyncio
    async def test_add_hotdeal(self, db, hotdeal):
        result = await db.add_hotdeal(hotdeal)
        assert result is True

    @pytest.mark.asyncio
    async def test_add_duplicate_hotdeal_returns_false(self, db, hotdeal):
        await db.add_hotdeal(hotdeal)
        result = await db.add_hotdeal(hotdeal)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_hotdeals(self, db, hotdeal):
        await db.add_hotdeal(hotdeal)
        hotdeals = await db.get_hotdeals()
        assert len(hotdeals) == 1
        assert hotdeals[0].title == "테스트 핫딜"

    @pytest.mark.asyncio
    async def test_get_hotdeal_by_url(self, db, hotdeal):
        await db.add_hotdeal(hotdeal)
        result = await db.get_hotdeal_by_url(hotdeal.url)
        assert result is not None
        assert result.title == hotdeal.title

    @pytest.mark.asyncio
    async def test_get_hotdeal_by_nonexistent_url_returns_none(self, db):
        result = await db.get_hotdeal_by_url("https://arca.live/b/hotdeal/0")
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_old_hotdeals(self, db):
        from datetime import timedelta
        hotdeal = Hotdeal(
            title="오래된 핫딜",
            price="1,000원",
            url="https://arca.live/b/hotdeal/1",
            source="Arca Live"
        )
        await db.add_hotdeal(hotdeal)
        # created_at을 48시간 전으로 강제 업데이트
        async with db._pool.acquire() as conn:
            await conn.execute(
                "UPDATE hotdeals SET created_at = NOW() - INTERVAL '48 hours' WHERE url = $1",
                hotdeal.url
            )
        deleted = await db.cleanup_old_hotdeals(hours=24)
        assert deleted == 1


# ==================== 크롤 상태 ====================

class TestCrawlState:
    @pytest.mark.asyncio
    async def test_update_and_get_last_post_id(self, db):
        await db.update_last_post_id("test_crawler", "12345")
        result = await db.get_last_post_id("test_crawler")
        assert result == "12345"

    @pytest.mark.asyncio
    async def test_update_with_url(self, db):
        url = "https://arca.live/b/hotdeal/12345"
        await db.update_last_post_id("test_crawler", "12345", post_url=url)
        assert await db.get_last_post_url("test_crawler") == url

    @pytest.mark.asyncio
    async def test_update_with_datetime(self, db):
        from datetime import datetime
        dt = datetime(2026, 3, 11, 10, 0, 0)
        url = "https://arca.live/b/hotdeal/12345"
        await db.update_last_post_id("test_crawler", "12345", post_url=url, post_datetime=dt)
        result = await db.get_last_post_datetime("test_crawler")
        assert result == dt

    @pytest.mark.asyncio
    async def test_get_nonexistent_crawler_returns_none(self, db):
        assert await db.get_last_post_id("nonexistent") is None

    @pytest.mark.asyncio
    async def test_upsert_overwrites(self, db):
        await db.update_last_post_id("test_crawler", "100")
        await db.update_last_post_id("test_crawler", "200")
        result = await db.get_last_post_id("test_crawler")
        assert result == "200"


# ==================== 알림 채널 ====================

class TestNotificationChannel:
    @pytest.mark.asyncio
    async def test_set_and_get_channel(self, db):
        await db.set_notification_channel(guild_id=1001, channel_id=2001)
        result = await db.get_notification_channel(1001)
        assert result == 2001

    @pytest.mark.asyncio
    async def test_get_nonexistent_guild_returns_none(self, db):
        result = await db.get_notification_channel(9999)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_channel(self, db):
        await db.set_notification_channel(guild_id=1001, channel_id=2001)
        await db.set_notification_channel(guild_id=1001, channel_id=3001)
        result = await db.get_notification_channel(1001)
        assert result == 3001


# ==================== 카테고리 구독 ====================

class TestCategory:
    @pytest.mark.asyncio
    async def test_add_category(self, db):
        result = await db.add_category(111, "식품")
        assert result is True

    @pytest.mark.asyncio
    async def test_add_duplicate_category_returns_false(self, db):
        await db.add_category(111, "식품")
        result = await db.add_category(111, "식품")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_categories(self, db):
        await db.add_category(111, "식품")
        await db.add_category(111, "전자제품")
        categories = await db.get_categories(111)
        names = [c.category for c in categories]
        assert "식품" in names
        assert "전자제품" in names

    @pytest.mark.asyncio
    async def test_delete_category(self, db):
        await db.add_category(111, "식품")
        result = await db.delete_category(111, "식품")
        assert result is True
        categories = await db.get_categories(111)
        assert all(c.category != "식품" for c in categories)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_category_returns_false(self, db):
        result = await db.delete_category(111, "의류")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_users_by_category(self, db):
        await db.add_category(111, "식품")
        await db.add_category(222, "식품")
        await db.add_category(333, "전자제품")
        users = await db.get_users_by_category("식품")
        assert 111 in users
        assert 222 in users
        assert 333 not in users

    @pytest.mark.asyncio
    async def test_get_all_categories_deduped(self, db):
        await db.add_category(111, "식품")
        await db.add_category(222, "식품")
        await db.add_category(111, "전자제품")
        all_cats = await db.get_all_categories()
        assert all_cats.count("식품") == 1
        assert "전자제품" in all_cats

    @pytest.mark.asyncio
    async def test_category_cascade_deleted_with_user(self, db):
        await db.add_category(111, "식품")
        await db.delete_user(111)
        categories = await db.get_categories(111)
        assert categories == []
