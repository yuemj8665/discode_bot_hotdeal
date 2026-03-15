# -*- coding: utf-8 -*-
"""
카테고리 구독 관리 명령어
"""
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

# Arca Live 핫딜 유효 카테고리 (사이트 기준)
VALID_CATEGORIES = [
    "식품",
    "생활용품",
    "전자제품",
    "PC/하드웨어",
    "SW/게임",
    "의류",
    "화장품",
    "상품권/쿠폰",
    "임박",
    "응모",
    "기타",
]


class CategoryCommands(commands.Cog):
    """카테고리 구독 관리 명령어 클래스"""

    def __init__(self, bot: commands.Bot, db):
        self.bot = bot
        self.db = db

    @commands.group(name='카테고리', invoke_without_command=True)
    async def category_group(self, ctx: commands.Context):
        """카테고리 관리 명령어 그룹"""
        logger.info(f"명령어 호출: !카테고리 - 사용자: {ctx.author.name} ({ctx.author.id})")
        category_list = "\n".join(f"• {c}" for c in VALID_CATEGORIES)
        embed = discord.Embed(
            title="카테고리 명령어 사용법",
            description=(
                "`!카테고리 추가 [카테고리명]`\n"
                "`!카테고리 삭제 [카테고리명]`\n"
                "`!카테고리 목록`\n\n"
                f"**사용 가능한 카테고리:**\n{category_list}"
            ),
            color=0x5865F2
        )
        await ctx.send(embed=embed)

    @category_group.command(name='추가')
    async def add_category(self, ctx: commands.Context, *, category: str = None):
        """
        카테고리 구독 추가

        사용법: !카테고리 추가 [카테고리명]
        """
        if not category:
            await ctx.send("❌ 사용법: `!카테고리 추가 [카테고리명]`\n예: `!카테고리 추가 식품`")
            return

        category = category.strip()
        if category not in VALID_CATEGORIES:
            category_list = ", ".join(VALID_CATEGORIES)
            await ctx.send(
                f"❌ 유효하지 않은 카테고리입니다.\n"
                f"사용 가능한 카테고리: {category_list}"
            )
            return

        try:
            user_id = ctx.author.id
            logger.info(f"명령어 호출: !카테고리 추가 '{category}' - 사용자: {ctx.author.name} ({user_id})")
            success = await self.db.add_category(user_id, category)

            if success:
                embed = discord.Embed(
                    title="✅ 카테고리 구독 추가 완료",
                    description=f"**{category}** 카테고리 알림이 등록되었습니다.",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="⚠️ 카테고리 중복",
                    description=f"**{category}** 카테고리는 이미 등록되어 있습니다.",
                    color=0xffaa00
                )
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"카테고리 추가 오류 (사용자 {ctx.author.id}): {e}", exc_info=True)
            await ctx.send(f"❌ 카테고리 추가 중 오류가 발생했습니다: {e}")

    @category_group.command(name='삭제')
    async def delete_category(self, ctx: commands.Context, *, category: str = None):
        """
        카테고리 구독 삭제

        사용법: !카테고리 삭제 [카테고리명]
        """
        if not category:
            await ctx.send("❌ 사용법: `!카테고리 삭제 [카테고리명]`\n예: `!카테고리 삭제 식품`")
            return

        category = category.strip()
        try:
            user_id = ctx.author.id
            logger.info(f"명령어 호출: !카테고리 삭제 '{category}' - 사용자: {ctx.author.name} ({user_id})")
            success = await self.db.delete_category(user_id, category)

            if success:
                embed = discord.Embed(
                    title="✅ 카테고리 구독 삭제 완료",
                    description=f"**{category}** 카테고리 알림이 삭제되었습니다.",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="⚠️ 카테고리 없음",
                    description=f"**{category}** 카테고리를 구독하고 있지 않습니다.",
                    color=0xffaa00
                )
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"카테고리 삭제 오류 (사용자 {ctx.author.id}): {e}", exc_info=True)
            await ctx.send(f"❌ 카테고리 삭제 중 오류가 발생했습니다: {e}")

    @category_group.command(name='목록')
    async def list_categories(self, ctx: commands.Context):
        """
        카테고리 구독 목록 조회

        사용법: !카테고리 목록
        """
        try:
            user_id = ctx.author.id
            logger.info(f"명령어 호출: !카테고리 목록 - 사용자: {ctx.author.name} ({user_id})")
            categories = await self.db.get_categories(user_id)

            if not categories:
                embed = discord.Embed(
                    title="📋 구독 중인 카테고리",
                    description=(
                        "구독 중인 카테고리가 없습니다.\n"
                        "`!카테고리 추가 [카테고리명]`으로 추가하세요."
                    ),
                    color=0x5865F2
                )
            else:
                category_text = "\n".join(f"• {c.category}" for c in categories)
                embed = discord.Embed(
                    title="📋 구독 중인 카테고리",
                    description=category_text,
                    color=0x5865F2
                )
                embed.set_footer(text=f"총 {len(categories)}개의 카테고리")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"카테고리 목록 조회 오류 (사용자 {ctx.author.id}): {e}", exc_info=True)
            await ctx.send(f"❌ 카테고리 목록 조회 중 오류가 발생했습니다: {e}")


async def setup(bot: commands.Bot, db):
    """Cog 등록 함수"""
    await bot.add_cog(CategoryCommands(bot, db))
