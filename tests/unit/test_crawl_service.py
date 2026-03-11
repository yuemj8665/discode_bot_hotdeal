# -*- coding: utf-8 -*-
"""
CrawlService 유닛 테스트 (Mock DB/크롤러 사용)
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from services.crawl_service import CrawlService


@pytest.fixture
def mock_crawler():
    crawler = MagicMock()
    crawler.crawler_name = "test_crawler"
    crawler.check_keywords = MagicMock(return_value=[])
    return crawler


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_last_post_datetime = AsyncMock(return_value=None)
    db.get_last_post_url = AsyncMock(return_value=None)
    db.get_last_post_id = AsyncMock(return_value=None)
    db.update_last_post_id = AsyncMock(return_value=True)
    db.get_all_keywords = AsyncMock(return_value=[])
    db.get_users_by_keyword = AsyncMock(return_value=[])
    db.add_hotdeal = AsyncMock(return_value=True)
    return db


@pytest.fixture
def service(mock_crawler, mock_db):
    return CrawlService(mock_crawler, mock_db)


# ==================== _filter_by_id ====================

class TestFilterById:
    def test_returns_newer_posts(self, service, sample_posts):
        result = service._filter_by_id(sample_posts, "98")
        ids = [p["post_id"] for p in result]
        assert "100" in ids
        assert "99" in ids
        assert "98" not in ids

    def test_no_new_posts(self, service, sample_posts):
        result = service._filter_by_id(sample_posts, "100")
        assert result == []

    def test_all_new_when_last_id_is_zero(self, service, sample_posts):
        result = service._filter_by_id(sample_posts, "0")
        assert len(result) == 3

    def test_invalid_last_id_returns_none(self, service, sample_posts):
        result = service._filter_by_id(sample_posts, "not_a_number")
        assert result is None


# ==================== _filter_by_url ====================

class TestFilterByUrl:
    def test_returns_posts_before_last_url(self, service, sample_posts):
        last_url = "https://arca.live/b/hotdeal/99"
        result = service._filter_by_url(sample_posts, last_url)
        ids = [p["post_id"] for p in result]
        assert "100" in ids
        assert "99" not in ids
        assert "98" not in ids

    def test_url_with_query_string_normalized(self, service, sample_posts):
        last_url = "https://arca.live/b/hotdeal/99?p=1"
        result = service._filter_by_url(sample_posts, last_url)
        ids = [p["post_id"] for p in result]
        assert "100" in ids
        assert "99" not in ids

    def test_url_not_found_returns_all(self, service, sample_posts):
        result = service._filter_by_url(sample_posts, "https://arca.live/b/hotdeal/999")
        assert len(result) == len(sample_posts)


# ==================== _filter_by_datetime ====================

class TestFilterByDatetime:
    def test_returns_newer_posts(self, service, sample_posts):
        last_dt = datetime(2026, 3, 11, 9, 0, 0)
        result = service._filter_by_datetime(sample_posts, last_dt, None)
        ids = [p["post_id"] for p in result]
        assert "100" in ids
        assert "99" not in ids
        assert "98" not in ids

    def test_no_new_posts_when_all_old(self, service, sample_posts):
        last_dt = datetime(2026, 3, 11, 11, 0, 0)
        result = service._filter_by_datetime(sample_posts, last_dt, None)
        assert result == []

    def test_all_new_when_last_dt_is_old(self, service, sample_posts):
        last_dt = datetime(2026, 3, 11, 7, 0, 0)
        result = service._filter_by_datetime(sample_posts, last_dt, None)
        assert len(result) == 3


# ==================== filter_new_posts ====================

class TestFilterNewPosts:
    @pytest.mark.asyncio
    async def test_first_crawl_returns_all(self, service, sample_posts):
        result = await service.filter_new_posts(sample_posts)
        assert len(result) == len(sample_posts)

    @pytest.mark.asyncio
    async def test_empty_posts_returns_empty(self, service):
        result = await service.filter_new_posts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_filters_by_id_when_no_datetime_url(self, service, mock_db, sample_posts):
        mock_db.get_last_post_id = AsyncMock(return_value="99")
        result = await service.filter_new_posts(sample_posts)
        ids = [p["post_id"] for p in result]
        assert "100" in ids
        assert "99" not in ids


# ==================== _parse_post_datetime ====================

class TestParsePostDatetime:
    def test_valid_iso_datetime(self, service):
        result = service._parse_post_datetime("2026-03-11T10:00:00")
        assert result == datetime(2026, 3, 11, 10, 0, 0)

    def test_timezone_aware_becomes_naive(self, service):
        result = service._parse_post_datetime("2026-03-11T10:00:00+09:00")
        assert result.tzinfo is None

    def test_empty_string_returns_none(self, service):
        assert service._parse_post_datetime("") is None

    def test_invalid_string_returns_none(self, service):
        assert service._parse_post_datetime("not-a-date") is None
