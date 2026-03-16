# -*- coding: utf-8 -*-
"""
Gemini AI 클라이언트
GEMINI_API_KEY_1,2,3 중 하나라도 설정되면 활성화됩니다.
여러 Key 설정 시 라운드로빈으로 부하를 분산합니다.
"""
import logging
from typing import Optional

from config.settings import Settings

logger = logging.getLogger(__name__)


class AIClient:
    """Google Gemini API 클라이언트 (라운드로빈 로드밸런싱)"""

    def __init__(self):
        self._keys = Settings.GEMINI_API_KEYS
        self.enabled = bool(self._keys)
        self._index = 0

        if self.enabled:
            logger.info(f"Gemini AI 클라이언트 초기화 — API Key {len(self._keys)}개 등록")
        else:
            logger.info("GEMINI_API_KEY 미설정 — AI 분석 기능 비활성화")

    def _next_key(self) -> str:
        """라운드로빈으로 다음 API Key 반환"""
        key = self._keys[self._index % len(self._keys)]
        self._index += 1
        return key

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

            api_key = self._next_key()
            client = genai.Client(api_key=api_key)

            comments_text = "\n".join(
                f"- {c}" for c in comments[:20]
            ) if comments else "댓글 없음"

            prompt = f"""당신은 커뮤니티 반응 분석가입니다.
제품에 대한 사전 지식은 사용하지 마세요. 오직 아래 댓글 반응과 추천수만을 근거로 판단해주세요.

[게시글 제목]
{title}

[반응 지표]
- 댓글수: {comment_count} (1순위 판단 기준)
- 추천수: {vote_count} (2순위 판단 기준)

[유저 댓글 (최근 {len(comments[:20])}개)]
{comments_text}

댓글의 전반적인 분위기(긍정/부정/중립 비율, 구매 후기, 가격 반응 등)를 1순위로, 추천수를 2순위로 참고하여 판단하세요.
아래 JSON 형식으로만 응답해주세요. 다른 텍스트는 포함하지 마세요.
{{"recommendation": "추천" 또는 "비추천", "reason": "5줄 이내의 판단 이유"}}"""

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
            # 429(사용량 제한)는 일시적 오류 — 상위로 던져서 재시도 대상으로 처리
            # 사용량은 태평양 표준시(PST) 자정 기준 리셋
            from google.genai.errors import ClientError
            if isinstance(e, ClientError) and e.status_code == 429:
                logger.warning(f"Gemini 사용량 제한 (429) — 재시도 예약: {e}")
                raise
            logger.error(f"AI 분석 오류: {e}", exc_info=True)
            return None
