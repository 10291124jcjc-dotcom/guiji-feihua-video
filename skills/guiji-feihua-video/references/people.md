# 人物库：添加和调整人物

视频里出现真实人物，就用他们的**公开授权照片**处理成漫画网点风。好认，也合规。
不要用 AI 生成的"像他的脸"，也不要用新闻图片、官网照片（没有改编授权）。

## 库在哪
- 种子人物（随 skill 自带）：`assets/people/`，现有 `sam_altman`、`dario_amodei`
- 用户的人物库：`<视频根目录>/people/`（例：`D:\ClaudeProjects\视频\people\`），新人物加在这里，跨期复用
- 漫画化结果缓存在每个人物的 `cache/` 里；改了 person.json 会自动重新生成

## 添加一个人（约 5~10 分钟）

1. **找照片**：`python add_person.py search "Jensen Huang"`
   - 只选 ✓（CC BY / CC BY-SA / CC0 / 公有领域）。带 NC（非商用）、ND（禁止改编）的不能用：视频要发到平台，而且我们改编了照片。
   - 优先：单人、正脸或 3/4 侧脸、背景简单、清晰的半身照。
2. **下载并生成初稿**：
   `python add_person.py add <库目录> jensen_huang "File:xxx.jpg" --zh 黄仁勋 --en "Jensen Huang" --org NVIDIA --facing right`
   - `facing` 填人物脸朝哪边（看照片）。朝右的人放画面左边，朝左的放右边；想换边就把 `mirror` 改成 true，同时翻转 facing。
3. **看调试图** `<库>/<id>/_mask.png`（用 Read 看图）：
   - 压暗的部分 = 被当成背景抠掉；绿框 = 一定是人（sure_fg）；紫框 = 一定是背景（sure_bg）。
   - 坐标是 900×1200 的工作图（crop 之后缩放出来的），网格每 50px 一条，每 100px 标数字。
4. **调 person.json，再 `python add_person.py check <库目录> <id>`**，直到干净：
   - **背景残留**（脸旁、头发边有一块没抠掉）：在那里加一个 `sure_bg` 矩形。注意别和 `sure_fg` 重叠，**fg 优先级更高**，重叠的地方永远算人。第一期奥特曼脸侧的残留，就是因为 fg 椭圆画太大、盖过了脸颊。
   - **人被抠掉一块**（肩膀、头发缺了）：加或扩大 `sure_fg`。
   - **构图**：`crop` 在原图上取 3:4 的半身像，头顶留一点空。
   - **底角有碎片**：用 `fade_corner`（右下角渐隐，镜像前的坐标）。
5. **看漫画预览** `_manga.png`，确认一眼能认出是谁。认不出就换一张照片（正脸、光线均匀的效果最好）。
6. **署名**：person.json 的 `credit` 会自动写进片尾卡；发布文案里也要写（见 publish.md）。

## person.json 例子
见 `assets/people/sam_altman/person.json`（没镜像）和 `dario_amodei/person.json`（镜像 + fade_corner）。
