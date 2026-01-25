# -*- coding: utf-8 -*-
"""
핫딜 크롤러 구현 (Arca Live)
"""
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re
import logging
from datetime import datetime
from .base import BaseCrawler

logger = logging.getLogger(__name__)


class HotdealCrawler(BaseCrawler):
    """Arca Live 핫딜 크롤러 클래스"""
    
    def __init__(self, url: str = None, db=None):
        """
        Args:
            url: 크롤링할 URL (기본값: Arca Live 핫딜 게시판)
            db: Database 인스턴스 (마지막 게시글 ID 저장용)
        """
        super().__init__("ArcaLiveHotdealCrawler")
        self.url = url or "https://arca.live/b/hotdeal"
        self.db = db
        self.crawler_name = "arca_live_hotdeal"
        self.base_url = "https://arca.live"
    
    async def fetch(self, max_retries: int = 3) -> str:
        """
        웹 페이지를 가져오는 메서드 (재시도 로직 포함)
        
        Args:
            max_retries: 최대 재시도 횟수 (기본값: 3)
        
        Returns:
            str: HTML 데이터
        """
        import asyncio
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(self.url, timeout=timeout) as response:
                        if response.status == 200:
                            html = await response.text()
                            if attempt > 0:
                                self.logger.info(f"요청 성공 (재시도 {attempt}회 후)")
                            return html
                        else:
                            self.logger.warning(f"HTTP 오류: {response.status} (시도 {attempt + 1}/{max_retries})")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 ** attempt)  # 지수 백오프
                                continue
                            return ""
            except asyncio.TimeoutError:
                self.logger.warning(f"타임아웃 오류 (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 지수 백오프
                    continue
                else:
                    self.logger.error("타임아웃 오류: 최대 재시도 횟수 초과")
                    return ""
            except aiohttp.ClientError as e:
                self.logger.warning(f"요청 오류: {e} (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 지수 백오프
                    continue
                else:
                    self.logger.error(f"요청 오류: 최대 재시도 횟수 초과 - {e}")
                    return ""
            except Exception as e:
                self.logger.error(f"예상치 못한 오류: {e} (시도 {attempt + 1}/{max_retries})", exc_info=True)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 지수 백오프
                    continue
                else:
                    return ""
        
        return ""
    
    def _extract_number(self, text: str) -> Optional[int]:
        """
        텍스트에서 숫자만 추출
        
        Args:
            text: 숫자가 포함된 텍스트
            
        Returns:
            Optional[int]: 추출된 숫자 또는 None
        """
        if not text:
            return None
        # 쉼표와 공백 제거 후 숫자만 추출
        numbers = re.findall(r'\d+', text.replace(',', ''))
        if numbers:
            try:
                return int(''.join(numbers))
            except ValueError:
                return None
        return None
    
    def _extract_price_numeric(self, price_text: str) -> Optional[int]:
        """
        가격 텍스트에서 숫자만 추출
        
        Args:
            price_text: 가격 텍스트 (예: "24,900원", "$209.99")
            
        Returns:
            Optional[int]: 숫자 값 또는 None
        """
        if not price_text:
            return None
        # 쉼표, 공백, 통화 기호 제거
        cleaned = re.sub(r'[^\d]', '', price_text.replace(',', ''))
        if cleaned:
            try:
                return int(cleaned)
            except ValueError:
                return None
        return None
    
    def _extract_comments_count(self, comment_text: str) -> Optional[int]:
        """
        댓글수 텍스트에서 숫자만 추출
        
        Args:
            comment_text: 댓글수 텍스트 (예: "[16]", "16")
            
        Returns:
            Optional[int]: 댓글수 또는 None
        """
        if not comment_text:
            return None
        # 대괄호와 공백 제거 후 숫자 추출
        numbers = re.findall(r'\d+', comment_text)
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                return None
        return None
    
    def _get_full_url(self, url: str) -> str:
        """
        상대 경로를 절대 경로로 변환
        
        Args:
            url: 상대 또는 절대 URL
            
        Returns:
            str: 절대 URL
        """
        if not url:
            return ""
        if url.startswith('http://') or url.startswith('https://'):
            return url
        return urljoin(self.base_url, url)
    
    def parse(self, data: str) -> List[Dict[str, Any]]:
        """
        HTML 데이터를 파싱하는 메서드
        
        Args:
            data: 파싱할 HTML 데이터
            
        Returns:
            List[Dict[str, Any]]: 파싱된 게시글 리스트
        """
        if not data:
            return []
        
        try:
            soup = BeautifulSoup(data, 'html.parser')
            posts = []
            
            # 핫딜 게시글 추출 (공지사항 제외)
            # div.vrow.hybrid만 선택하여 공지사항(a.vrow.column.notice) 자동 제외
            articles = soup.select('div.list-table.hybrid > div.vrow.hybrid')
            
            # 대체 셀렉터 시도 (HTML 구조가 변경되었을 수 있음)
            if len(articles) == 0:
                self.logger.warning("기본 셀렉터로 게시글을 찾지 못했습니다. 대체 셀렉터 시도 중...")
                # 다양한 대체 셀렉터 시도
                alt_selectors = [
                    'div.vrow.hybrid',
                    '.vrow.hybrid',
                    'div[class*="vrow"]',
                    'article',
                ]
                for selector in alt_selectors:
                    articles = soup.select(selector)
                    if len(articles) > 0:
                        self.logger.warning(f"대체 셀렉터 '{selector}'로 {len(articles)}개 게시글 발견")
                        break
            
            for article in articles:
                try:
                    post_data = {}
                    
                    # 게시글 번호 추출
                    col_id = article.select_one('.vrow-top .col-id span')
                    if not col_id:
                        # 대체 방법 시도
                        col_id = article.select_one('.col-id span')
                    if not col_id:
                        col_id = article.select_one('.col-id')
                    if not col_id:
                        # 링크에서 게시글 ID 추출 시도
                        title_link = article.select_one('a[href*="/b/hotdeal/"]')
                        if title_link:
                            href = title_link.get('href', '')
                            # /b/hotdeal/123456 형식에서 ID 추출
                            match = re.search(r'/b/hotdeal/(\d+)', href)
                            if match:
                                post_data['post_id'] = match.group(1)
                            else:
                                self.logger.warning(f"게시글 ID를 추출할 수 없습니다. href: {href}")
                                continue
                        else:
                            self.logger.warning("게시글 ID를 찾을 수 없어 스킵합니다")
                            continue
                    else:
                        post_data['post_id'] = col_id.get_text(strip=True)
                    
                    # 판매처 추출
                    deal_store = article.select_one('.deal-store')
                    post_data['store'] = deal_store.get_text(strip=True) if deal_store else ""
                    
                    # 카테고리 추출
                    badge = article.select_one('.badges .badge')
                    post_data['category'] = badge.get_text(strip=True) if badge else ""
                    
                    # 제목 및 링크 추출
                    title_elem = article.select_one('.hybrid-title')
                    if not title_elem:
                        # 대체 방법: a 태그 직접 찾기
                        title_elem = article.select_one('a.hybrid-title')
                    if not title_elem:
                        # 또 다른 대체 방법: 제목이 있는 a 태그 찾기
                        title_elem = article.select_one('a[href*="/b/hotdeal/"]')
                    
                    if title_elem:
                        # 제목 텍스트 (댓글수 아이콘 제외)
                        title_text = title_elem.get_text(strip=True)
                        # 댓글수 아이콘 텍스트 제거
                        comment_icon = title_elem.select_one('.comment-count')
                        if comment_icon:
                            comment_text = comment_icon.get_text(strip=True)
                            title_text = title_text.replace(comment_text, '').strip()
                        post_data['title'] = title_text
                        
                        # 링크 추출 (a 태그인 경우 href, 아니면 부모의 a 태그 찾기)
                        href = title_elem.get('href', '')
                        if not href and title_elem.name != 'a':
                            # 부모나 자식에서 a 태그 찾기
                            parent_a = title_elem.find_parent('a')
                            if parent_a:
                                href = parent_a.get('href', '')
                            else:
                                child_a = title_elem.find('a')
                                if child_a:
                                    href = child_a.get('href', '')
                        
                        post_data['url'] = href
                        post_data['full_url'] = self._get_full_url(href)
                    else:
                        self.logger.warning(f"게시글 ID {post_data.get('post_id', 'unknown')}의 제목/링크를 찾을 수 없습니다")
                        post_data['title'] = ""
                        post_data['url'] = ""
                        post_data['full_url'] = ""
                    
                    # 가격 추출
                    deal_price = article.select_one('.deal-price')
                    if deal_price:
                        price_text = deal_price.get_text(strip=True)
                        post_data['price'] = price_text
                        post_data['price_numeric'] = self._extract_price_numeric(price_text)
                    else:
                        post_data['price'] = ""
                        post_data['price_numeric'] = None
                    
                    # 배송비 추출
                    deal_delivery = article.select_one('.deal-delivery')
                    post_data['delivery'] = deal_delivery.get_text(strip=True) if deal_delivery else ""
                    
                    # 작성자 추출
                    author_elem = article.select_one('.col-author span[data-filter]')
                    if author_elem:
                        post_data['author'] = author_elem.get_text(strip=True)
                    else:
                        # data-filter 속성이 없으면 다른 방법 시도
                        author_elem = article.select_one('.col-author .user-info span')
                        post_data['author'] = author_elem.get_text(strip=True) if author_elem else ""
                    
                    # 작성시간 추출
                    time_elem = article.select_one('.col-time time[datetime]')
                    if time_elem:
                        datetime_attr = time_elem.get('datetime', '')
                        post_data['datetime'] = datetime_attr
                        # 표시 시간 텍스트도 추출
                        post_data['datetime_display'] = time_elem.get_text(strip=True)
                    else:
                        post_data['datetime'] = ""
                        post_data['datetime_display'] = ""
                    
                    # 조회수 추출
                    col_view = article.select_one('.col-view')
                    if col_view:
                        view_text = col_view.get_text(strip=True)
                        post_data['views'] = view_text
                        post_data['views_numeric'] = self._extract_number(view_text)
                    else:
                        post_data['views'] = ""
                        post_data['views_numeric'] = None
                    
                    # 추천수 추출
                    col_rate = article.select_one('.col-rate')
                    if col_rate:
                        rate_text = col_rate.get_text(strip=True)
                        post_data['rate'] = rate_text
                        post_data['rate_numeric'] = self._extract_number(rate_text)
                    else:
                        post_data['rate'] = ""
                        post_data['rate_numeric'] = None
                    
                    # 댓글수 추출
                    comment_count = article.select_one('.comment-count')
                    if comment_count:
                        comment_text = comment_count.get_text(strip=True)
                        post_data['comments'] = comment_text
                        post_data['comments_numeric'] = self._extract_comments_count(comment_text)
                    else:
                        post_data['comments'] = ""
                        post_data['comments_numeric'] = None
                    
                    # 썸네일 이미지 추출
                    thumbnail_img = article.select_one('.vrow-preview img[src]')
                    if thumbnail_img:
                        img_src = thumbnail_img.get('src', '')
                        post_data['thumbnail'] = self._get_full_url(img_src)
                    else:
                        post_data['thumbnail'] = ""
                    
                    # 초핫딜 여부 (불꽃 아이콘)
                    fire_icon = article.select_one('img[src*="deal_channel_fire"]')
                    post_data['is_hot'] = fire_icon is not None
                    
                    # 종료 여부
                    deal_close = article.select_one('.deal-close')
                    post_data['is_closed'] = deal_close is not None
                    
                    # 이미지 포함 여부
                    media_icon = article.select_one('.media-icon.ion-ios-photos-outline')
                    post_data['has_image'] = media_icon is not None
                    
                    # 출처 추가
                    post_data['source'] = "Arca Live"
                    
                    # 필수 필드 검증
                    if not post_data.get('post_id'):
                        self.logger.warning("게시글 ID가 없어 스킵합니다")
                        continue
                    if not post_data.get('title') and not post_data.get('url'):
                        self.logger.warning(f"게시글 ID {post_data.get('post_id')}의 제목과 URL이 모두 없어 스킵합니다")
                        continue
                    
                    posts.append(post_data)
                    
                except Exception as e:
                    self.logger.warning(f"게시글 파싱 오류: {e}", exc_info=True)
                    continue
            
            # 게시글 ID 기준으로 정렬 (최신순, 숫자로 변환하여 정렬)
            try:
                posts.sort(key=lambda x: int(x.get('post_id', 0)) if x.get('post_id', '').isdigit() else 0, reverse=True)
            except Exception as e:
                self.logger.warning(f"정렬 오류: {e}")
            
            self.logger.debug(f"파싱 완료: 총 {len(posts)}개 게시글 추출 성공")
            
            return posts
            
        except Exception as e:
            self.logger.error(f"파싱 오류: {e}", exc_info=True)
            return []
    
    async def crawl(self) -> List[Dict[str, Any]]:
        """
        크롤링 실행 메서드 (새로운 글만 필터링)
        
        Returns:
            List[Dict[str, Any]]: 새로운 게시글 리스트
        """
        try:
            # HTML 가져오기
            html_data = await self.fetch()
            if not html_data:
                return []
            
            # 파싱
            all_posts = self.parse(html_data)
            if not all_posts:
                return []
            
            # 마지막 게시글 ID 가져오기
            last_post_id = None
            if self.db:
                last_post_id = await self.db.get_last_post_id(self.crawler_name)
                self.logger.info(f"마지막 게시글 ID: {last_post_id}")
            else:
                self.logger.warning("데이터베이스가 설정되지 않아 마지막 게시글 ID를 가져올 수 없습니다")
            
            # 새로운 게시글만 필터링
            new_posts = []
            if last_post_id:
                try:
                    last_id_int = int(last_post_id)
                    self.logger.info(f"마지막 ID ({last_id_int})보다 큰 게시글 필터링 중...")
                    # 처음 몇 개 게시글 ID 로깅 (디버깅용)
                    if all_posts:
                        top_ids = [p.get('post_id', 'N/A') for p in all_posts[:5]]
                        self.logger.info(f"크롤링된 상위 5개 게시글 ID: {top_ids}")
                    
                    for post in all_posts:
                        post_id = post.get('post_id', '')
                        if post_id.isdigit():
                            post_id_int = int(post_id)
                            if post_id_int > last_id_int:
                                new_posts.append(post)
                                self.logger.debug(f"새 게시글 발견: ID {post_id_int}, 제목: {post.get('title', '')[:50]}")
                            elif post_id_int == last_id_int:
                                # 같은 ID는 이미 처리된 게시글이므로 중단
                                self.logger.info(f"게시글 ID {post_id_int}는 마지막 ID와 같아 필터링 중단 (이미 처리된 게시글)")
                                break
                            else:
                                # 게시글이 ID 순서대로 정렬되어 있으므로, 더 이상 새로운 게시글이 없음
                                self.logger.info(f"게시글 ID {post_id_int}는 마지막 ID {last_id_int}보다 작아 필터링 중단")
                                break
                        else:
                            self.logger.warning(f"게시글 ID가 숫자가 아닙니다: {post_id}")
                    self.logger.info(f"필터링 결과: {len(new_posts)}개 새로운 게시글 발견")
                except ValueError as e:
                    # last_post_id가 숫자가 아니면 모든 게시글을 새로운 것으로 간주
                    self.logger.warning(f"마지막 ID 변환 오류: {e}, 최신 5개만 반환")
                    new_posts = all_posts[:5]
            else:
                # 첫 크롤링이거나 마지막 ID가 없으면 최신 5개만 반환 (너무 많은 알림 방지)
                self.logger.info("첫 크롤링이거나 마지막 ID가 없어 최신 5개만 반환")
                new_posts = all_posts[:5]
            
            # 마지막 게시글 ID 업데이트
            if new_posts and self.db:
                latest_post_id = new_posts[0].get('post_id', '')
                if latest_post_id:
                    await self.db.update_last_post_id(self.crawler_name, latest_post_id)
                    self.logger.info(f"마지막 게시글 ID 업데이트: {latest_post_id}")
                else:
                    self.logger.warning("새로운 게시글이 있지만 ID가 없어 업데이트하지 않습니다")
            
            return new_posts
            
        except Exception as e:
            self.logger.error(f"{self.name} 크롤링 오류: {e}", exc_info=True)
            return []
    
    def check_keywords(self, title: str, keywords: List[str]) -> List[str]:
        """
        제목에 키워드가 포함되어 있는지 검사
        '*' 키워드는 와일드카드로 처리하여 모든 게시글에 매칭됩니다.
        
        Args:
            title: 게시글 제목
            keywords: 검색할 키워드 리스트
            
        Returns:
            List[str]: 매칭된 키워드 리스트
        """
        matched_keywords = []
        title_lower = title.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            
            # 와일드카드 '*' 처리: 모든 게시글에 매칭
            if keyword_lower == '*':
                matched_keywords.append(keyword)
                continue
            
            # 일반 키워드 매칭: 제목에 키워드가 포함되어 있는지 검사
            if keyword_lower and keyword_lower in title_lower:
                matched_keywords.append(keyword)
        
        return matched_keywords
    
    async def crawl_with_keyword_check(self, db) -> List[Dict[str, Any]]:
        """
        키워드 검사를 포함한 크롤링 실행
        
        Args:
            db: Database 인스턴스
            
        Returns:
            List[Dict[str, Any]]: 키워드가 매칭된 새로운 게시글 리스트 (matched_keywords 필드 포함)
        """
        # 크롤링 실행
        new_posts = await self.crawl()
        
        if not new_posts:
            return []
        
        # 모든 키워드 가져오기
        all_keywords = await db.get_all_keywords()
        
        # 각 게시글에 대해 키워드 매칭
        matched_posts = []
        for post in new_posts:
            matched_keywords = self.check_keywords(post.get('title', ''), all_keywords)
            if matched_keywords:
                post['matched_keywords'] = matched_keywords
                # 키워드를 가진 사용자 ID 목록 가져오기
                matched_users = []
                for keyword in matched_keywords:
                    users = await db.get_users_by_keyword(keyword)
                    matched_users.extend(users)
                # 중복 제거
                post['matched_user_ids'] = list(set(matched_users))
                matched_posts.append(post)
        
        return matched_posts
