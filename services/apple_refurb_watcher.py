# -*- coding: utf-8 -*-
"""
애플 리퍼비쉬 스토어(한국) 재고 감시 서비스

수신자는 트리거 키워드(기본 '애플리퍼')를 !키워드 추가 로 등록한 사용자.
등록자가 없으면 크롤링도 하지 않는다. 페이지에 새 부품번호가 나타나고
조건(모델/화면/메모리/용량/칩/가격)에 맞으면 등록자 전원에게 DM을 보낸다.
"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from config.settings import Settings

logger = logging.getLogger(__name__)

REFURB_URL = "https://www.apple.com/kr/shop/refurbished/mac"
BASE_URL = "https://www.apple.com"
CRAWLER_NAME = "apple_refurb"

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
}

_CHIP_RE = re.compile(r'\bM(\d)\b', re.IGNORECASE)
_SIZE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(tb|gb)', re.IGNORECASE)


def _size_to_gb(text: Optional[str]) -> Optional[int]:
    """'1tb' → 1024, '512gb' → 512, 없거나 형식 불일치 → None"""
    if not text:
        return None
    m = _SIZE_RE.search(text)
    if not m:
        return None
    value = float(m.group(1))
    return int(value * 1024) if m.group(2).lower() == 'tb' else int(value)


def _extract_chip(title: str) -> Optional[str]:
    """제목에서 'M3' / 'M4' / 'M5' 세대 추출 (Pro/Max 접미어 무시)"""
    m = _CHIP_RE.search(title or '')
    return f"M{m.group(1)}" if m else None


class AppleRefurbWatcher:
    """애플 리퍼비쉬 재고 감시 및 조건 매칭 알림"""

    def __init__(self, db, notification_service, url: str = REFURB_URL):
        self.db = db
        self.notification_service = notification_service
        self.url = url

    # ------------------------------------------------------------------ fetch

    async def fetch(self, max_retries: int = 3) -> str:
        """페이지 HTML 가져오기 (지수 백오프 재시도)"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(headers=_HEADERS) as session:
                    async with session.get(self.url, timeout=timeout) as response:
                        if response.status == 200:
                            return await response.text()
                        logger.warning(
                            f"애플 리퍼비쉬 HTTP 오류: {response.status} "
                            f"(시도 {attempt + 1}/{max_retries})"
                        )
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"애플 리퍼비쉬 요청 오류: {e} (시도 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        return ""

    # ------------------------------------------------------------------ parse

    @staticmethod
    def parse(html: str) -> List[Dict[str, Any]]:
        """
        HTML → 상품 목록. 임베디드 tiles JSON을 우선 사용하고, 실패 시 no-js HTML 폴백.

        각 항목: part_number, title, price(표시용), price_raw(int|None), url,
                 model, screen, storage_gb, memory_gb, chip
        """
        if not html:
            return []
        items = AppleRefurbWatcher._parse_tiles_json(html)
        if items:
            return items
        logger.warning("tiles JSON 파싱 실패 — no-js HTML 폴백 시도")
        return AppleRefurbWatcher._parse_nojs_html(html)

    @staticmethod
    def _parse_tiles_json(html: str) -> List[Dict[str, Any]]:
        key = '"tiles":'
        idx = html.find(key)
        if idx < 0:
            return []
        start = idx + len(key)
        while start < len(html) and html[start] in ' \n\r\t':
            start += 1
        try:
            tiles, _ = json.JSONDecoder().raw_decode(html, start)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"tiles JSON 디코드 오류: {e}")
            return []
        if not isinstance(tiles, list):
            return []

        items = []
        for tile in tiles:
            try:
                part_number = (
                    tile.get('partNumber')
                    or tile.get('omnitureModel', {}).get('partNumber', '')
                )
                if not part_number:
                    continue
                title = tile.get('title', '') or ''
                dims = tile.get('filters', {}).get('dimensions', {}) or {}
                price_info = (tile.get('price') or {}).get('currentPrice') or {}
                raw = price_info.get('raw_amount')
                price_raw = int(float(raw)) if raw not in (None, '') else None
                url = tile.get('productDetailsUrl', '') or ''
                if url and not url.startswith('http'):
                    url = BASE_URL + url
                items.append({
                    'part_number': part_number,
                    'title': title,
                    'price': price_info.get('amount', '') or '',
                    'price_raw': price_raw,
                    'url': url,
                    'model': (dims.get('refurbClearModel') or '').lower() or None,
                    'screen': (dims.get('dimensionScreensize') or '').lower() or None,
                    'storage_gb': _size_to_gb(dims.get('dimensionCapacity')),
                    'memory_gb': _size_to_gb(dims.get('tsMemorySize')),
                    'chip': _extract_chip(title),
                })
            except Exception as e:
                logger.warning(f"타일 파싱 오류: {e}", exc_info=True)
        return items

    @staticmethod
    def _parse_nojs_html(html: str) -> List[Dict[str, Any]]:
        """필터 정보가 없는 폴백. 제목에서 모델/화면만 추정하고 나머지는 None."""
        items = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for li in soup.select('.rf-refurb-category-grid-no-js li'):
                a = li.select_one('h3 a[href]')
                if not a:
                    continue
                href = a.get('href', '')
                m = re.search(r'/shop/product/([a-z0-9]+)/([a-z])', href, re.IGNORECASE)
                if not m:
                    continue
                part_number = f"{m.group(1).upper()}/{m.group(2).upper()}"
                title = a.get_text(strip=True)
                price_el = li.select_one('.as-price-currentprice')
                price = price_el.get_text(strip=True) if price_el else ''
                digits = re.sub(r'[^\d]', '', price)
                lower = title.lower()
                screen_m = re.search(r'\b(1[3-6])\b', title)
                items.append({
                    'part_number': part_number,
                    'title': title,
                    'price': price,
                    'price_raw': int(digits) if digits else None,
                    'url': BASE_URL + href if href.startswith('/') else href,
                    'model': 'macbookpro' if 'macbook pro' in lower else None,
                    'screen': f"{screen_m.group(1)}inch" if screen_m else None,
                    'storage_gb': None,
                    'memory_gb': None,
                    'chip': _extract_chip(title),
                })
        except Exception as e:
            logger.error(f"no-js HTML 파싱 오류: {e}", exc_info=True)
        return items

    # ------------------------------------------------------------------ match

    @staticmethod
    def matches(item: Dict[str, Any], criteria: Optional[Dict[str, Any]] = None) -> bool:
        """
        조건 판별. 값이 None(정보 없음)인 필드는 통과시킨다 — 일회성 구매 알림이므로
        놓치는 것보다 한 번 더 확인하는 쪽이 낫다.
        """
        c = criteria or AppleRefurbWatcher.default_criteria()

        if c.get('model') and item.get('model') and item['model'] != c['model']:
            return False
        if c.get('screen') and item.get('screen') and item['screen'] != c['screen']:
            return False
        if c.get('min_memory_gb') and item.get('memory_gb') is not None \
                and item['memory_gb'] < c['min_memory_gb']:
            return False
        if c.get('min_storage_gb') and item.get('storage_gb') is not None \
                and item['storage_gb'] < c['min_storage_gb']:
            return False
        if c.get('chips') and item.get('chip') and item['chip'].upper() not in c['chips']:
            return False
        if c.get('max_price') and item.get('price_raw') is not None \
                and item['price_raw'] > c['max_price']:
            return False
        return True

    @staticmethod
    def default_criteria() -> Dict[str, Any]:
        return {
            'model': Settings.APPLE_REFURB_MODEL,
            'screen': Settings.APPLE_REFURB_SCREEN,
            'min_memory_gb': Settings.APPLE_REFURB_MIN_MEMORY_GB,
            'min_storage_gb': Settings.APPLE_REFURB_MIN_STORAGE_GB,
            'chips': [c.upper() for c in Settings.APPLE_REFURB_CHIPS],
            'max_price': Settings.APPLE_REFURB_MAX_PRICE,
        }

    # -------------------------------------------------------------------- run

    async def run(self) -> int:
        """
        1회 감시 실행. 반환값은 발송한 알림 수.
        - 트리거 키워드 등록자가 없으면 크롤링 없이 종료
        - 첫 실행(crawl_state에 기록 없음)은 알림 없이 스냅샷만 저장
        - 파싱 결과 0개면 스냅샷을 건드리지 않음 (다음 회차 전체 재알림 방지)
        """
        recipients = await self.db.get_users_by_keyword(Settings.APPLE_REFURB_TRIGGER_KEYWORD)
        if not recipients:
            logger.debug(
                f"애플 리퍼비쉬: '{Settings.APPLE_REFURB_TRIGGER_KEYWORD}' 키워드 등록자 없음, 건너뜀"
            )
            return 0

        html = await self.fetch()
        items = self.parse(html)
        if not items:
            logger.warning("애플 리퍼비쉬: 상품을 파싱하지 못해 이번 회차 건너뜀")
            return 0

        previous = await self.db.get_refurb_snapshot()
        first_run = await self.db.get_last_post_id(CRAWLER_NAME) is None
        new_items = [i for i in items if i['part_number'] not in previous]

        sent = 0
        if first_run:
            logger.info(
                f"애플 리퍼비쉬 첫 실행: 재고 {len(items)}개 스냅샷 저장 (알림 없음)"
            )
        elif new_items:
            matched = [i for i in new_items if self.matches(i)]
            logger.info(
                f"애플 리퍼비쉬 새 재고 {len(new_items)}개, 조건 일치 {len(matched)}개, "
                f"수신자 {len(recipients)}명"
            )
            for item in matched:
                for user_id in recipients:
                    if await self.notification_service.send_refurb_alert(user_id, item):
                        sent += 1
                    else:
                        logger.warning(
                            f"리퍼비쉬 알림 전송 실패: {item['part_number']} → {user_id}"
                        )

        await self.db.replace_refurb_snapshot(items)
        await self.db.update_last_post_id(CRAWLER_NAME, str(len(items)), self.url, None)
        return sent
