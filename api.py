import json
import aiohttp
from astrbot import logger

# 网易云音乐加密参数（仅 NetEaseMusicAPI 类使用，NodeJS 版本无需依赖）
PARAMS = "D33zyir4L/58v1qGPcIPjSee79KCzxBIBy507IYDB8EL7jEnp41aDIqpHBhowfQ6iT1Xoka8jD+0p44nRKNKUA0dv+n5RWPOO57dZLVrd+T1J/sNrTdzUhdHhoKRIgegVcXYjYu+CshdtCBe6WEJozBRlaHyLeJtGrABfMOEb4PqgI3h/uELC82S05NtewlbLZ3TOR/TIIhNV6hVTtqHDVHjkekrvEmJzT5pk1UY6r0="
ENC_SEC_KEY = "45c8bcb07e69c6b545d3045559bd300db897509b8720ee2b45a72bf2d3b216ddc77fb10daec4ca54b466f2da1ffac1e67e245fea9d842589dc402b92b262d3495b12165a721aed880bf09a0a99ff94c959d04e49085dc21c78bbbe8e3331827c0ef0035519e89f097511065643120cbc478f9c0af96400ba4649265781fc9079"


class NetEaseMusicAPI:
    """
    网易云音乐公开API版本（兼容原有逻辑，按需使用）
    """
    def __init__(self):
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/55.0.2883.87 UBrowser/6.2.4098.3 Safari/537.36"
        }
        self.headers = {"referer": "http://music.163.com"}
        self.cookies = {"appver": "2.0.2"}
        self.session = aiohttp.ClientSession()

    async def _request(self, url: str, data: dict = {}, method: str = "GET"):
        """统一请求接口（含错误捕获与日志）"""
        try:
            # 关键修复：补充 full_url 定义（拼接完整URL，用于日志打印）
            full_url = url  # NetEaseMusicAPI 直接使用传入的完整URL，无需额外拼接
            if method.upper() == "POST":
                async with self.session.post(
                    url, headers=self.header, cookies=self.cookies, data=data
                ) as response:
                    raw_response = await response.text()
                    logger.debug(f"NetEase API POST 请求: {full_url} | 状态: {response.status}")
                    if response.headers.get("Content-Type") == "application/json":
                        return await response.json()
                    else:
                        return json.loads(raw_response) if raw_response else {}
            elif method.upper() == "GET":
                async with self.session.get(
                    url, headers=self.headers, cookies=self.cookies
                ) as response:
                    raw_response = await response.text()
                    logger.debug(f"NetEase API GET 请求: {full_url} | 状态: {response.status}")
                    return await response.json() if response.headers.get("Content-Type") == "application/json" else {}
            else:
                raise ValueError("不支持的请求方式")
        except json.JSONDecodeError as e:
            # 修复：使用已定义的 full_url 打印日志
            logger.error(f"NetEase API JSON 解析失败: {e} | 响应内容: {raw_response[:200]} | URL: {full_url}")
            return {}
        except Exception as e:
            # 修复：使用已定义的 full_url 打印日志
            logger.error(f"NetEase API 请求失败: {str(e)} | URL: {full_url}")
            return {}

    async def fetch_data(self, keyword: str, limit=5) -> list[dict]:
        """搜索歌曲（返回结构化列表）"""
        try:
            url = "http://music.163.com/api/search/get/web"
            data = {"s": keyword, "limit": limit, "type": 1, "offset": 0}
            result = await self._request(url, data=data, method="POST")
            
            # 校验响应结构
            if not result or "result" not in result or "songs" not in result["result"]:
                logger.error(f"NetEase API 搜索响应格式错误: {result}")
                return []
            
            return [
                {
                    "id": song["id"],
                    "name": song["name"],
                    "artists": "、".join(artist["name"] for artist in song["artists"]),
                    "duration": song["duration"],
                }
                for song in result["result"]["songs"][:limit]
            ]
        except Exception as e:
            logger.error(f"NetEase API 搜索歌曲失败: {str(e)}")
            return []

    async def fetch_comments(self, song_id: int):
        """获取歌曲热评"""
        try:
            url = f"https://music.163.com/weapi/v1/resource/hotcomments/R_SO_4_{song_id}?csrf_token="
            data = {"params": PARAMS, "encSecKey": ENC_SEC_KEY}
            result = await self._request(url, data=data, method="POST")
            return result.get("hotComments", [])
        except Exception as e:
            logger.error(f"NetEase API 获取热评失败: {str(e)} | 歌曲ID: {song_id}")
            return []

    async def fetch_lyrics(self, song_id):
        """获取歌曲歌词"""
        try:
            url = f"https://netease-music.api.harisfox.com/lyric?id={song_id}"
            result = await self._request(url, method="GET")
            return result.get("lrc", {}).get("lyric", "歌词未找到")
        except Exception as e:
            logger.error(f"NetEase API 获取歌词失败: {str(e)} | 歌曲ID: {song_id}")
            return "歌词获取失败"

    async def fetch_extra(self, song_id: str | int) -> dict[str, str]:
        """获取歌曲额外信息（音频链接、封面等）"""
        try:
            url = f"https://www.hhlqilongzhu.cn/api/dg_wyymusic.php?id={song_id}&br=7&type=json"
            result = await self._request(url, method="GET")
            return {
                "title": result.get("title", "未知歌曲"),
                "author": result.get("singer", "未知歌手"),
                "cover_url": result.get("cover", ""),
                "audio_url": result.get("music_url", ""),
            }
        except Exception as e:
            logger.error(f"NetEase API 获取额外信息失败: {str(e)} | 歌曲ID: {song_id}")
            return {"title": "未知歌曲", "author": "未知歌手", "cover_url": "", "audio_url": ""}

    async def close(self):
        """关闭会话（释放资源）"""
        await self.session.close()


