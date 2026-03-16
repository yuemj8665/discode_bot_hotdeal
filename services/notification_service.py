# -*- coding: utf-8 -*-
"""
알림 전송 서비스
"""
import discord
from discord.ext import commands
import logging
from typing import List

logger = logging.getLogger(__name__)


class NotificationService:
    """Discord 알림 전송을 담당하는 서비스"""

    def __init__(self, bot: commands.Bot, db):
        self.bot = bot
        self.db = db

    def _build_post_url(self, post_data: dict) -> str:
        """게시글 URL을 절대 경로로 변환"""
        url = post_data.get('full_url') or post_data.get('url', '')
        if url and not url.startswith(('http://', 'https://')):
            if url.startswith('/'):
                url = f"https://arca.live{url}"
            else:
                url = f"https://arca.live/{url}"
        return url

    def _build_embed(
        self,
        post_data: dict,
        matched_keywords: List[str],
        post_url: str,
        matched_categories: List[str] = None,
    ) -> discord.Embed:
        """알림용 Embed 생성"""
        embed = discord.Embed(
            title="🔔 핫딜 알림",
            description=f"**{post_data['title']}**",
            color=0xFF0000,
            url=post_url if post_url.startswith(('http://', 'https://')) else None
        )
        if matched_keywords:
            embed.add_field(
                name="매칭된 키워드",
                value=", ".join(matched_keywords),
                inline=False
            )
        if matched_categories:
            embed.add_field(
                name="매칭된 카테고리",
                value=", ".join(matched_categories),
                inline=False
            )
        embed.add_field(
            name="링크",
            value=post_url or 'N/A',
            inline=False
        )
        if post_data.get('price'):
            embed.add_field(
                name="가격",
                value=post_data['price'],
                inline=True
            )
        if post_data.get('category'):
            embed.add_field(
                name="카테고리",
                value=post_data['category'],
                inline=True
            )
        embed.set_footer(text=f"출처: {post_data.get('source', 'Arca Live')}")
        return embed

    async def _find_user(self, user_id: int) -> discord.User | None:
        """다양한 방법으로 Discord 사용자를 찾기"""
        # 1. 캐시에서 찾기
        user = self.bot.get_user(user_id)
        if user:
            return user

        # 2. 서버 멤버 캐시에서 찾기
        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member:
                logger.debug(f"사용자 ID {user_id}를 서버 '{guild.name}'에서 찾음 (캐시)")
                return member

        # 3. API에서 가져오기
        try:
            user = await self.bot.fetch_user(user_id)
            logger.debug(f"사용자 ID {user_id}를 API에서 가져옴: {user.name}")
            return user
        except discord.NotFound:
            pass

        # 4. 서버 멤버 API에서 가져오기
        for guild in self.bot.guilds:
            try:
                member = await guild.fetch_member(user_id)
                if member:
                    logger.debug(f"사용자 ID {user_id}를 서버 '{guild.name}'에서 API로 가져옴")
                    return member
            except (discord.NotFound, discord.Forbidden):
                continue

        return None

    async def _send_via_channel(
        self,
        user_id: int,
        embed: discord.Embed,
        post_data: dict,
        matched_keywords: List[str],
        matched_categories: List[str] = None,
    ) -> bool:
        """DM 실패 시 채널로 알림 전송"""
        post_url = self._build_post_url(post_data)

        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if not member:
                continue

            channel = await self._find_notification_channel(guild)
            if not channel:
                continue

            try:
                message = f"{member.mention} 🔔 핫딜 알림!\n"
                if matched_keywords:
                    message += f"**매칭된 키워드:** {', '.join(matched_keywords)}\n"
                if matched_categories:
                    message += f"**매칭된 카테고리:** {', '.join(matched_categories)}\n"
                message += f"**제목:** {post_data['title']}\n"
                message += f"**링크:** {post_url or 'N/A'}"
                await channel.send(message, embed=embed)
                logger.debug(f"채널 알림 전송 성공: 사용자 {member.name} ({user_id}), 채널: {channel.name}")
                return True
            except discord.Forbidden:
                logger.warning(f"채널 알림 전송 실패 (권한 없음): 채널 {channel.name} ({channel.id})")
                continue

        return False

    async def _find_notification_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """서버의 알림 채널 찾기"""
        channel_id = await self.db.get_notification_channel(guild.id)
        if channel_id:
            return guild.get_channel(channel_id)

        channel = discord.utils.get(guild.text_channels, name='general')
        if channel:
            return channel

        channels = [ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages]
        return channels[0] if channels else None

    async def send(
        self,
        user_id: int,
        post_data: dict,
        matched_keywords: List[str],
        matched_categories: List[str] = None,
    ) -> bool:
        """
        사용자에게 알림 전송 (DM 우선, 실패 시 채널 폴백)

        Args:
            user_id: Discord 사용자 ID
            post_data: 게시글 데이터
            matched_keywords: 매칭된 키워드 리스트
            matched_categories: 매칭된 카테고리 리스트

        Returns:
            bool: 알림 전송 성공 여부
        """
        try:
            user = await self._find_user(user_id)
            if not user:
                logger.warning(f"사용자 ID {user_id}를 찾을 수 없어 알림을 전송할 수 없습니다 (모든 방법 시도 실패)")
                return False

            post_url = self._build_post_url(post_data)
            embed = self._build_embed(post_data, matched_keywords, post_url, matched_categories)

            # DM 시도
            try:
                await user.send(embed=embed)
                logger.debug(f"DM 전송 성공: 사용자 {user.name} ({user_id})")
                return True
            except discord.Forbidden:
                logger.debug(f"DM 전송 실패 (차단됨): 사용자 {user.name} ({user_id}), 채널로 전송 시도")

            # DM 실패 시 채널로 폴백
            if await self._send_via_channel(user_id, embed, post_data, matched_keywords, matched_categories):
                return True

            logger.warning(f"사용자 ID {user_id}에게 알림을 전송할 수 있는 방법이 없습니다")
            return False

        except Exception as e:
            logger.error(f"알림 전송 중 오류 발생: 사용자 ID {user_id}, 오류: {e}", exc_info=True)
            return False

    async def send_analysis_result(
        self,
        user_id: int,
        post_data: dict,
        ai_result: dict,
    ) -> bool:
        """
        AI 분석 결과 2차 알림 전송

        Args:
            user_id: Discord 사용자 ID
            post_data: 게시글 데이터 (title, url, vote_count, comment_count)
            ai_result: AI 분석 결과 {"recommendation": ..., "reason": ...}
                       None이면 통계 정보만 전송

        Returns:
            bool: 전송 성공 여부
        """
        try:
            user = await self._find_user(user_id)
            if not user:
                return False

            post_url = self._build_post_url(post_data)
            embed = self._build_analysis_embed(post_data, ai_result, post_url)

            try:
                await user.send(embed=embed)
                logger.debug(f"AI 분석 2차 알림 DM 전송: 사용자 {user_id}")
                return True
            except discord.Forbidden:
                pass

            # 채널 폴백
            for guild in self.bot.guilds:
                member = guild.get_member(user_id)
                if not member:
                    continue
                channel = await self._find_notification_channel(guild)
                if not channel:
                    continue
                try:
                    await channel.send(f"{member.mention}", embed=embed)
                    return True
                except discord.Forbidden:
                    continue

            return False

        except Exception as e:
            logger.error(f"AI 분석 알림 전송 오류: 사용자 ID {user_id}, {e}", exc_info=True)
            return False

    async def send_deleted_post_notice(
        self,
        user_id: int,
        post_data: dict,
    ) -> bool:
        """
        게시글 삭제 알림 전송

        Args:
            user_id: Discord 사용자 ID
            post_data: 게시글 데이터 (title, full_url)

        Returns:
            bool: 전송 성공 여부
        """
        try:
            user = await self._find_user(user_id)
            if not user:
                return False

            post_url = self._build_post_url(post_data)
            embed = discord.Embed(
                title="🗑️ 게시글 삭제됨",
                description=f"**{post_data.get('title', '')}**",
                color=0x888888,
                url=post_url if post_url.startswith(('http://', 'https://')) else None,
            )
            embed.add_field(name="링크", value=post_url or 'N/A', inline=False)
            embed.set_footer(text="해당 게시글이 삭제되어 AI 분석을 진행할 수 없습니다.")

            try:
                await user.send(embed=embed)
                logger.debug(f"삭제 알림 DM 전송: 사용자 {user_id}")
                return True
            except discord.Forbidden:
                pass

            for guild in self.bot.guilds:
                member = guild.get_member(user_id)
                if not member:
                    continue
                channel = await self._find_notification_channel(guild)
                if not channel:
                    continue
                try:
                    await channel.send(f"{member.mention}", embed=embed)
                    return True
                except discord.Forbidden:
                    continue

            return False

        except Exception as e:
            logger.error(f"삭제 알림 전송 오류: 사용자 ID {user_id}, {e}", exc_info=True)
            return False

    def _build_analysis_embed(
        self, post_data: dict, ai_result: dict, post_url: str
    ) -> discord.Embed:
        """AI 분석 결과 Embed 생성"""
        if ai_result:
            recommendation = ai_result.get('recommendation', '')
            is_positive = recommendation == '추천'
            color = 0x00C851 if is_positive else 0xFF4444
            icon = '✅' if is_positive else '❌'
            title = f"🤖 AI 분석 결과 — {icon} {recommendation}"
        else:
            color = 0x999999
            title = "🤖 AI 분석 결과 — 분석 불가"

        embed = discord.Embed(
            title=title,
            description=f"**{post_data.get('title', '')}**",
            color=color,
            url=post_url if post_url.startswith(('http://', 'https://')) else None,
        )

        if ai_result:
            embed.add_field(
                name="AI 판단 이유",
                value=ai_result.get('reason', '-'),
                inline=False,
            )

        embed.add_field(
            name="추천수",
            value=str(post_data.get('vote_count', 0)),
            inline=True,
        )
        embed.add_field(
            name="댓글수",
            value=str(post_data.get('comment_count', 0)),
            inline=True,
        )
        embed.add_field(name="링크", value=post_url or 'N/A', inline=False)
        embed.set_footer(text="1차 알림 후 3시간 뒤 분석 결과입니다.")
        return embed
