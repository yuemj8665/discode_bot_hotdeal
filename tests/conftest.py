# -*- coding: utf-8 -*-
"""
공통 테스트 픽스처
"""
import pytest

TEST_DATABASE_URL = "postgresql://root:root@localhost:5432/hotdeal_test"


@pytest.fixture
def sample_posts():
    """테스트용 게시글 데이터"""
    return [
        {
            "post_id": "100",
            "title": "삼성 노트북 50% 할인",
            "price": "500,000원",
            "url": "/b/hotdeal/100",
            "full_url": "https://arca.live/b/hotdeal/100",
            "source": "Arca Live",
            "datetime": "2026-03-11T10:00:00",
        },
        {
            "post_id": "99",
            "title": "애플 맥북 프로 특가",
            "price": "1,500,000원",
            "url": "/b/hotdeal/99",
            "full_url": "https://arca.live/b/hotdeal/99",
            "source": "Arca Live",
            "datetime": "2026-03-11T09:00:00",
        },
        {
            "post_id": "98",
            "title": "LG 모니터 최저가",
            "price": "200,000원",
            "url": "/b/hotdeal/98",
            "full_url": "https://arca.live/b/hotdeal/98",
            "source": "Arca Live",
            "datetime": "2026-03-11T08:00:00",
        },
    ]
