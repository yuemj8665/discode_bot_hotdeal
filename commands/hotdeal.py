# -*- coding: utf-8 -*-
"""
핫딜 관련 명령어
"""
import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)


class HotdealCommands(commands.Cog):
    """핫딜 관련 명령어 클래스"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(name='핫딜')
    async def hotdeal(self, ctx: commands.Context):
        """핫딜 목록 조회 명령어"""
        logger.info(f"명령어 호출: !핫딜 - 사용자: {ctx.author.name} ({ctx.author.id})")
        await ctx.send("핫딜 목록을 조회합니다... (구현 예정)")
    
    @app_commands.command(name="핫딜", description="핫딜 목록을 조회합니다")
    async def hotdeal_slash(self, interaction: discord.Interaction):
        """핫딜 목록 조회 슬래시 명령어"""
        logger.info(f"슬래시 명령어 호출: /핫딜 - 사용자: {interaction.user.name} ({interaction.user.id})")
        embed = discord.Embed(
            title="🔥 핫딜 목록",
            description="핫딜 목록을 조회합니다... (구현 예정)",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="핫딜추가", description="핫딜을 추가합니다")
    async def add_hotdeal(self, interaction: discord.Interaction):
        """핫딜 추가 슬래시 명령어"""
        logger.info(f"슬래시 명령어 호출: /핫딜추가 - 사용자: {interaction.user.name} ({interaction.user.id})")
        await interaction.response.send_message(
            "핫딜 추가 기능은 구현 예정입니다.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    """Cog 등록 함수"""
    await bot.add_cog(HotdealCommands(bot))
