# -*- coding: utf-8 -*-
"""
키워드 관리 명령어
"""
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


class KeywordCommands(commands.Cog):
    """키워드 관리 명령어 클래스"""
    
    def __init__(self, bot: commands.Bot, db):
        """
        Args:
            bot: Discord 봇 인스턴스
            db: Database 인스턴스
        """
        self.bot = bot
        self.db = db
    
    @commands.group(name='키워드', invoke_without_command=True)
    async def keyword_group(self, ctx: commands.Context):
        """키워드 관리 명령어 그룹"""
        logger.info(f"명령어 호출: !키워드 - 사용자: {ctx.author.name} ({ctx.author.id})")
        await ctx.send("사용법: `!키워드 추가 [단어]`, `!키워드 삭제 [단어]`, `!키워드 목록`")
    
    @keyword_group.command(name='추가')
    async def add_keyword(self, ctx: commands.Context, *, keyword: str = None):
        """
        키워드 추가 명령어
        
        사용법: !키워드 추가 [단어]
        """
        if not keyword:
            await ctx.send("❌ 사용법: `!키워드 추가 [단어]`\n예: `!키워드 추가 노트북`")
            return
        
        keyword = keyword.strip()
        if not keyword:
            await ctx.send("❌ 키워드를 입력해주세요.")
            return
        
        try:
            user_id = ctx.author.id
            logger.info(f"명령어 호출: !키워드 추가 '{keyword}' - 사용자: {ctx.author.name} ({user_id})")
            success = await self.db.add_keyword(user_id, keyword)
            
            if success:
                embed = discord.Embed(
                    title="✅ 키워드 추가 완료",
                    description=f"키워드 '{keyword}'가 추가되었습니다.",
                    color=0x00ff00
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="⚠️ 키워드 중복",
                    description=f"키워드 '{keyword}'는 이미 등록되어 있습니다.",
                    color=0xffaa00
                )
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"키워드 추가 오류 (사용자 {ctx.author.id}): {e}", exc_info=True)
            await ctx.send(f"❌ 키워드 추가 중 오류가 발생했습니다: {e}")
    
    @keyword_group.command(name='삭제')
    async def delete_keyword(self, ctx: commands.Context, *, keyword: str = None):
        """
        키워드 삭제 명령어
        
        사용법: !키워드 삭제 [단어]
        """
        if not keyword:
            await ctx.send("❌ 사용법: `!키워드 삭제 [단어]`\n예: `!키워드 삭제 노트북`")
            return
        
        keyword = keyword.strip()
        if not keyword:
            await ctx.send("❌ 키워드를 입력해주세요.")
            return
        
        try:
            user_id = ctx.author.id
            logger.info(f"명령어 호출: !키워드 삭제 '{keyword}' - 사용자: {ctx.author.name} ({user_id})")
            success = await self.db.delete_keyword(user_id, keyword)
            
            if success:
                embed = discord.Embed(
                    title="✅ 키워드 삭제 완료",
                    description=f"키워드 '{keyword}'가 삭제되었습니다.",
                    color=0x00ff00
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="⚠️ 키워드 없음",
                    description=f"키워드 '{keyword}'를 찾을 수 없습니다.",
                    color=0xffaa00
                )
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"키워드 삭제 오류 (사용자 {ctx.author.id}): {e}", exc_info=True)
            await ctx.send(f"❌ 키워드 삭제 중 오류가 발생했습니다: {e}")
    
    @keyword_group.command(name='목록')
    async def list_keywords(self, ctx: commands.Context):
        """
        키워드 목록 조회 명령어
        
        사용법: !키워드 목록
        """
        try:
            user_id = ctx.author.id
            logger.info(f"명령어 호출: !키워드 목록 - 사용자: {ctx.author.name} ({user_id})")
            keywords = await self.db.get_keywords(user_id)
            
            if not keywords:
                embed = discord.Embed(
                    title="📋 등록된 키워드",
                    description="등록된 키워드가 없습니다.\n`!키워드 추가 [단어]`로 키워드를 추가하세요.",
                    color=0x5865F2
                )
                await ctx.send(embed=embed)
                return
            
            # 키워드 목록을 문자열로 변환
            keyword_list = [f"• {kw.keyword}" for kw in keywords]
            keyword_text = "\n".join(keyword_list)
            
            embed = discord.Embed(
                title="📋 등록된 키워드",
                description=keyword_text,
                color=0x5865F2
            )
            embed.set_footer(text=f"총 {len(keywords)}개의 키워드")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"키워드 목록 조회 오류 (사용자 {ctx.author.id}): {e}", exc_info=True)
            await ctx.send(f"❌ 키워드 목록 조회 중 오류가 발생했습니다: {e}")


async def setup(bot: commands.Bot, db):
    """Cog 등록 함수"""
    await bot.add_cog(KeywordCommands(bot, db))
