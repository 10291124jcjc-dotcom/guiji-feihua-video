# 硅基废话视频 · guiji-feihua-video

一个 [Claude Code](https://claude.com/claude-code) Skill，用来做「硅基废话」风格的 AI 圈中文解说视频：**白板逐笔手绘 × 黑白漫画网点**，用作者本人的克隆声音配音。

给它一个选题，它负责调研核实、写旁白、把人物照片处理成漫画像、逐笔动画渲染、自己抽帧质检，最后出封面和各平台的发布文案。

[![动画预览：笔跟着旁白一笔一笔画出来（点击到油管看完整版）](examples/2026-09-27%20从战友到对手/preview.gif)](https://www.youtube.com/watch?v=S5KILwew-TM)

## 示例：《奥特曼与阿莫迪：从战友到对手》

- ▶️ **[在油管观看](https://www.youtube.com/watch?v=S5KILwew-TM)** · 频道：[硅基废话](https://www.youtube.com/@DDJCXX)
- ▶️ [在线观看（不用登录油管，5:37，1080p）](https://10291124jcjc-dotcom.github.io/guiji-feihua-video/)
- ⬇️ [下载完整版（约 50MB）](https://github.com/10291124jcjc-dotcom/guiji-feihua-video/raw/main/examples/2026-09-27%20%E4%BB%8E%E6%88%98%E5%8F%8B%E5%88%B0%E5%AF%B9%E6%89%8B/%E4%BB%8E%E6%88%98%E5%8F%8B%E5%88%B0%E5%AF%B9%E6%89%8B.mp4)**（GitHub 页面里不能直接播放这么大的视频）
- 封面：[横版 4:3](examples/2026-09-27%20从战友到对手/封面-4x3.png) · [竖版 3:4](examples/2026-09-27%20从战友到对手/封面-3x4.png)
- 旁白稿：[`narration.py`](examples/2026-09-27%20从战友到对手/narration.py)，12 个场景的分镜：[`scenes.py`](examples/2026-09-27%20从战友到对手/scenes.py)
- 从第一句话到成片，是和 Claude Opus 5.5 在一个对话里完成的，没有打开过剪辑软件。

## 风格

- 米白纸面，一支黑杆红尾的蘸水笔跟着旁白**念到哪画到哪**，每块板画完用板擦擦掉
- 真实人物用 Wikimedia Commons 上的授权照片，处理成黑白漫画网点像：先勾墨线，再铺网点
- 只用黑、白、红三色，加黄色阴影
- 固定品牌元素：关系温度计、「不是废话」红章、漫画对白框字幕、片尾卡"都是废话，盖了章的除外"

## 能做什么

| 步骤 | 命令 |
|---|---|
| 新建一期 | `python new_episode.py <视频根目录> "标题"` |
| 找人物照片、加进人物库 | `python add_person.py search "Jensen Huang"`，然后 `add ...` |
| 配音（克隆音色 / 免费占位 / 真人录音） | `python voice.py <期> tts \| placeholder \| import` |
| 预览静帧 / 出片 / 只重渲几个场景 | `python build.py <期> preview \| render [场景...]` |
| 质检：画面是否跟得上旁白、成片抽帧 | `python build.py <期> audit \| sheet 42.5 3 \| check` |
| 油管章节 / 剪推特短版 | `python build.py <期> chapters \| cut 推特版 场景...` |
| 横竖两张封面 | `python cover.py <期>` |

9 个现成版式：开场、两人档案、对比表、时间线、大数字、金句气泡、名场面、要点清单、结尾提问加片尾卡。详见 [`references/patterns.md`](skills/guiji-feihua-video/references/patterns.md)。

## 安装

1. 把 `skills/guiji-feihua-video` 复制到 `~/.claude/skills/`（Windows：`C:\Users\<你>\.claude\skills\`）
2. 依赖：Python 3.10+、ffmpeg，以及 `pip install pillow numpy opencv-python-headless`（占位配音另需 `edge-tts`）
3. 克隆音色（可选）：在火山引擎「豆包语音」里复刻自己的声音，把 `VOLC_API_KEY`、`VOLC_SPEAKER_ID` 写进视频根目录的 `.env`（**不要提交到仓库**）
4. 开一个新的 Claude Code 会话，说"做一期视频：……"，或者输入 `/guiji-feihua-video`

说明：字体用的是 Windows 自带的楷体和微软雅黑，其他系统需要改 `scripts/wb.py` 里的字体路径。

## 致谢与授权

- 风格参考了 [trustfuture/simon-skills 的 whiteboard-video](https://github.com/trustfuture/simon-skills/tree/master/skills/whiteboard-video)（逐笔绘制、跟随旁白节拍的思路），本项目的代码是独立实现的
- 代码（skills/ 目录）：MIT 许可证，见 [LICENSE](LICENSE)；MIT 不覆盖下面的示例视频、封面和人物照片
- 示例视频、封面：© 硅基废话，保留所有权利
- 人物照片（Wikimedia Commons，CC BY 2.0，经裁剪、抠图、漫画化处理）：
  - Sam Altman：[TechCrunch](https://commons.wikimedia.org/wiki/File:Sam_Altman_CropEdit_James_Tamim.jpg)
  - Dario Amodei：[UK Prime Minister / Flickr](https://commons.wikimedia.org/wiki/File:Dario_Amodei_in_2023_(cropped).jpg)
- 视频配音为作者本人声音经 AI 克隆合成；片中"据报道"的内容以原始报道为准
