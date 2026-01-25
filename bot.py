# -*- coding: utf-8 -*-
"""
Discord 봇 메인 파일
"""
import discord
from discord.ext import commands, tasks
import logging
import asyncio

from config import Settings, setup_logging
from database import Database
from crawling import HotdealCrawler

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

# 크롤러 초기화
crawler = HotdealCrawler(db=db)


async def send_notification(user_id: int, post_data: dict, matched_keywords: list) -> bool:
    """
    사용자에게 알림 전송
    
    Args:
        user_id: Discord 사용자 ID
        post_data: 게시글 데이터
        matched_keywords: 매칭된 키워드 리스트
    
    Returns:
        bool: 알림 전송 성공 여부
    """
    try:
        # 먼저 캐시에서 찾기
        user = bot.get_user(user_id)
        if not user:
            # 캐시에 없으면 서버에서 찾기
            for guild in bot.guilds:
                member = guild.get_member(user_id)
                if member:
                    user = member
                    logger.debug(f"사용자 ID {user_id}를 서버 '{guild.name}'에서 찾음 (캐시)")
                    break
        
        # 여전히 없으면 API에서 가져오기 시도
        if not user:
            try:
                user = await bot.fetch_user(user_id)
                logger.debug(f"사용자 ID {user_id}를 API에서 가져옴: {user.name}")
            except discord.NotFound:
                logger.warning(f"사용자 ID {user_id}를 Discord API에서도 찾을 수 없습니다")
                # 서버 멤버로 찾기 시도
                for guild in bot.guilds:
                    try:
                        member = await guild.fetch_member(user_id)
                        if member:
                            user = member
                            logger.debug(f"사용자 ID {user_id}를 서버 '{guild.name}'에서 API로 가져옴")
                            break
                    except discord.NotFound:
                        continue
                    except discord.Forbidden:
                        logger.warning(f"서버 '{guild.name}'에서 멤버를 가져올 권한이 없습니다")
                        continue
        
        if not user:
            logger.warning(f"사용자 ID {user_id}를 찾을 수 없어 알림을 전송할 수 없습니다 (모든 방법 시도 실패)")
            return False
        
        # URL 처리 (full_url 우선, 없으면 url 사용, 상대 경로면 절대 경로로 변환)
        post_url = post_data.get('full_url') or post_data.get('url', '')
        if post_url and not post_url.startswith(('http://', 'https://')):
            # 상대 경로인 경우 절대 경로로 변환
            if post_url.startswith('/'):
                post_url = f"https://arca.live{post_url}"
            else:
                post_url = f"https://arca.live/{post_url}"
        
        # 알림 메시지 생성
        embed = discord.Embed(
            title="🔔 키워드 알림",
            description=f"**{post_data['title']}**",
            color=0xFF0000,
            url=post_url if post_url.startswith(('http://', 'https://')) else None
        )
        embed.add_field(
            name="매칭된 키워드",
            value=", ".join(matched_keywords),
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
        embed.set_footer(text=f"출처: {post_data.get('source', 'Arca Live')}")
        
        # DM 시도
        try:
            await user.send(embed=embed)
            logger.debug(f"DM 전송 성공: 사용자 {user.name} ({user_id})")
            return True
        except discord.Forbidden:
            # DM이 차단되었거나 불가능한 경우
            logger.debug(f"DM 전송 실패 (차단됨): 사용자 {user.name} ({user_id}), 채널로 전송 시도")
            pass
        
        # DM 실패 시 봇이 있는 채널에 메시지 전송
        for guild in bot.guilds:
            member = guild.get_member(user_id)
            if member:
                # 알림 채널이 설정되어 있으면 해당 채널 사용
                channel_id = await db.get_notification_channel(guild.id)
                if channel_id:
                    channel = guild.get_channel(channel_id)
                else:
                    # 알림 채널이 없으면 텍스트 채널 중 첫 번째 사용
                    channel = discord.utils.get(guild.text_channels, name='general')
                    if not channel:
                        # general 채널이 없으면 첫 번째 텍스트 채널 사용
                        channels = [ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages]
                        if channels:
                            channel = channels[0]
                
                if channel:
                    try:
                        # URL 처리 (위에서 처리한 post_url 사용)
                        post_url = post_data.get('full_url') or post_data.get('url', '')
                        if post_url and not post_url.startswith(('http://', 'https://')):
                            if post_url.startswith('/'):
                                post_url = f"https://arca.live{post_url}"
                            else:
                                post_url = f"https://arca.live/{post_url}"
                        
                        message = f"{member.mention} 🔔 키워드 알림!\n"
                        message += f"**매칭된 키워드:** {', '.join(matched_keywords)}\n"
                        message += f"**제목:** {post_data['title']}\n"
                        message += f"**링크:** {post_url or 'N/A'}"
                        await channel.send(message, embed=embed)
                        logger.debug(f"채널 알림 전송 성공: 사용자 {member.name} ({user_id}), 채널: {channel.name}")
                        return True
                    except discord.Forbidden:
                        logger.warning(f"채널 알림 전송 실패 (권한 없음): 채널 {channel.name} ({channel.id})")
                        continue
        
        # 모든 방법 실패
        logger.warning(f"사용자 ID {user_id}에게 알림을 전송할 수 있는 방법이 없습니다")
        return False
        
    except Exception as e:
        # 알림 전송 오류 로깅
        logger.error(f"알림 전송 중 오류 발생: 사용자 ID {user_id}, 오류: {e}", exc_info=True)
        return False


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
        # HTML 가져오기 및 파싱 (필터링 없이 모든 게시글)
        html_data = await crawler.fetch()
        if not html_data:
            return
        
        all_posts = crawler.parse(html_data)
        if not all_posts:
            return
        
        # 마지막 게시글 작성 시간 가져오기 (알림용 - datetime 기준으로 판단)
        last_post_datetime = await db.get_last_post_datetime(crawler.crawler_name) if crawler.db else None
        last_post_url = await db.get_last_post_url(crawler.crawler_name) if crawler.db else None
        last_post_id = await db.get_last_post_id(crawler.crawler_name) if crawler.db else None
        
        # 새로운 게시글 필터링 (게시글 작성 시간 기준)
        new_posts_for_notification = []
        if last_post_datetime and all_posts:
            # 마지막 게시글 작성 시간을 기준으로 필터링
            from dateutil import parser as date_parser
            try:
                for post in all_posts:
                    post_datetime_str = post.get('datetime', '')
                    if post_datetime_str:
                        try:
                            # ISO 형식 datetime 문자열을 datetime 객체로 변환
                            parsed_datetime = date_parser.isoparse(post_datetime_str)
                            # timezone-aware면 timezone-naive로 변환
                            if parsed_datetime.tzinfo is not None:
                                post_datetime = parsed_datetime.replace(tzinfo=None)
                            else:
                                post_datetime = parsed_datetime
                            
                            # 마지막 게시글 시간도 timezone-naive로 통일
                            if last_post_datetime.tzinfo is not None:
                                last_datetime_naive = last_post_datetime.replace(tzinfo=None)
                            else:
                                last_datetime_naive = last_post_datetime
                            
                            # 마지막 게시글 시간보다 나중에 작성된 게시글만 새로운 게시글
                            if post_datetime > last_datetime_naive:
                                new_posts_for_notification.append(post)
                        except (ValueError, TypeError) as e:
                            logger.debug(f"게시글 datetime 파싱 오류: {post_datetime_str}, {e}")
                            # datetime 파싱 실패 시 URL로 폴백
                            if last_post_url:
                                post_url = post.get('full_url') or post.get('url', '')
                                if post_url:
                                    normalized_post_url = post_url.split('?')[0]
                                    normalized_last_url = last_post_url.split('?')[0]
                                    if normalized_post_url != normalized_last_url:
                                        new_posts_for_notification.append(post)
                    else:
                        # datetime이 없으면 URL로 폴백
                        if last_post_url:
                            post_url = post.get('full_url') or post.get('url', '')
                            if post_url:
                                normalized_post_url = post_url.split('?')[0]
                                normalized_last_url = last_post_url.split('?')[0]
                                if normalized_post_url != normalized_last_url:
                                    new_posts_for_notification.append(post)
                
                if new_posts_for_notification:
                    logger.info(f"새로운 게시글 {len(new_posts_for_notification)}개 발견 (마지막 시간: {last_post_datetime.strftime('%Y-%m-%d %H:%M:%S')})")
            except Exception as e:
                logger.warning(f"datetime 기준 필터링 오류: {e}, URL 기준으로 폴백")
                # datetime 필터링 실패 시 URL로 폴백
                if last_post_url and all_posts:
                    found_last_post = False
                    for post in all_posts:
                        post_url = post.get('full_url') or post.get('url', '')
                        if post_url:
                            normalized_post_url = post_url.split('?')[0]
                            normalized_last_url = last_post_url.split('?')[0]
                            if normalized_post_url == normalized_last_url:
                                found_last_post = True
                                continue
                            elif found_last_post or not found_last_post:
                                new_posts_for_notification.append(post)
        elif last_post_url and all_posts:
            # datetime이 없으면 URL 기준으로 필터링
            found_last_post = False
            for post in all_posts:
                post_url = post.get('full_url') or post.get('url', '')
                if post_url:
                    normalized_post_url = post_url.split('?')[0]
                    normalized_last_url = last_post_url.split('?')[0]
                    if normalized_post_url == normalized_last_url:
                        found_last_post = True
                        continue
                    elif found_last_post:
                        new_posts_for_notification.append(post)
                    else:
                        new_posts_for_notification.append(post)
            
            if new_posts_for_notification:
                logger.info(f"새로운 게시글 {len(new_posts_for_notification)}개 발견 (마지막 URL: {last_post_url.split('?')[0]})")
            elif not found_last_post:
                logger.warning(f"마지막 게시글 URL을 찾을 수 없어 모든 게시글을 새로운 것으로 간주")
                new_posts_for_notification = all_posts
        elif last_post_id and all_posts:
            # URL도 없으면 ID로 폴백 (하위 호환성)
            try:
                last_id_int = int(last_post_id)
                for post in all_posts:
                    post_id = post.get('post_id', '')
                    if post_id.isdigit():
                        post_id_int = int(post_id)
                        if post_id_int > last_id_int:
                            new_posts_for_notification.append(post)
                        elif post_id_int <= last_id_int:
                            break
                
                if new_posts_for_notification:
                    logger.info(f"새로운 게시글 {len(new_posts_for_notification)}개 발견 (마지막 ID: {last_id_int})")
            except ValueError:
                logger.warning(f"마지막 게시글 ID 변환 오류: {last_post_id}")
                new_posts_for_notification = all_posts
        else:
            # 첫 크롤링이거나 마지막 정보가 없으면 모든 게시글을 새로운 것으로 간주
            logger.info("첫 크롤링: 모든 게시글을 새로운 것으로 간주")
            new_posts_for_notification = all_posts
        
        # 모든 게시글을 데이터베이스에 저장 (URL 중복 체크로 자동 처리)
        # DB에서 삭제된 게시글도 다시 저장됨
        saved_count = 0
        for post_data in all_posts:
            from database.models import Hotdeal
            # full_url이 있으면 사용, 없으면 url 사용
            url = post_data.get('full_url') or post_data.get('url', '')
            if not url:
                continue
                
            hotdeal = Hotdeal(
                title=post_data.get('title', ''),
                price=post_data.get('price', ''),
                url=url,
                source=post_data.get('source', '')
            )
            if await db.add_hotdeal(hotdeal):
                saved_count += 1
        
        if saved_count > 0:
            logger.info(f"데이터베이스 저장 완료: {saved_count}개 새 게시글 저장됨")
        
        # 모든 키워드 가져오기
        all_keywords = await db.get_all_keywords()
        
        # 새로운 게시글에 대해서만 알림 전송
        notification_count = 0
        if not new_posts_for_notification:
            logger.debug("알림 전송할 새로운 게시글이 없습니다")
        else:
            logger.debug(f"알림 전송 대상 게시글 수: {len(new_posts_for_notification)}개")
        
        for post_data in new_posts_for_notification:
            # 키워드 매칭 확인
            matched_keywords = crawler.check_keywords(post_data.get('title', ''), all_keywords)
            if not matched_keywords:
                logger.debug(f"키워드 미매칭: '{post_data.get('title', '')[:50]}'")
            if matched_keywords:
                # 키워드를 가진 사용자 ID 목록 가져오기
                matched_users = []
                for keyword in matched_keywords:
                    users = await db.get_users_by_keyword(keyword)
                    matched_users.extend(users)
                # 중복 제거
                matched_user_ids = list(set(matched_users))
                
                if matched_user_ids:
                    logger.info(f"키워드 매칭: '{post_data.get('title', '')[:50]}' - 키워드: {matched_keywords}, 알림 대상: {len(matched_user_ids)}명")
                
                # 키워드가 매칭된 경우 사용자에게 알림
                if matched_user_ids:
                    for user_id in matched_user_ids:
                        success = await send_notification(user_id, post_data, matched_keywords)
                        if success:
                            notification_count += 1
                        else:
                            logger.warning(f"알림 전송 실패: 사용자 ID {user_id}")
        
        if notification_count > 0:
            logger.info(f"알림 전송 완료: {notification_count}개")
        
        # 마지막 게시글 정보 업데이트 (새로운 게시글이 있을 때만)
        if new_posts_for_notification and crawler.db:
            latest_post = new_posts_for_notification[0]
            latest_post_id = latest_post.get('post_id', '')
            latest_post_url = latest_post.get('full_url') or latest_post.get('url', '')
            latest_post_datetime_str = latest_post.get('datetime', '')
            
            # datetime 파싱 (timezone-naive로 통일)
            latest_post_datetime = None
            if latest_post_datetime_str:
                try:
                    from dateutil import parser as date_parser
                    parsed_datetime = date_parser.isoparse(latest_post_datetime_str)
                    # timezone-aware면 timezone-naive로 변환 (로컬 시간으로)
                    if parsed_datetime.tzinfo is not None:
                        latest_post_datetime = parsed_datetime.replace(tzinfo=None)
                    else:
                        latest_post_datetime = parsed_datetime
                except (ValueError, TypeError) as e:
                    logger.debug(f"게시글 datetime 파싱 실패: {latest_post_datetime_str}, {e}")
            
            if latest_post_id:
                await db.update_last_post_id(
                    crawler.crawler_name, 
                    latest_post_id, 
                    latest_post_url, 
                    latest_post_datetime
                )
                logger.debug(f"마지막 게시글 업데이트: ID={latest_post_id}, 시간={latest_post_datetime or 'N/A'}")
        
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
