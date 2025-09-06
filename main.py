from pathlib import Path
import random
import aiofiles
import aiohttp
import traceback
import asyncio
from astrbot.api.event import filter, AstrMessageEvent
import astrbot.api.message_components as Comp
from astrbot.api.star import Context, Star, register
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.components import Record, File
from astrbot.core.message.message_event_result import MessageChain
from astrbot import logger
from data.plugins.astrbot_plugin_m.draw import draw_lyrics

# 歌曲缓存目录
SAVED_SONGS_DIR = Path(__file__).parent.resolve() / "songs"
SAVED_SONGS_DIR.mkdir(parents=True, exist_ok=True)

class FileSenderMixin:
    """文件发送逻辑的混入类"""
    async def download_file(self, url: str, title: str) -> Path | None:
        """
        优化版文件下载：含URL验证、网络检测、完整性校验
        :return: 下载成功返回文件路径，失败返回None
        """
        try:
            # 1. URL有效性验证（仅支持HTTP/HTTPS）
            if not url.startswith(('http://', 'https://')):
                logger.error(f"无效URL格式: {url}")
                return None
            
            # 2. 网络连通性测试（避免容器网络异常）
            try:
                async with aiohttp.ClientSession() as test_session:
                    async with test_session.get("https://www.baidu.com", timeout=5):
                        pass
            except Exception as e:
                logger.error(f"网络连接异常: {str(e)}")
                return None
            
            # 3. 生成安全文件名（过滤特殊字符，避免路径错误）
            safe_title = "".join(
                c for c in title if c.isalnum() or c in ('_', '-')
            ).strip().replace(' ', '_') or str(int(random.getrandbits(32)))
            filename = f"{safe_title}.mp3"
            file_path = SAVED_SONGS_DIR / filename
            logger.debug(f"下载目标路径: {file_path}")

            # 4. 流式下载（修复：删除 stream=True 参数）
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    response.raise_for_status()  # HTTP状态码非200则抛异常
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded_size = 0

                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB分片
                            if chunk:
                                await f.write(chunk)
                                downloaded_size += len(chunk)
                                logger.debug(f"已下载: {downloaded_size}/{total_size} 字节")

            # 5. 文件完整性校验（空文件直接删除）
            if file_path.stat().st_size == 0 or (total_size > 0 and downloaded_size != total_size):
                logger.error(f"文件下载不完整: 实际大小{file_path.stat().st_size}字节，预期{total_size}字节")
                file_path.unlink(missing_ok=True)
                return None

            logger.info(f"文件下载完成: {file_path}")
            return file_path

        except aiohttp.ClientSSLError as e:
            logger.error(f"SSL证书错误: {str(e)}")
        except asyncio.TimeoutError:  # 已导入asyncio，可正常识别
            logger.error("文件下载超时（30秒）")
        except Exception as e:
            logger.error(f"下载异常: {str(e)} | 堆栈: {traceback.format_exc()}")
        return None

    async def send_audio_file(self, event: AstrMessageEvent, file_path: Path) -> bool:
        """
        优化版音频文件发送（适配 QQ 平台 aiocqhttp，仅保留 File 组件标准参数）
        :return: 发送成功返回True，失败返回False
        """
        try:
            # 1. 校验文件是否存在
            if not file_path.is_file():
                logger.error(f"文件不存在: {file_path}")
                await event.send(event.plain_result("音频文件丢失，发送失败~"))
                return False
    
            # 2. 关键：获取本地文件绝对路径（QQ 平台仅支持绝对路径，不支持 file:// URL）
            file_abs_path = str(file_path.resolve())  # 转为字符串格式（如 "/AstrBot/.../6000.mp3"）
            logger.debug(f"QQ 平台文件发送路径: {file_abs_path}")

            # 3. 构建 File 消息：仅保留标准参数（name + file）
            # 关键修复：删除 file_type 和 size，避免非标准参数报错
            file_msg = File(
                name=file_path.name,          # 必选：用户端显示的文件名（如 "6000.mp3"）
                file=file_abs_path           # 必选：QQ 平台需本地绝对路径字符串
            )

            # 4. 发送文件消息链
            await event.send(MessageChain(chain=[file_msg]))
            logger.info(f"文件发送成功: {file_path.name}")
            return True

        except Exception as e:
            # 针对性捕获 QQ 平台文件发送异常
            if "ActionFailed" in str(type(e)) and ("1200" in str(e) or "文件" in str(e)):
                logger.error(f"QQ 平台文件发送失败: {str(e)} | 检查路径: {file_abs_path}")
                await event.send(event.plain_result("文件发送失败：请确认文件路径正确且有权限访问~"))
            else:
                logger.error(f"文件发送失败: {str(e)} | 堆栈: {traceback.format_exc()}")
                await event.send(event.plain_result(f"文件发送出错: {str(e)[:20]}..."))
            return False

    async def cleanup_file(self, file_path: Path):
        """临时文件清理（参考main (1).txt的finally清理逻辑）"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"临时文件已清理: {file_path}")
        except Exception as e:
            logger.error(f"文件清理失败: {str(e)}")

@register(
    "astrbot_plugin_m",
    "Mnbqq",
    "AI识别对话中的歌名，自动发送音乐卡片/链接/语音/文件（优化版）",
    "2.1.0",
    "https://github.com/Mnbqq/astrbot_plugin_m",
)
class MusicPlugin(Star, FileSenderMixin):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config or AstrBotConfig()
        # 基础配置
        self.auto_cleanup = self.config.get("auto_cleanup", True)  # 自动清理临时文件
        self.default_api = self.config.get("default_api", "netease")
        self.nodejs_base_url = self.config.get("nodejs_base_url", "http://netease_cloud_music_api:3000")
        self.enable_comments = self.config.get("enable_comments", True)
        self.enable_lyrics = self.config.get("enable_lyrics", False)
        self.analysis_prob = self.config.get("analysis_prob", 0.9)  # 消息识别概率

        # 初始化音乐API
        if self.default_api == "netease":
            from .api import NetEaseMusicAPI
            self.api = NetEaseMusicAPI()
        elif self.default_api == "netease_nodejs":
            from .api import NetEaseMusicAPINodeJs
            self.api = NetEaseMusicAPINodeJs(base_url=self.nodejs_base_url)

        # LLM意图识别配置（原有核心逻辑保留）
        self.llm_tool_mgr = self.context.get_llm_tool_manager()
        self.llm_system_prompt = """
        你是音乐需求分析助手，需严格完成两个任务：1. 提取歌名 2. 判断意图。
         1. 歌名提取：从用户输入中精确识别并提取歌曲名称。用户有可能使用书名号《》，也可能直接说出歌名。提取时需忽略“的”、“一首”、“个”等停用词。若未提及任何歌名，输出“无歌名”。
         2. 意图判断：仅从以下选项中选择最匹配的一个输出：
          - 发卡片：用户希望发送音乐平台卡片（如网易云音乐卡片）
          - 发链接：用户希望获取音乐播放链接
          - 发语音：用户希望直接发送音频文件（语音形式）
          - 发文件：用户希望发送音频文件（附件形式）
          - 默认：未明确表述意图时返回“默认”（优先用卡片形式）
        
        示例1：用户输入“我想听《晴天》” → 歌名：晴天；意图：默认
        示例2：用户输入“发《孤勇者》的链接给我” → 歌名：孤勇者；意图：发链接
        示例3：用户输入“把《小幸运》当文件发过来” → 歌名：小幸运；意图：发文件
        示例4：用户输入“今天天气真好” → 歌名：无歌名；意图：无
        """

    async def judge_music_intent(self, text: str) -> tuple[str, str]:
        """原有LLM意图识别逻辑保留"""
        try:
            llm_provider = self.context.get_using_provider()
            if not llm_provider:
                return "无歌名", "LLM未启用"
            
            llm_response = await llm_provider.text_chat(
                prompt=f"用户输入：{text}",
                system_prompt=self.llm_system_prompt,
                image_urls=[],
                func_tool=self.llm_tool_mgr,
            )
            response_text = llm_response.completion_text.strip()

            # 解析LLM结果
            song_name = "无歌名"
            intent = "无"
            if "歌名：" in response_text:
                song_name = response_text.split("歌名：")[-1].split("；")[0].strip()
            if "意图：" in response_text:
                intent = response_text.split("意图：")[-1].strip()
            
            return song_name, intent
        except Exception as e:
            logger.error(f"LLM识别失败: {str(e)}")
            return "无歌名", "识别失败"

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """主消息监听逻辑：融合AI识别与优化版文件发送"""
        # 概率触发（避免频繁调用LLM）
        if random.random() > self.analysis_prob:
            return
        
        text = event.get_message_str().strip()
        if not text:
            return
        
        # 1. LLM识别歌名与意图
        song_name, intent = await self.judge_music_intent(text)
        if song_name == "无歌名" or intent == "无":
            return
        if intent == "LLM未启用":
            await event.send(event.plain_result("未检测到可用的大模型，请先启用LLM~"))
            return
        if intent == "识别失败":
            await event.send(event.plain_result("歌名识别失败，请重试~"))
            return
        
        # 2. 搜索歌曲信息
        songs = await self.api.fetch_data(keyword=song_name, limit=1)
        if not songs:
            await event.send(event.plain_result(f"未找到歌曲《{song_name}》~"))
            return
        selected_song = songs[0]
        song_id = selected_song["id"]
        file_path = None  # 初始化临时文件路径

        try:
            # 3. 获取歌曲音频链接（新增日志）
            extra_info = await self.api.fetch_extra(song_id=song_id)
            audio_url = extra_info.get("audio_url", "")
            logger.debug(f"获取音频链接结果 | song_id: {song_id} | extra_info: {extra_info} | audio_url: {audio_url}")  # 新增日志
            if not audio_url:
                # 新增：提示用户检查 API 状态
                await event.send(event.plain_result(f"获取《{song_name}》音频链接失败~ 可能原因：API 接口不可用/歌曲无权限"))
                return

            platform_name = event.get_platform_name()
            # 4. 按意图执行操作（核心变更：文件发送逻辑替换为优化版）
            # 4.1 发卡片（仅QQ个人号）
            if intent in ["默认", "发卡片"] and platform_name == "aiocqhttp":
                from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                assert isinstance(event, AiocqhttpMessageEvent)
                client = event.bot
                is_private = event.is_private_chat()
                payloads = {
                    "message": [{"type": "music", "data": {"type": "163", "id": str(song_id)}}]
                }
                if is_private:
                    payloads["user_id"] = event.get_sender_id()
                    await client.api.call_action("send_private_msg", **payloads)
                else:
                    payloads["group_id"] = event.get_group_id()
                    await client.api.call_action("send_group_msg", **payloads)
                await event.send(event.plain_result(f"已发送《{song_name}》音乐卡片~"))

            # 4.2 发链接
            elif intent == "发链接":
                song_info = f"🎶《{selected_song['name']}》- {selected_song['artists']}\n🔗播放链接：{audio_url}"
                await event.send(event.plain_result(song_info))

            # 4.3 发语音（原逻辑保留，适配多平台）
            elif intent == "发语音" and platform_name in ["aiocqhttp", "telegram", "lark"]:
                await event.send(event.chain_result([Record.fromURL(audio_url)]))
                await event.send(event.plain_result(f"已发送《{song_name}》语音~"))

            # 4.4 发文件（核心优化：使用融合后的下载+发送逻辑）
            elif intent == "发文件":
                await event.send(event.plain_result(f"开始下载《{song_name}》，请稍候..."))
                # 调用优化版下载方法
                file_path = await self.download_file(audio_url, song_name)
                if not file_path:
                    await event.send(event.plain_result(f"《{song_name}》下载失败，无法发送文件~"))
                    return
                # 调用优化版发送方法
                send_success = await self.send_audio_file(event, file_path)
                if send_success:
                    await event.send(event.plain_result(f"已发送《{song_name}》音频文件~"))

            # 5. 发送热评（原有逻辑保留）
            if self.enable_comments:
                comments = await self.api.fetch_comments(song_id=song_id)
                if comments:
                    hot_comment = random.choice(comments)["content"]
                    await event.send(event.plain_result(f"🔥热评：{hot_comment}"))

            # 6. 发送歌词（原有逻辑保留）
            if self.enable_lyrics:
                lyrics = await self.api.fetch_lyrics(song_id=song_id)
                if lyrics != "歌词未找到":
                    lyric_image = draw_lyrics(lyrics)
                    await event.send(MessageChain(chain=[Comp.Image.fromBytes(lyric_image)]))

        except Exception as e:
            logger.error(f"处理《{song_name}》出错: {traceback.format_exc()}")
            await event.send(event.plain_result(f"处理《{song_name}》时出错，请联系管理员~"))
        finally:
            # 7. 临时文件清理
            if self.auto_cleanup and file_path and isinstance(file_path, Path):
                await self.cleanup_file(file_path)

    @staticmethod
    def format_time(duration_ms):
        """原有时长格式化逻辑保留"""
        duration = duration_ms // 1000
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    async def terminate(self):
        """插件卸载时关闭API会话"""
        await self.api.close()
        await super().terminate()
