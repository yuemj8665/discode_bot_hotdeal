# -*- coding: utf-8 -*-
"""
Gemini AI 클라이언트
GEMINI_API_KEY가 설정되지 않으면 전체 기능이 비활성화됩니다.
"""
import logging
from typing import Optional

from config.settings import Settings

logger = logging.getLogger(__name__)


class AIClient:
    """Google Gemini API 클라이언트 (API Key 없으면 비활성화)"""

    def __init__(self):
        self.enabled = bool(Settings.GEMINI_API_KEY)
        if not self.enabled:
            logger.info("GEMINI_API_KEY 미설정 — AI 분석 기능 비활성화")

    async def analyze_hotdeal(
        self,
        title: str,
        price: str,
        vote_count: int,
        comment_count: int,
        comments: list,
    ) -> Optional[dict]:
        """
        핫딜 정보와 유저 반응을 분석하여 추천/비추천 판단

        Args:
            title: 게시글 제목
            price: 가격
            vote_count: 추천수
            comment_count: 댓글 수
            comments: 댓글 목록

        Returns:
            dict: {"recommendation": "추천"/"비추천", "reason": "이유"}
            None: API Key 미설정 또는 오류
        """
        if not self.enabled:
            return None

        try:
            from google import genai
            import json

            client = genai.Client(api_key=Settings.GEMINI_API_KEY)

            comments_text = "\n".join(
                f"- {c}" for c in comments[:20]
            ) if comments else "댓글 없음"

            prompt = f"""당신은 온라인 핫딜 전문가입니다.
아래 핫딜 정보와 유저들의 반응을 분석하여 이 핫딜이 살만한지 판단해주세요.

[핫딜 정보]
- 제목: {title}
- 가격: {price or '정보 없음'}
- 추천수: {vote_count}
- 댓글수: {comment_count}

[유저 댓글 (최근 {len(comments[:20])}개)]
{comments_text}

위 정보를 바탕으로 아래 JSON 형식으로만 응답해주세요. 다른 텍스트는 포함하지 마세요.
{{"recommendation": "추천" 또는 "비추천", "reason": "3줄 이내의 판단 이유"}}"""

            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            content = response.text.strip()
            # JSON 코드블록 제거 (```json ... ``` 형태 대응)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)
            if "recommendation" in result and "reason" in result:
                return result

            logger.warning(f"AI 응답 형식 불일치: {content}")
            return None

        except ImportError:
            logger.error("google-genai 패키지가 설치되지 않았습니다. pip install google-genai")
            return None
        except Exception as e:
            logger.error(f"AI 분석 오류: {e}", exc_info=True)
            return None