class NetEaseMusicAPINodeJs:
    """
    网易云音乐 NodeJS API 版本（适配 https://163api.qijieya.cn）
    优化：支持 HTTPS、JSON 格式请求、浏览器头信息
    """
    def __init__(self, base_url: str):
        # 处理 BaseURL 格式（确保结尾带 "/"，避免拼接错误）
        self.base_url = base_url.rstrip("/") + "/"
        # 初始化会话（添加浏览器头，避免 API 拦截）
        self.session = aiohttp.ClientSession(
            base_url=self.base_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
                "Referer": self.base_url,
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*"
            },
            connector=aiohttp.TCPConnector()  # 避免 SSL 证书验证问题（可选，视 API 情况调整）
        )
        logger.debug(f"NodeJS API 初始化完成 | BaseURL: {self.base_url}")

    async def _request(self, url: str, data: dict = {}, method: str = "GET"):
        """统一请求接口（适配 NodeJS API 格式）"""
        try:
            full_url = self.base_url + url.lstrip("/")  # 拼接完整 URL
            if method.upper() == "POST":
                # NodeJS API 优先使用 JSON 格式传参
                async with self.session.post(url, json=data) as response:
                    raw_response = await response.text()
                    logger.debug(f"NodeJS API POST 请求: {full_url} | 状态: {response.status}")
                    logger.debug(f"NodeJS API 响应内容: {raw_response[:300]}")  # 打印前300字符（避免过长）
                    
                    if response.status == 200:
                        try:
                            return json.loads(raw_response)
                        except json.JSONDecodeError:
                            logger.error(f"NodeJS API JSON 解析失败 | 响应: {raw_response[:200]}")
                            return {}
                    else:
                        logger.error(f"NodeJS API POST 失败 | 状态: {response.status} | 响应: {raw_response[:200]}")
                        return {}
            elif method.upper() == "GET":
                async with self.session.get(url, params=data) as response:
                    raw_response = await response.text()
                    logger.debug(f"NodeJS API GET 请求: {full_url} | 状态: {response.status}")
                    if response.status == 200:
                        try:
                            return json.loads(raw_response)
                        except json.JSONDecodeError:
                            logger.error(f"NodeJS API GET JSON 解析失败 | 响应: {raw_response[:200]}")
                            return {}
                    else:
                        logger.error(f"NodeJS API GET 失败 | 状态: {response.status} | 响应: {raw_response[:200]}")
                        return {}
            else:
                raise ValueError(f"不支持的请求方式: {method}")
        except aiohttp.ClientSSLError:
            logger.error(f"NodeJS API SSL 证书验证失败 | 建议检查 API 地址或关闭 SSL 验证")
            return {}
        except Exception as e:
            logger.error(f"NodeJS API 请求异常 | URL: {full_url} | 错误: {str(e)}")
            return {}

    async def fetch_data(self, keyword: str, limit=5) -> list[dict]:
        """搜索歌曲（NodeJS API 适配版）"""
        try:
            url = "/search"  # NodeJS 搜索接口路径
            data = {"keywords": keyword, "limit": limit, "type": 1, "offset": 0}
            result = await self._request(url, data=data, method="POST")
            
            # 校验响应结构（确保包含歌曲列表）
            if not result or "result" not in result or "songs" not in result["result"]:
                logger.error(f"NodeJS API 搜索响应格式错误 | 响应: {result}")
                return []
            
            # 结构化返回结果（与 NetEaseMusicAPI 格式一致，保证插件兼容性）
            return [
                {
                    "id": song["id"],
                    "name": song["name"],
                    "artists": "、".join(artist["name"] for artist in song["artists"]),
                    "duration": song["duration"],
                }
                for song in result["result"]["songs"][:limit]
            ]
        except Exception as e:
            logger.error(f"NodeJS API 搜索歌曲失败 | 关键词: {keyword} | 错误: {str(e)}")
            return []

    async def fetch_comments(self, song_id: int):
        """获取歌曲热评（NodeJS API 适配版）"""
        try:
            url = "/comment/hot"  # NodeJS 热评接口路径
            data = {"id": song_id, "type": 0, "limit": 10}  # type=0 表示歌曲
            result = await self._request(url, data=data, method="POST")
            return result.get("hotComments", [])
        except Exception as e:
            logger.error(f"NodeJS API 获取热评失败 | 歌曲ID: {song_id} | 错误: {str(e)}")
            return []

    async def fetch_lyrics(self, song_id):
        """获取歌曲歌词（NodeJS API 适配版）"""
        try:
            url = "/lyric"  # NodeJS 歌词接口路径
            data = {"id": song_id, "os": "pc"}  # 增加 os 参数适配部分 NodeJS 服务
            result = await self._request(url, data=data, method="GET")
            return result.get("lrc", {}).get("lyric", "歌词未找到")
        except Exception as e:
            logger.error(f"NodeJS API 获取歌词失败 | 歌曲ID: {song_id} | 错误: {str(e)}")
            return "歌词获取失败"

    async def fetch_extra(self, song_id: str | int) -> dict[str, str]:
        """获取歌曲额外信息（音频链接等，NodeJS API 适配版）"""
        try:
            # 关键修复1：确保 song_id 是字符串（部分 API 不接受数字类型）
            song_id_str = str(song_id)
            url = "/song/url"  # NodeJS 音频链接接口路径
            # 关键修复2：调整参数格式（部分 NodeJS API 要求 "ids" 而非 "id"，多传一个参数兼容）
            data = {
                "id": song_id_str,
                "ids": song_id_str,  # 新增 ids 参数，适配部分 API 要求
                "br": 320000  # 320k 高质量音频
            }
            logger.debug(f"NodeJS API 请求音频链接 | song_id: {song_id_str} | 参数: {data}")
            result = await self._request(url, data=data, method="POST")
            
            # 关键修复3：增强响应解析容错（打印完整响应，便于定位格式问题）
            logger.debug(f"NodeJS API 音频响应: {json.dumps(result, ensure_ascii=False)[:500]}")
            
            # 校验响应结构（兼容可能的响应格式差异）
            if not result:
                logger.error(f"NodeJS API 音频响应为空 | song_id: {song_id_str}")
                return {"audio_url": ""}
            # 情况1：响应是 {"data": [{"url": "..."}]}（标准格式）
            if "data" in result and isinstance(result["data"], list) and len(result["data"]) > 0:
                audio_url = result["data"][0].get("url", "")
                if not audio_url:
                    logger.error(f"NodeJS API 音频链接为空 | song_id: {song_id_str} | 响应: {result}")
                    return {"audio_url": ""}
                return {"audio_url": audio_url}
            # 情况2：响应是 {"url": "..."}（部分 API 简化格式）
            elif "url" in result and result["url"]:
                return {"audio_url": result["url"]}
            # 情况3：响应格式不匹配
            else:
                logger.error(f"NodeJS API 音频响应格式错误 | song_id: {song_id_str} | 响应: {result}")
                return {"audio_url": ""}
        except Exception as e:
            logger.error(f"NodeJS API 获取音频链接失败 | song_id: {song_id} | 错误: {str(e)} | 堆栈: {traceback.format_exc()}")
            return {"audio_url": ""}


