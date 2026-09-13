# -*- coding: utf-8 -*-
"""
AppleRefurbWatcher 유닛 테스트 (네트워크/DB 없이 실행)
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.apple_refurb_watcher import (
    AppleRefurbWatcher, _size_to_gb, _extract_chip, CRAWLER_NAME,
)


def _tile(part, title, capacity, memory, screen='14inch', model='macbookpro', price='4282000.00'):
    dims = {
        'refurbClearModel': model,
        'dimensionScreensize': screen,
        'dimensionCapacity': capacity,
    }
    if memory is not None:
        dims['tsMemorySize'] = memory
    return {
        'partNumber': part,
        'title': title,
        'filters': {'dimensions': dims},
        'price': {'currentPrice': {'amount': '₩' + f"{int(float(price)):,}", 'raw_amount': price}},
        'productDetailsUrl': f'/kr/shop/product/{part.lower().replace("/", "/")}/refurb?fnode=abc',
        'omnitureModel': {'partNumber': part},
    }


def _html_with_tiles(tiles):
    # 실제 페이지처럼 다른 JSON 키 사이에 "tiles" 배열이 끼어 있는 형태
    return (
        '<html><head><script>window.data = {"filters":{"x":[1,2]},'
        '"tiles":' + json.dumps(tiles, ensure_ascii=False) +
        ',"footer":"[bracket] in string"};</script></head><body></body></html>'
    )


MATCH_TILE = _tile('G1AAAKH/A', '리퍼비쉬 MacBook Pro 14 Apple M4 Max 칩 모델(14코어 CPU 및 32코어 GPU) - 스페이스 블랙', '1tb', '64gb')
LOW_MEM_TILE = _tile('G1MLAKH/A', '리퍼비쉬 MacBook Pro 14 Apple M5 Pro 칩 모델(15코어 CPU 및 16코어 GPU) - 스페이스 블랙', '2tb', '24gb')
SIXTEEN_TILE = _tile('FX303KH/A', '리퍼비쉬 MacBook Pro 16 Apple M4 Max 칩 모델 - 스페이스 블랙', '1tb', '64gb', screen='16inch')
NEO_TILE = _tile('FHFD4KH/A', '리퍼비쉬 MacBook Neo Apple A18 Pro 칩 모델 - 시트러스', '256gb', None, screen='13inch', model='macbookneo', price='1029000.00')


CRITERIA = {
    'model': 'macbookpro', 'screen': '14inch',
    'min_memory_gb': 64, 'min_storage_gb': 1024,
    'chips': ['M3', 'M4', 'M5'], 'max_price': None,
}


# ==================== helpers ====================

class TestHelpers:
    def test_size_tb(self):
        assert _size_to_gb('1tb') == 1024
        assert _size_to_gb('2TB') == 2048

    def test_size_gb(self):
        assert _size_to_gb('512gb') == 512
        assert _size_to_gb('64gb') == 64

    def test_size_invalid(self):
        assert _size_to_gb(None) is None
        assert _size_to_gb('') is None
        assert _size_to_gb('large') is None

    def test_chip_extract(self):
        assert _extract_chip('MacBook Pro 14 Apple M4 Max 칩') == 'M4'
        assert _extract_chip('Apple M5 Pro 칩 모델') == 'M5'
        assert _extract_chip('MacBook Neo Apple A18 Pro') is None
        assert _extract_chip('') is None


# ==================== parse ====================

class TestParse:
    def test_empty_html(self):
        assert AppleRefurbWatcher.parse('') == []

    def test_no_tiles_no_nojs(self):
        assert AppleRefurbWatcher.parse('<html><body>nothing</body></html>') == []

    def test_parses_tiles_json(self):
        items = AppleRefurbWatcher.parse(_html_with_tiles([MATCH_TILE, NEO_TILE]))
        assert len(items) == 2
        it = items[0]
        assert it['part_number'] == 'G1AAAKH/A'
        assert it['model'] == 'macbookpro'
        assert it['screen'] == '14inch'
        assert it['storage_gb'] == 1024
        assert it['memory_gb'] == 64
        assert it['chip'] == 'M4'
        assert it['price_raw'] == 4282000
        assert it['url'].startswith('https://www.apple.com/kr/shop/product/')

    def test_missing_memory_is_none(self):
        items = AppleRefurbWatcher.parse(_html_with_tiles([NEO_TILE]))
        assert items[0]['memory_gb'] is None
        assert items[0]['chip'] is None

    def test_nojs_fallback(self):
        html = '''
        <div class="rf-refurb-category-grid-no-js"><ul>
          <li><h3><a href="/kr/shop/product/g1mlakh/a/%EB%A6%AC%ED%8D%BC-MacBook-Pro-14-M5?fnode=x">
              리퍼비쉬 MacBook Pro 14 Apple M5 Pro 칩 모델 - 스페이스 블랙</a></h3>
              <div class="as-price-currentprice">₩4,282,000</div></li>
        </ul></div>'''
        items = AppleRefurbWatcher.parse(html)
        assert len(items) == 1
        assert items[0]['part_number'] == 'G1MLAKH/A'
        assert items[0]['model'] == 'macbookpro'
        assert items[0]['screen'] == '14inch'
        assert items[0]['chip'] == 'M5'
        assert items[0]['price_raw'] == 4282000
        assert items[0]['memory_gb'] is None


# ==================== matches ====================

class TestMatches:
    def _item(self, **over):
        base = {'model': 'macbookpro', 'screen': '14inch', 'memory_gb': 64,
                'storage_gb': 1024, 'chip': 'M4', 'price_raw': 4000000}
        base.update(over)
        return base

    def test_exact_match(self):
        assert AppleRefurbWatcher.matches(self._item(), CRITERIA)

    def test_higher_specs_match(self):
        assert AppleRefurbWatcher.matches(self._item(memory_gb=128, storage_gb=4096, chip='M5'), CRITERIA)

    def test_low_memory_rejected(self):
        assert not AppleRefurbWatcher.matches(self._item(memory_gb=48), CRITERIA)

    def test_low_storage_rejected(self):
        assert not AppleRefurbWatcher.matches(self._item(storage_gb=512), CRITERIA)

    def test_wrong_screen_rejected(self):
        assert not AppleRefurbWatcher.matches(self._item(screen='16inch'), CRITERIA)

    def test_wrong_model_rejected(self):
        assert not AppleRefurbWatcher.matches(self._item(model='macbookair'), CRITERIA)

    def test_old_chip_rejected(self):
        assert not AppleRefurbWatcher.matches(self._item(chip='M2'), CRITERIA)

    def test_missing_info_passes(self):
        """정보 없는 필드는 놓치지 않도록 통과"""
        assert AppleRefurbWatcher.matches(self._item(memory_gb=None, storage_gb=None, chip=None), CRITERIA)

    def test_max_price(self):
        c = dict(CRITERIA, max_price=3000000)
        assert not AppleRefurbWatcher.matches(self._item(price_raw=4000000), c)
        assert AppleRefurbWatcher.matches(self._item(price_raw=2500000), c)

    def test_real_tiles_against_criteria(self):
        items = AppleRefurbWatcher.parse(_html_with_tiles([MATCH_TILE, LOW_MEM_TILE, SIXTEEN_TILE, NEO_TILE]))
        matched = [i['part_number'] for i in items if AppleRefurbWatcher.matches(i, CRITERIA)]
        assert matched == ['G1AAAKH/A']


# ==================== run ====================

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_refurb_snapshot = AsyncMock(return_value={})
    db.replace_refurb_snapshot = AsyncMock(return_value=True)
    db.get_last_post_id = AsyncMock(return_value=None)
    db.update_last_post_id = AsyncMock(return_value=True)
    db.get_users_by_keyword = AsyncMock(return_value=[12345])
    return db


@pytest.fixture
def mock_notifier():
    n = MagicMock()
    n.send_refurb_alert = AsyncMock(return_value=True)
    return n


@pytest.fixture
def watcher(mock_db, mock_notifier, monkeypatch):
    from config.settings import Settings
    monkeypatch.setattr(Settings, 'APPLE_REFURB_TRIGGER_KEYWORD', '애플리퍼')
    monkeypatch.setattr(Settings, 'APPLE_REFURB_MODEL', 'macbookpro')
    monkeypatch.setattr(Settings, 'APPLE_REFURB_SCREEN', '14inch')
    monkeypatch.setattr(Settings, 'APPLE_REFURB_MIN_MEMORY_GB', 64)
    monkeypatch.setattr(Settings, 'APPLE_REFURB_MIN_STORAGE_GB', 1024)
    monkeypatch.setattr(Settings, 'APPLE_REFURB_CHIPS', ['M3', 'M4', 'M5'])
    monkeypatch.setattr(Settings, 'APPLE_REFURB_MAX_PRICE', None)
    w = AppleRefurbWatcher(mock_db, mock_notifier)
    return w


class TestRun:
    @pytest.mark.asyncio
    async def test_skips_without_subscribers(self, watcher, mock_db):
        mock_db.get_users_by_keyword = AsyncMock(return_value=[])
        watcher.fetch = AsyncMock(return_value=_html_with_tiles([MATCH_TILE]))
        assert await watcher.run() == 0
        mock_db.get_users_by_keyword.assert_awaited_once_with('애플리퍼')
        watcher.fetch.assert_not_called()
        mock_db.replace_refurb_snapshot.assert_not_called()

    @pytest.mark.asyncio
    async def test_alerts_every_subscriber(self, watcher, mock_db, mock_notifier):
        mock_db.get_users_by_keyword = AsyncMock(return_value=[111, 222])
        mock_db.get_last_post_id = AsyncMock(return_value='1')
        mock_db.get_refurb_snapshot = AsyncMock(return_value={})
        watcher.fetch = AsyncMock(return_value=_html_with_tiles([MATCH_TILE]))
        assert await watcher.run() == 2
        called_users = [c.args[0] for c in mock_notifier.send_refurb_alert.await_args_list]
        assert called_users == [111, 222]

    @pytest.mark.asyncio
    async def test_first_run_saves_snapshot_without_alert(self, watcher, mock_db, mock_notifier):
        watcher.fetch = AsyncMock(return_value=_html_with_tiles([MATCH_TILE, NEO_TILE]))
        mock_db.get_last_post_id = AsyncMock(return_value=None)
        assert await watcher.run() == 0
        mock_notifier.send_refurb_alert.assert_not_called()
        mock_db.replace_refurb_snapshot.assert_awaited_once()
        saved = mock_db.replace_refurb_snapshot.await_args.args[0]
        assert {i['part_number'] for i in saved} == {'G1AAAKH/A', 'FHFD4KH/A'}
        mock_db.update_last_post_id.assert_awaited_once()
        assert mock_db.update_last_post_id.await_args.args[0] == CRAWLER_NAME

    @pytest.mark.asyncio
    async def test_new_matching_item_alerts(self, watcher, mock_db, mock_notifier):
        mock_db.get_last_post_id = AsyncMock(return_value='1')
        mock_db.get_refurb_snapshot = AsyncMock(return_value={'FHFD4KH/A': {}})
        watcher.fetch = AsyncMock(return_value=_html_with_tiles([MATCH_TILE, NEO_TILE, LOW_MEM_TILE]))
        assert await watcher.run() == 1
        mock_notifier.send_refurb_alert.assert_awaited_once()
        user_id, item = mock_notifier.send_refurb_alert.await_args.args
        assert user_id == 12345
        assert item['part_number'] == 'G1AAAKH/A'

    @pytest.mark.asyncio
    async def test_already_seen_item_no_alert(self, watcher, mock_db, mock_notifier):
        mock_db.get_last_post_id = AsyncMock(return_value='1')
        mock_db.get_refurb_snapshot = AsyncMock(return_value={'G1AAAKH/A': {}})
        watcher.fetch = AsyncMock(return_value=_html_with_tiles([MATCH_TILE]))
        assert await watcher.run() == 0
        mock_notifier.send_refurb_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_parse_keeps_snapshot(self, watcher, mock_db):
        mock_db.get_last_post_id = AsyncMock(return_value='1')
        watcher.fetch = AsyncMock(return_value='<html>maintenance</html>')
        assert await watcher.run() == 0
        mock_db.replace_refurb_snapshot.assert_not_called()
        mock_db.update_last_post_id.assert_not_called()
