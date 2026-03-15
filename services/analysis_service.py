# -*- coding: utf-8 -*-
"""
AI 분석 서비스
3시간 후 재크롤링 → Claude AI 분석 → 2차 알림 전송
"""
import logging

from .ai_client import AIClient
from .notification_service import NotificationService

logger = logging.getLogger(__name__)


class AnalysisService:
    """AI 핫딜 분석 및 2차 알림을 담당하는 서비스"""

    def __init__(self, crawler, db, notification_service: NotificationService):
        self.crawler = crawler
        self.db = db
        self.notification_service = notification_service
        self.ai_client = AIClient()

    async def run(self) -> int:
        """
        scheduled_at이 지난 pending 분석 항목을 일괄 처리

        Returns:
            int: 처리 완료된 항목 수
        """
        due_list = await self.db.get_due_analyses()
        if not due_list:
            return 0

        logger.info(f"AI 분석 대기 항목: {len(due_list)}개")
        processed = 0

        for analysis in due_list:
            try:
                await self.db.update_analysis_status(analysis.id, 'processing')
                await self._process(analysis)
                await self.db.update_analysis_status(analysis.id, 'done')
                processed += 1
            except Exception as e:
                logger.error(f"분석 처리 오류 (id={analysis.id}): {e}", exc_info=True)
                await self.db.update_analysis_status(analysis.id, 'failed')

        if processed > 0:
            logger.info(f"AI 분석 완료: {processed}개")
        return processed

    async def _process(self, analysis) -> None:
        """개별 분석 항목 처리"""
        post_url = analysis.post_url
        post_title = analysis.post_title

        # 1. 개별 게시글 재크롤링 (댓글 + 추천수)
        detail = await self.crawler.fetch_post_detail(post_url)
        vote_count = detail.get('vote_count', 0)
        comment_count = detail.get('comment_count', 0)
        comments = detail.get('comments', [])

        logger.debug(
            f"게시글 상세 수집: '{post_title[:30]}' "
            f"추천={vote_count}, 댓글={comment_count}"
        )

        # 2. Claude AI 분석
        ai_result = await self.ai_client.analyze_hotdeal(
            title=post_title,
            price="",
            vote_count=vote_count,
            comment_count=comment_count,
            comments=comments,
        )

        # 3. 1차 알림 수신자 조회
        user_ids = await self.db.get_notified_users(post_url)
        if not user_ids:
            logger.debug(f"2차 알림 대상 없음: {post_url}")
            return

        # 4. 2차 알림 전송
        post_data = {
            'title': post_title,
            'full_url': post_url,
            'url': post_url,
            'vote_count': vote_count,
            'comment_count': comment_count,
        }

        for user_id in user_ids:
            await self.notification_service.send_analysis_result(
                user_id, post_data, ai_result
            )

        logger.info(
            f"2차 알림 전송 완료: '{post_title[:30]}' → {len(user_ids)}명 "
            f"(AI: {ai_result['recommendation'] if ai_result else 'N/A'})"
        )