class MusicSearcher:
    """
    多平台音乐搜索工具类（保留原有功能，支持 QQ/网易云/酷狗等平台）
    """
    def __init__(self):
        self.base_url = "https://music.txqq.pro/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://music.txqq.pro/"
        }
        self.session = aiohttp.ClientSession()

    async def fetch_data(self, song_name: str, platform_type: str, limit: int = 5):
        """多平台搜索歌曲（platform_type 支持 qq/netease/kugou 等）"""
        try:
            data = {
                "input": song_name,
                "filter": "name",
                "type": platform_type,
                "page": 1,
            }
            async with self.session.post(
                self.base_url, data=data, headers=self.headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "songs" not in result or not isinstance(result["songs"], list):
                        logger.error(f"MusicSearcher 响应格式错误 | 平台: {platform_type} | 响应: {result}")
                        return []
                    # 结构化返回结果（完整闭合所有花括号和括号）
                    return [
                        {
                            "id": song["songid"],
                            "name": song.get("title", "未知歌曲"),
                            "artists": song.get("author", "未知歌手"),
                            "url": song.get("url", "无"),
                            "link": song.get("link", "无"),
                            "lyrics": song.get("lrc", "无"),
                            "cover_url": song.get("pic", "无")
                        }
                        for song in result["songs"][:limit]
                    ]
                else:
                    logger.error(f"MusicSearcher 请求失败 | 平台: {platform_type} | 状态码: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"MusicSearcher 搜索异常 | 关键词: {song_name} | 错误: {str(e)}")
            return []

    async def close(self):
        """关闭会话释放资源"""
        await self.session.close()