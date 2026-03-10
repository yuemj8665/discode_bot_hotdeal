# -*- coding: utf-8 -*-
"""
크롤링 서비스
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from database.models import Hotdeal
from .notification_service import NotificationService

logger = logging.getLogger(__name__)


class CrawlService:
    """크롤링 및 새 게시글 감지를 담당하는 서비스"""

    def __init__(self, crawler, db):
        self.crawler = crawler
        self.db = db

    async def fetch_and_parse(self) -> List[Dict[str, Any]]:
        """HTML을 가져와서 파싱한 모든 게시글 반환"""
        html_data = await self.crawler.fetch()
        if not html_data:
            return []
        return self.crawler.parse(html_data)

    async def filter_new_posts(self, all_posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        마지막 크롤링 이후의 새로운 게시글만 필터링.
        datetime > URL > post ID 순으로 폴백.
        """
        if not all_posts:
            return []

        last_datetime = await self.db.get_last_post_datetime(self.crawler.crawler_name)
        last_url = await self.db.get_last_post_url(self.crawler.crawler_name)
        last_id = await self.db.get_last_post_id(self.crawler.crawler_name)

        if last_datetime:
            new_posts = self._filter_by_datetime(all_posts, last_datetime, last_url)
            if new_posts is not None:
                return new_posts

        if last_url:
            new_posts = self._filter_by_url(all_posts, last_url)
            return new_posts

        if last_id:
            new_posts = self._filter_by_id(all_posts, last_id)
            if new_posts is not None:
                return new_posts

        logger.info("첫 크롤링: 모든 게시글을 새로운 것으로 간주")
        return all_posts

    def _filter_by_datetime(
        self,
        posts: List[Dict[str, Any]],
        last_datetime: datetime,
        last_url: Optional[str],
    ) -> Optional[List[Dict[str, Any]]]:
        """datetime 기준으로 새 게시글 필터링. 실패 시 None 반환."""
        from dateutil import parser as date_parser

        last_naive = last_datetime.replace(tzinfo=None) if last_datetime.tzinfo else last_datetime
        new_posts = []

        try:
            for post in posts:
                dt_str = post.get('datetime', '')
                if dt_str:
                    try:
                        parsed = date_parser.isoparse(dt_str)
                        post_naive = parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
                        if post_naive > last_naive:
                            new_posts.append(post)
                    except (ValueError, TypeError) as e:
                        logger.debug(f"게시글 datetime 파싱 오류: {dt_str}, {e}")
                        if last_url and self._url_differs(post, last_url):
                            new_posts.append(post)
                else:
                    if last_url and self._url_differs(post, last_url):
                        new_posts.append(post)

            if new_posts:
                logger.info(
                    f"새로운 게시글 {len(new_posts)}개 발견 "
                    f"(마지막 시간: {last_naive.strftime('%Y-%m-%d %H:%M:%S')})"
                )
            return new_posts

        except Exception as e:
            logger.warning(f"datetime 기준 필터링 오류: {e}, URL 기준으로 폴백")
            return None

    def _filter_by_url(self, posts: List[Dict[str, Any]], last_url: str) -> List[Dict[str, Any]]:
        """URL 기준으로 새 게시글 필터링"""
        normalized_last = last_url.split('?')[0]
        new_posts = []
        found_last = False

        for post in posts:
            post_url = post.get('full_url') or post.get('url', '')
            if not post_url:
                continue
            normalized_post = post_url.split('?')[0]
            if normalized_post == normalized_last:
                found_last = True
                continue
            new_posts.append(post)

        if new_posts:
            logger.info(f"새로운 게시글 {len(new_posts)}개 발견 (마지막 URL: {normalized_last})")
        elif not found_last:
            logger.warning("마지막 게시글 URL을 찾을 수 없어 모든 게시글을 새로운 것으로 간주")
            return posts

        return new_posts

    def _filter_by_id(self, posts: List[Dict[str, Any]], last_id: str) -> Optional[List[Dict[str, Any]]]:
        """게시글 ID 기준으로 새 게시글 필터링"""
        try:
            last_id_int = int(last_id)
        except ValueError:
            logger.warning(f"마지막 게시글 ID 변환 오류: {last_id}")
            return None

        new_posts = []
        for post in posts:
            post_id = post.get('post_id', '')
            if post_id.isdigit():
                if int(post_id) > last_id_int:
                    new_posts.append(post)
                else:
                    break

        if new_posts:
            logger.info(f"새로운 게시글 {len(new_posts)}개 발견 (마지막 ID: {last_id_int})")
        return new_posts

    def _url_differs(self, post: Dict[str, Any], last_url: str) -> bool:
        """게시글 URL이 마지막 URL과 다른지 비교"""
        post_url = post.get('full_url') or post.get('url', '')
        if not post_url:
            return False
        return post_url.split('?')[0] != last_url.split('?')[0]

    async def save_posts(self, posts: List[Dict[str, Any]]) -> int:
        """모든 게시글을 DB에 저장 (URL 중복 자동 처리)"""
        saved_count = 0
        for post_data in posts:
            url = post_data.get('full_url') or post_data.get('url', '')
            if not url:
                continue
            hotdeal = Hotdeal(
                title=post_data.get('title', ''),
                price=post_data.get('price', ''),
                url=url,
                source=post_data.get('source', '')
            )
            if await self.db.add_hotdeal(hotdeal):
                saved_count += 1

        if saved_count > 0:
            logger.info(f"데이터베이스 저장 완료: {saved_count}개 새 게시글 저장됨")
        return saved_count

    async def send_keyword_notifications(
        self,
        new_posts: List[Dict[str, Any]],
        notification_service: NotificationService,
    ) -> int:
        """새 게시글에 대해 키워드 매칭 후 알림 전송"""
        if not new_posts:
            logger.debug("알림 전송할 새로운 게시글이 없습니다")
            return 0

        logger.debug(f"알림 전송 대상 게시글 수: {len(new_posts)}개")
        all_keywords = await self.db.get_all_keywords()
        notification_count = 0

        for post_data in new_posts:
            title = post_data.get('title', '')
            matched_keywords = self.crawler.check_keywords(title, all_keywords)

            if not matched_keywords:
                logger.debug(f"키워드 미매칭: '{title[:50]}'")
                continue

            # 매칭된 키워드를 가진 사용자 목록 수집
            matched_users = set()
            for keyword in matched_keywords:
                users = await self.db.get_users_by_keyword(keyword)
                matched_users.update(users)

            if not matched_users:
                continue

            logger.info(
                f"키워드 매칭: '{title[:50]}' - "
                f"키워드: {matched_keywords}, 알림 대상: {len(matched_users)}명"
            )

            for user_id in matched_users:
                success = await notification_service.send(user_id, post_data, matched_keywords)
                if success:
                    notification_count += 1
                else:
                    logger.warning(f"알림 전송 실패: 사용자 ID {user_id}")

        if notification_count > 0:
            logger.info(f"알림 전송 완료: {notification_count}개")
        return notification_count

    async def update_crawl_state(self, new_posts: List[Dict[str, Any]]) -> None:
        """마지막 게시글 정보를 DB에 업데이트"""
        if not new_posts:
            return

        latest = new_posts[0]
        post_id = latest.get('post_id', '')
        if not post_id:
            return

        post_url = latest.get('full_url') or latest.get('url', '')
        post_datetime = self._parse_post_datetime(latest.get('datetime', ''))

        await self.db.update_last_post_id(
            self.crawler.crawler_name, post_id, post_url, post_datetime
        )
        logger.debug(f"마지막 게시글 업데이트: ID={post_id}, 시간={post_datetime or 'N/A'}")

    def _parse_post_datetime(self, datetime_str: str) -> Optional[datetime]:
        """datetime 문자열을 timezone-naive datetime으로 파싱"""
        if not datetime_str:
            return None
        try:
            from dateutil import parser as date_parser
            parsed = date_parser.isoparse(datetime_str)
            if parsed.tzinfo is not None:
                return parsed.replace(tzinfo=None)
            return parsed
        except (ValueError, TypeError) as e:
            logger.debug(f"게시글 datetime 파싱 실패: {datetime_str}, {e}")
            return None

    async def run(self, notification_service: NotificationService) -> None:
        """크롤링 전체 프로세스 실행 (fetch → filter → save → notify → update)"""
        all_posts = await self.fetch_and_parse()
        if not all_posts:
            return

        new_posts = await self.filter_new_posts(all_posts)
        await self.save_posts(all_posts)
        await self.send_keyword_notifications(new_posts, notification_service)
        await self.update_crawl_state(new_posts)
