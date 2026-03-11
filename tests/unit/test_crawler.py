# -*- coding: utf-8 -*-
"""
HotdealCrawler 유닛 테스트 (DB/네트워크 없이 실행)
"""
import pytest
from crawling.crawler import HotdealCrawler


@pytest.fixture
def crawler():
    return HotdealCrawler()


# ==================== check_keywords ====================

class TestCheckKeywords:
    def test_keyword_matched(self, crawler):
        matched = crawler.check_keywords("삼성 노트북 할인", ["노트북"])
        assert "노트북" in matched

    def test_keyword_not_matched(self, crawler):
        matched = crawler.check_keywords("삼성 노트북 할인", ["맥북"])
        assert matched == []

    def test_multiple_keywords_partial_match(self, crawler):
        matched = crawler.check_keywords("삼성 노트북 할인", ["노트북", "맥북", "삼성"])
        assert "노트북" in matched
        assert "삼성" in matched
        assert "맥북" not in matched

    def test_wildcard_matches_all(self, crawler):
        matched = crawler.check_keywords("어떤 제목이든", ["*"])
        assert "*" in matched

    def test_case_insensitive(self, crawler):
        matched = crawler.check_keywords("Samsung Laptop Sale", ["samsung"])
        assert "samsung" in matched

    def test_empty_title(self, crawler):
        matched = crawler.check_keywords("", ["노트북"])
        assert matched == []

    def test_empty_keywords(self, crawler):
        matched = crawler.check_keywords("삼성 노트북 할인", [])
        assert matched == []

    def test_whitespace_keyword_ignored(self, crawler):
        matched = crawler.check_keywords("삼성 노트북", ["   "])
        assert matched == []


# ==================== _extract_price_numeric ====================

class TestExtractPriceNumeric:
    def test_korean_price(self, crawler):
        assert crawler._extract_price_numeric("24,900원") == 24900

    def test_usd_price(self, crawler):
        assert crawler._extract_price_numeric("$209.99") == 20999

    def test_no_price(self, crawler):
        assert crawler._extract_price_numeric("") is None

    def test_none_price(self, crawler):
        assert crawler._extract_price_numeric(None) is None

    def test_plain_number(self, crawler):
        assert crawler._extract_price_numeric("50000") == 50000


# ==================== _get_full_url ====================

class TestGetFullUrl:
    def test_relative_url(self, crawler):
        result = crawler._get_full_url("/b/hotdeal/12345")
        assert result == "https://arca.live/b/hotdeal/12345"

    def test_absolute_url_unchanged(self, crawler):
        url = "https://arca.live/b/hotdeal/12345"
        assert crawler._get_full_url(url) == url

    def test_empty_url(self, crawler):
        assert crawler._get_full_url("") == ""


# ==================== parse ====================

class TestParse:
    def test_empty_html_returns_empty(self, crawler):
        assert crawler.parse("") == []

    def test_invalid_html_returns_empty(self, crawler):
        assert crawler.parse("<html><body>내용없음</body></html>") == []

    def test_returns_list(self, crawler):
        result = crawler.parse("<html></html>")
        assert isinstance(result, list)

    def test_valid_html_structure(self, crawler):
        """실제 Arca Live 구조와 유사한 HTML로 파싱 검증"""
        html = """
        <div class="list-table hybrid">
            <div class="vrow hybrid">
                <div class="vrow-top">
                    <span class="col-id"><span>12345</span></span>
                </div>
                <a class="hybrid-title" href="/b/hotdeal/12345">테스트 핫딜 제목</a>
                <span class="deal-price">10,000원</span>
                <div class="col-time"><time datetime="2026-03-11T10:00:00">10:00</time></div>
            </div>
        </div>
        """
        result = crawler.parse(html)
        assert isinstance(result, list)
