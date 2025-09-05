![:name](https://count.getloli.com/@astrbot_plugin_m?name=astrbot_plugin_m&theme=minecraft&padding=6&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

# AstrBot 智能音乐识别插件
 **本插件由豆包生成** 
作者使用的是docker


一款基于 AstrBot 生态的智能音乐插件，通过 **AI 大模型意图识别** 自动捕捉对话中的歌名，支持发送音乐卡片、播放链接、语音消息及音频文件，集成网易云音乐数据接口，无需手动输入指令即可完成音乐交互。

[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![AstrBot](https://img.shields.io/badge/AstrBot-3.4%2B-orange.svg)](https://github.com/Soulter/AstrBot)
[![GitHub](https://img.shields.io/badge/原作者-Zhalslar-blue)](https://github.com/Zhalslar)
[![GitHub](https://img.shields.io/badge/作者-Mnbqq-blue)](https://github.com/Mnbqq)

## 🌟 核心功能
1. **AI 智能识别**：无需 `/点歌` 等指令，自动识别对话中的歌名（如“我想听《晴天》”“发《孤勇者》的链接”）
2. **多模式发送**：根据用户意图自动选择发送方式
  - 音乐卡片（QQ 个人号专属，支持网易云音乐跳转）
  - 播放链接（直接获取音频 URL，全平台适配）
  - 语音消息（Telegram/QQ/飞书等平台支持）
  - 音频文件（以附件形式发送，支持后续保存）
3. **附加功能**：可配置自动发送歌曲热评、生成歌词图片
4. **稳定的文件处理**：集成 URL 验证、网络检测、文件完整性校验，避免无效下载与发送失败


## 📋 目录结构
```
astrbot_plugin_music/
├── main.py              # 插件核心代码（AI识别+发送逻辑）
├── api.py               # 网易云音乐API封装（歌曲搜索/热评/歌词获取）
├── metadata.yaml        # 插件元数据（名称/版本/依赖等）
├── _conf_schema.json    # 可视化配置文件（WebUI中调整参数）
├── draw.py              # 用于生成歌词图片
├── simhei.ttf           # 生成歌词所使用的字体
├── songs/               # 临时音频文件缓存目录（自动创建）
└── README.md            # 插件说明文档（本文档）
```


## 🚀 快速部署
### 1. 环境要求
- Python 3.8+
- AstrBot 核心框架（已部署并启用 LLM 大模型，如 OpenAI/Gemini 等）
- 网络环境：可访问网易云音乐公开接口或自建 NodeJS API 服务


### 2. 安装步骤
1. **下载插件**  
   将插件目录 `astrbot_plugin_m` 放入 AstrBot 插件目录：  
   `AstrBot/data/plugins/astrbot_plugin_m/`

2. **安装依赖**  
   插件依赖以下 Python 包，可通过 pip 安装：
   ```bash
   pip install aiohttp>=3.9.0 requests>=2.31.0 jinja2>=3.1.0
   ```

3. **启用插件**  
  1. 登录 AstrBot WebUI → 进入「插件管理」页面  
  2. 找到「AstrBot 智能音乐识别插件」，点击「启用」  
  3. （可选）点击「配置」调整参数（如 API 类型、热评开关等）


### 3. 配置说明（_conf_schema.json）
在 WebUI 插件配置页或直接修改 `_conf_schema.json`，支持以下参数：

| 配置项            | 类型    | 默认值          | 说明                                                                 |
|-------------------|---------|-----------------|----------------------------------------------------------------------|
| auto_cleanup      | bool    | true            | 是否自动清理临时音频文件（避免占用存储空间）                         |
| default_api       | string  | "netease"       | 音乐数据来源：<br>- "netease"：直接调用公开API<br>- "netease_nodejs"：自建NodeJS服务 |
| nodejs_base_url   | string  | "http://netease_cloud_music_api:3000" | 自建 NodeJS 网易云 API 地址（仅 default_api 为 "netease_nodejs" 时生效） |
| enable_comments   | bool    | true            | 是否自动发送歌曲热评（识别成功后随机返回一条热评）                   |
| enable_lyrics     | bool    | false           | 是否生成并发送歌词图片（需确保 draw.py 文件正常）                   |
| analysis_prob     | float   | 0.9             | 消息识别概率（0-1，1=100% 触发 AI 识别，0=不触发）                  |


## 🎯 使用示例
| 用户输入                          | AI 识别结果                | 插件输出                                  |
|-----------------------------------|---------------------------|-----------------------------------------|
| “我想听周杰伦的《晴天》”          | 歌名：晴天；意图：默认     | 发送网易云音乐卡片 + 随机热评            |
| “发《孤勇者》的链接给我”          | 歌名：孤勇者；意图：发链接 | 发送“🎶《孤勇者》- 陈奕迅\n🔗播放链接：xxx” |
| “把《小幸运》当文件发过来”        | 歌名：小幸运；意图：发文件 | 下载音频并以附件形式发送 + 提示“已发送文件” |
| “《稻香》用语音播放”              | 歌名：稻香；意图：发语音   | 以语音消息形式发送音频（支持平台：QQ/Telegram） |


## 网易云Nodejs模块说明

> 通过网易云Nodejs项目，使用互联网上公开的项目资源 或 自己部署项目 来获得稳定的网易云音源

>项目地址：[网易云Nodejs项目官网](https://neteasecloudmusicapi.js.org/#/)
- 通过公开的项目获取音源

  如果你不想搭建服务器，又不能使用默认的服务，可以在互联网上搜索`allinurl:eapi_decrypt.html`来寻找公开项目的域名。下面贴一些搜集的公开url。
  ```text
  https://163api.qijieya.cn
  https://zm.armoe.cn
  http://dg-t.cn:3000
  http://111.229.38.178:3333
  https://wyy.xhily.com/
  http://45.152.64.114:3005
  http://42.193.244.179:3000
  https://music-api.focalors.ltd
  ```
  举例：插件的`nodejs_base_url`参数设置为`https://163api.qijieya.cn`，`default_api`调为`netease_nodejs`，即可完成配置。可以多尝试几个域名来寻找稳定音源。
- 部署自己的项目

  通过官网介绍部署项目，获得稳定音源。这里介绍docker compose快速部署。

  修改`astrbot.yml`文件，添加服务
  ```yaml
    netease_cloud_music_api:
      image: binaryify/netease_cloud_music_api
      container_name: netease_cloud_music_api
      environment:
        - http_proxy=
        - https_proxy=
        - no_proxy=
        - HTTP_PROXY=
        - HTTPS_PROXY=
        - NO_PROXY=
      networks:
        - astrbot_network
      # ports:
      #   - "3000:3000" 可以通过公共端口来调试
  ```
  然后在`astrbot.yml`文件所在的目录运行命令启动服务：
  ```cmd
  docker compose -f astrbot.yml up -d netease_cloud_music_api
  ```
  如果你开放了上面的调试端口，可以通过`{主机名}:3000`访问示例页面

  将参数`nodejs_base_url`设置为`http://netease_cloud_music_api:3000`,`default_api`调为`netease_nodejs`，即可完成配置。

  这里的端口号3000可以修改成其他端口，具体见 Nodejs项目 文档。
  
  
## ⚠️ 常见问题
1. **“未检测到可用的大模型”**  
   - 原因：AstrBot 未配置或启用 LLM 供应商  
   - 解决：进入 AstrBot 「系统配置」→「LLM 供应商」，添加并启用 OpenAI/Gemini 等服务

2. **“获取音频链接失败”**  
   - 原因1：网易云公开 API 限制，部分歌曲无法获取链接  
   - 原因2：自建 NodeJS API 服务未启动或地址错误  
   - 解决：切换 `default_api` 为 “netease_nodejs” 并配置正确的 `nodejs_base_url`

3. **“文件发送失败”**  
   - 原因1：临时文件下载不完整（网络波动）  
   - 原因2：平台不支持文件发送（如部分第三方聊天工具）  
   - 解决：重试操作，或切换为“发链接”模式


## 📌 版本更新日志
| 版本    | 更新时间       | 核心变更                                                                 |
|---------|----------------|--------------------------------------------------------------------------|
| v2.1.0  | 2025-8-31     | 1. 融合优化版文件发送逻辑（URL验证+网络检测+完整性校验）<br>2. 优化临时文件清理机制 |
| v2.0.0  | 2025-XX-XX     | 1. 移除原有点歌命令与按钮功能<br>2. 新增 LLM 意图识别，支持自动识别歌名与需求       |
| v1.0.0  | 2025-XX-XX     | 1. 初始版本，支持网易云音乐搜索<br>2. 实现热评发送、歌词图片生成功能               |

# ✍🏻️TODO

- [ ] 让LLM识别出用户意图，发送歌词/歌词图片
- [ ] 将网易云params和encseckey，放到插件配置中，用户自行配置


## 👥 贡献指南

- 🌟 Star 这个项目！（点右上角的星星，感谢支持！）
- 🐛 提交 Issue 报告问题
- 💡 提出新功能建议
- 🔧 提交 Pull Request 改进代码

## 📞 反馈与维护
- 插件仓库：[https://github.com/Mnbqq/astrbot_plugin_m](https://github.com/Mnbqq/astrbot_plugin_m)
- 问题反馈：在 GitHub Issues 提交 bug 或功能建议
- 维护者：Mnbqq

## 原插件地址
- 插件仓库：[https://github.com/Zhalslar/astrbot_plugin_music](https://github.com/Zhalslar/astrbot_plugin_music)
- 作者：Zhalslar


