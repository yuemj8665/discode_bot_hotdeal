# -*- coding: utf-8 -*-
"""
Discord 봇 메인 파일
"""
import discord
from discord.ext import commands, tasks
import logging

from config import Settings, setup_logging
from database import Database
from crawling import HotdealCrawler
from services import CrawlService, NotificationService

# 로깅 설정
logger = setup_logging()

# Intents 설정
intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용 읽기 권한

# 봇 초기화
bot = commands.Bot(
    command_prefix=Settings.COMMAND_PREFIX,
    intents=intents
)

# 데이터베이스 초기화
db = Database()

# 크롤러 및 서비스 초기화
crawler = HotdealCrawler(db=db)
crawl_service = CrawlService(crawler, db)
notification_service = NotificationService(bot, db)


@tasks.loop(hours=1)
async def cleanup_task():
    """주기적으로 오래된 핫딜 데이터 삭제 (1시간마다)"""
    try:
        deleted_count = await db.cleanup_old_hotdeals(hours=24)
        if deleted_count > 0:
            logger.info(f"오래된 핫딜 데이터 삭제 완료: {deleted_count}개")
    except Exception as e:
        logger.error(f"데이터 정리 태스크 오류: {e}", exc_info=True)


@tasks.loop(minutes=1)
async def crawl_task():
    """주기적으로 크롤링을 실행하는 태스크 (1분마다)"""
    try:
        await crawl_service.run(notification_service)
    except Exception as e:
        logger.error(f"크롤링 태스크 오류: {e}", exc_info=True)


@bot.event
async def on_ready():
    """봇이 준비되었을 때 실행되는 이벤트"""
    # 데이터베이스 연결 (크롤링 태스크 시작 전에 완료되어야 함)
    try:
        await db.connect()
        logger.info("데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}", exc_info=True)
        # 데이터베이스 연결 실패 시 크롤링 태스크를 시작하지 않음
        return

    # 봇 상태 설정
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game("핫딜 모니터링 중...")
    )

    # 슬래시 명령어 동기화
    try:
        await bot.tree.sync()
    except Exception as e:
        logger.error(f"슬래시 명령어 동기화 중 오류 발생: {e}")

    # 명령어 로드
    try:
        await bot.load_extension('commands.hotdeal')
        # 키워드 명령어 로드 (db 전달)
        from commands.keyword import setup as keyword_setup
        await keyword_setup(bot, db)
    except Exception as e:
        logger.error(f"명령어 모듈 로드 오류: {e}", exc_info=True)

    # 데이터베이스 연결이 완료된 후에만 크롤링 태스크 시작
    if not crawl_task.is_running():
        crawl_task.start()
        logger.info("크롤링 태스크 시작")

    # 데이터 정리 태스크 시작
    if not cleanup_task.is_running():
        cleanup_task.start()
        logger.info("데이터 정리 태스크 시작")


@bot.event
async def on_message(message):
    """메시지가 들어올 때 실행되는 이벤트"""
    # 봇이 보낸 메시지는 무시
    if message.author.bot:
        return

    # 명령어 처리
    await bot.process_commands(message)


@bot.command(name='ping')
async def ping(ctx):
    """봇의 응답 속도를 확인하는 명령어"""
    logger.info(f"명령어 호출: !ping - 사용자: {ctx.author.name} ({ctx.author.id})")
    latency = round(bot.latency * 1000)
    await ctx.send(f'🏓 Pong! 지연 시간: {latency}ms')


@bot.command(name='정보')
async def info(ctx):
    """봇 정보를 보여주는 명령어"""
    logger.info(f"명령어 호출: !정보 - 사용자: {ctx.author.name} ({ctx.author.id})")
    embed = discord.Embed(
        title="봇 정보",
        description="핫딜 모니터링 봇",
        color=0x00ff00
    )
    embed.add_field(name="봇 이름", value=bot.user.name, inline=True)
    embed.add_field(name="서버 수", value=len(bot.guilds), inline=True)
    embed.add_field(name="지연 시간", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.set_footer(text=f"봇 ID: {bot.user.id}")
    await ctx.send(embed=embed)


# 봇 실행
if __name__ == '__main__':
    try:
        # 봇 실행
        bot.run(Settings.DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.error("토큰이 유효하지 않습니다. DISCORD_TOKEN을 확인하세요.")
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}", exc_info=True)
    finally:
        # 봇 종료 시 데이터베이스 연결 종료
        if db._pool:
            bot.loop.run_until_complete(db.close())
