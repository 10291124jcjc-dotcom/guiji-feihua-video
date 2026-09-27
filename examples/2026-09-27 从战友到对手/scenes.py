"""示例期：奥特曼与阿莫迪，从战友到对手（2026-09-27，12 个场景、约 5 分半）。
每个元素挂在旁白的第 i 句：s.t(i, frac)。不写 at 的元素接在上一笔之后画；chain=False 表示并行。"""
import math
from patterns import *  # noqa: F401,F403


# ------------------------------------------------------------ 12 个场景
def sc_title(s):
    watermark(s, draw_at=0.05)
    title = Text(960, 110, "从战友到对手", 120, INK, "center", bold=2, at=s.t(0, 0.0))
    s.add(title, underline(640, 1280, 262, RED, 9, double=True, seed=21))
    s.add(Portrait("sam_altman", 440, 1080, 0.82, at=s.t(0, 0.45)), Portrait("dario_amodei", 1480, 1080, 0.82, chain=False))
    for x, name, org in ((440, "山姆·奥特曼", "OpenAI"), (1480, "达里奥·阿莫迪", "Anthropic")):
        s.add(Text(x, 385, name, 44, INK, "center", bold=1, at=s.t(1, 0.05)),
              Text(x, 440, org, 34, GRAY, "center", bold=0.6))
    s.add(crack(960, 340, 930, seed=8, at=s.t(1, 0.55)))
    end_erase(s)


def sc_bios(s):
    watermark(s)
    s.add(Portrait("sam_altman", 320, 1080, 0.8, at=s.t(0, 0.0)))
    s.add(Text(600, 170, "山姆·奥特曼", 54, INK, bold=1.4, at=s.t(0, 0.05), chain=False))
    rows = ["· 斯坦福辍学创业", "· Y Combinator 总裁", "· 会讲故事，会融资"]
    for k, r in enumerate(rows):
        e = Text(600, 262 + k * 66, r, 34, INK, bold=0.8, at=s.t(0, 0.18 + k * 0.22))
        s.add(e)
    s.add(circle_text(e, seed=5))
    s.add(Portrait("dario_amodei", 1590, 1080, 0.8, at=s.t(1, 0.0)))
    s.add(Text(1000, 170, "达里奥·阿莫迪", 54, INK, bold=1.4, at=s.t(1, 0.05), chain=False))
    rows = ["· 普林斯顿物理学博士", "· 百度 → 谷歌大脑", "· 典型的科学家"]
    for k, r in enumerate(rows):
        e = Text(1000, 262 + k * 66, r, 34, INK, bold=0.8, at=s.t(1, 0.2 + k * 0.22))
        s.add(e)
    s.add(under(e, seed=6))
    end_erase(s)


def sc_openai(s):
    watermark(s)
    # 几路并行画（chain=False = 到点就画，不排队）
    s.add(year_box(60, 40, "2015年底", at=0.2, tag="year", chain=False))
    s.add(Portrait("sam_altman", 420, 1080, 0.8, at=s.t(0, 0.0), chain=False))
    s.add(Text(960, 172, "联合创始人：奥特曼、马斯克、布罗克曼、苏茨克维……", 34, GRAY, "center", bold=0.5,
               at=s.t(0, 0.1), chain=False, dur=1.4))
    # 手绘小楼（第 0 句后半段画完）
    b0 = s.t(0, 0.35)
    s.add(poly([(930, 450), (1250, 290), (1570, 450)], INK, 5, closed=False, seed=31, at=b0, chain=False, dur=0.5),
          rect(980, 450, 1520, 880, INK, 5, seed=32, at=b0 + 0.5, chain=False, dur=0.8),
          Text(1250, 470, "OpenAI", 70, INK, "center", bold=2, at=b0 + 1.3, chain=False, dur=0.6),
          rect(1210, 760, 1290, 880, INK, 4, seed=33, at=b0 + 1.9, chain=False, dur=0.3))
    for k, x in enumerate((1040, 1150, 1350, 1460)):
        s.add(hachure([(x, 600), (x + 60, 600), (x + 60, 660), (x, 660)], YELLOW, gap=9, w=3, seed=40 + k,
                      at=b0 + 2.2 + k * 0.15, chain=False, dur=0.15))
    # 第 1 句：念到“非营利”“使命”时画
    s.add(rect(1140, 690, 1360, 750, RED, 5, seed=34, at=s.t(1, 0.08), chain=False, dur=0.4),
          Text(1250, 692, "非营利", 42, RED, "center", bold=1.2, at=s.t(1, 0.08) + 0.4, chain=False, dur=0.4))
    m = Text(90, 290, "使命：\n让 AGI 造福全人类", 50, INK, bold=1.4, at=s.t(1, 0.3), chain=False, dur=1.4)
    s.add(m, wavy(96, 540, 432, RED, 5, seed=35, at=s.t(1, 0.3) + 1.45, chain=False, dur=0.5))
    end_erase(s)


def sc_meet(s):
    watermark(s)
    s.add(year_box(60, 40, "2016", at=0.2, tag="year"))
    t = Text(960, 150, "达里奥加入 OpenAI", 78, INK, "center", bold=1.8, at=s.t(0, 0.0))
    s.add(t, under(t, seed=7))
    s.add(Portrait("sam_altman", 420, 1080, 0.8, at=s.t(0, 0.2)), Portrait("dario_amodei", 1490, 1080, 0.8, chain=False))
    # 两个扣在一起的链环：搭档
    s.add(ellipse(905, 700, 78, 44, INK, 6, seed=51, at=s.t(0, 0.55)), ellipse(1015, 700, 78, 44, INK, 6, seed=52),
          Text(960, 590, "同事", 44, INK, "center", bold=1.2))
    thermo(s, 0.9, draw_at=s.t(0, 0.8))
    s.add(Text(420, 425, "CEO（2019 起）", 38, INK, "center", bold=1, at=s.t(1, 0.35)),
          Text(1490, 425, "研究副总裁", 38, INK, "center", bold=1, at=s.t(1, 0.05)))
    end_erase(s)


def sc_golden(s):
    watermark(s)
    thermo(s, 0.9, 0.95, s.t(0, 0.2))
    t = Text(960, 70, "黄金搭档期", 72, INK, "center", bold=1.8, at=s.t(0, 0.0))
    s.add(t, under(t, seed=8))
    s.add(Portrait("sam_altman", 220, 1080, 0.6), Portrait("dario_amodei", 1650, 1080, 0.6, chain=False))
    s.add(line((440, 300), (1480, 296), INK, 5, seed=60, at=s.t(1, 0.0)))
    for k, (x, yr, txt, i, f) in enumerate([(560, "2017", "RLHF\n人类反馈强化学习", 1, 0.08),
                                             (960, "2019", "GPT-2", 2, 0.25),
                                             (1360, "2020", "GPT-3\n缩放定律", 2, 0.55)]):
        s.add(ellipse(x, 298, 12, 12, RED, 7, seed=61 + k, turns=1.3, at=s.t(i, f)),
              Text(x, 318, yr, 42, RED, "center", bold=1.2), Text(x, 375, txt, 34, INK, "center", bold=0.8))
    s.add(Text(560, 470, "→ 训练 ChatGPT 的关键", 28, GRAY, "center", bold=0.4, at=s.t(1, 0.62)))
    # 缩放定律曲线
    s.add(arrow((720, 890), (720, 560), INK, 4, curve=0, seed=70, at=s.t(3, 0.0)),
          arrow((720, 890), (1230, 890), INK, 4, curve=0, seed=71),
          Text(690, 540, "能力", 32, INK, "right", bold=0.8, chain=False),
          Text(1225, 900, "规模（数据 · 算力 · 参数）", 28, INK, "right", bold=0.6, chain=False))
    curve = [(740 + i * 9, 870 - 280 * (1 - math.exp(-i / 22))) for i in range(52)]
    s.add(Stroke([(curve, False)], RED, 7, seed=72, smooth=True, at=s.t(3, 0.25)))
    s.add(not_nonsense(1140, 650, rot=12, at=s.t(3, 0.62)))
    end_erase(s)


def sc_rift(s):
    watermark(s)
    thermo(s, 0.95, 0.6, s.t(0, 0.3))
    t = Text(960, 60, "裂 痕", 72, INK, "center", bold=1.8, at=s.t(0, 0.0))
    s.add(t)
    s.add(crack(960, 170, 900, amp=22, seed=9))
    s.add(Portrait("sam_altman", 360, 1080, 0.76, at=s.t(0, 0.35)), Portrait("dario_amodei", 1560, 1080, 0.76, chain=False))
    s.add(Text(90, 170, "2019 · OpenAI", 46, RED, bold=1.2, at=s.t(1, 0.0)),
          Text(90, 240, "成立利润封顶的营利公司", 36, INK, bold=0.8))
    m = Text(90, 300, "微软投资 10 亿美元", 36, INK, bold=0.8)
    s.add(m, circle_text(m, seed=11), Text(90, 380, "商业化提速 ↗", 40, INK, bold=1.2))
    s.add(Text(1010, 170, "达里奥一派：", 46, INK, bold=1.2, at=s.t(2, 0.0)),
          Text(1010, 240, "能力随规模可预测增长", 36, INK, bold=0.8),
          Text(1010, 290, "↓", 40, RED, bold=1))
    e = Text(1010, 345, "安全必须从第一天内建", 36, RED, bold=1.1)
    s.add(e, under(e, seed=12))
    s.add(bubble(1320, 520, 210, 76, (1440, 610), "离开不是因为\n微软的交易", 32, seed=13, at=s.t(3, 0.05)))
    end_erase(s)


def sc_leave(s):
    watermark(s)
    thermo(s, 0.6, 0.25, s.t(0, 0.4))
    s.add(year_box(60, 40, "2020年底", at=0.2, tag="year"))
    s.add(speed_lines(960, 560, 520, 400, seed=14, at=s.t(0, 0.0)))
    s.add(Portrait("sam_altman", 380, 1080, 0.8, at=s.t(0, 0.0), dur=1.3), Portrait("dario_amodei", 1330, 1080, 0.8, chain=False,
                                                                            dur=1.3))
    s.add(crack(960, 150, 950, seed=15))
    s.add(Img(sfx_img("咔嚓！"), 960, 600, "pop", "c", chain=False))
    for k, x in enumerate((1560, 1650, 1740)):
        s.add(stick_person(x, 930, 190, seed=70 + k, dur=0.45))
    s.add(Text(1650, 690, "丹妮拉等核心成员", 30, INK, "center", bold=0.8))
    s.add(bubble(830, 330, 500, 128, (1180, 500),
                 "和别人的愿景争论，是极其低效的；\n不如带上你信任的人，去实现自己的愿景。", 36, seed=16,
                 at=s.t(1, 0.02), tag="q1"))
    s.erase(s.t(2, 0.0), dur=0.45, keep=("thermo", "wm", "year"))
    s.add(bubble(830, 330, 430, 118, (1180, 500), "既然愿景不同，又彼此不信任，\n何必争论？", 40, seed=17,
                 at=s.t(2, 0.08)))
    s.erase(s.t(3, 0.0), dur=0.45, keep=("thermo", "wm", "year"))
    s.add(rect(560, 190, 1360, 470, INK, 6, seed=18, at=s.t(3, 0.1)),
          Text(960, 205, "Anthropic", 110, RED, "center", bold=2),
          Text(960, 370, "2021 · 公益公司（PBC）", 42, INK, "center", bold=1))
    end_erase(s)


def sc_race(s):
    watermark(s)
    thermo(s, 0.25, 0.25)
    s.add(Portrait("sam_altman", 330, 1080, 0.78, at=s.t(0, 0.0)))
    s.add(Text(560, 160, "2022.11", 54, RED, bold=1.4, chain=False),
          Text(560, 240, "ChatGPT 横空出世", 48, INK, bold=1.2))
    e = Text(560, 330, "2 个月 → 1 亿用户", 42, INK, bold=1)
    s.add(e, under(e, seed=20), not_nonsense(790, 470, rot=-8))
    s.add(Portrait("dario_amodei", 1580, 1080, 0.78, at=s.t(1, 0.0)))
    s.add(Text(1040, 160, "2023.3", 54, RED, bold=1.4, chain=False),
          Text(1040, 240, "Claude 发布", 48, INK, bold=1.2))
    e = Text(1040, 330, "正面迎战", 42, INK, bold=1)
    s.add(e, wavy(1044, 1210, 392, RED, 5, seed=21))
    s.erase(s.t(2, 0.0), dur=0.5)
    s.add(speed_lines(700, 600, 380, 330, seed=22, at=s.t(2, 0.12)))
    s.add(Portrait("sam_altman", 640, 1080, 0.84, chain=False, dur=1.2))
    s.add(Img(stamp_img("罢免", size=90, rot=-14), 840, 600, "pop", "c"))
    s.add(Img(sfx_img("轰！", 120), 960, 300, "pop", "c", chain=False))
    s.add(Text(960, 90, "2023.11 · OpenAI 董事会风波", 56, INK, "center", bold=1.6, chain=False))
    s.add(Text(1100, 470, "据报道：", 34, GRAY, bold=0.6, at=s.t(2, 0.3)),
          Text(1100, 525, "董事会找过达里奥", 40, INK, bold=1),
          Text(1100, 585, "商讨接任 / 合并", 40, INK, bold=1))
    e = Text(1100, 670, "达里奥：拒绝", 48, RED, bold=1.4, at=s.t(2, 0.8))
    s.add(e, under(e, seed=23))
    s.add(Text(1100, 780, "几天后：奥特曼回归", 42, INK, bold=1.2, at=s.t(3, 0.05)))
    end_erase(s)


def sc_clash(s):
    watermark(s)
    thermo(s, 0.25, 0.06, s.t(0, 0.3))
    s.add(year_box(60, 40, "2026", at=0.2, tag="year"))
    t = Text(960, 360, "竞争，摆上台面", 116, INK, "center", bold=2.2, at=s.t(0, 0.0))
    s.add(t, underline(560, 1360, 520, RED, 9, double=True, seed=24))
    s.add(Text(TX, TBOT + 76, "冰点", 26, (40, 90, 170), "center", bold=0.8, at=s.t(0, 0.6), tag="thermo"))
    # 超级碗广告
    s.erase(s.t(1, 0.0), dur=0.45)
    s.add(rect(640, 170, 1440, 610, INK, 6, seed=25, at=s.t(1, 0.05)), rect(670, 200, 1410, 580, INK, 3, seed=26),
          line((980, 610), (940, 680), INK, 5, seed=27), line((1100, 610), (1140, 680), INK, 5, seed=28),
          Text(700, 222, "Anthropic 超级碗广告", 30, GRAY, bold=0.4),
          Text(700, 300, "广告正在进入 AI，", 60, INK, bold=1.6),
          Text(700, 400, "但不会进入 Claude。", 60, RED, bold=1.6))
    s.add(Portrait("sam_altman", 250, 1080, 0.62, at=s.t(1, 0.4), dur=1.2))
    s.add(bubble(330, 450, 190, 72, (300, 650), "明显不诚实！", 38, seed=29, at=s.t(1, 0.66)))
    s.add(Portrait("dario_amodei", 1650, 1080, 0.62, chain=False, dur=1.2))
    # 印度峰会合影
    s.erase(s.t(2, 0.0), dur=0.45)
    s.add(Text(960, 120, "印度 AI 峰会 · 合影", 56, INK, "center", bold=1.6, at=s.t(2, 0.02)))
    for k, x in enumerate((360, 540, 1380, 1560)):
        s.add(stick_person(x, 860, 260, seed=80 + k, arms="wide", dur=0.4))
    s.add(Portrait("sam_altman", 830, 900, 0.5, dur=1.0), Portrait("dario_amodei", 1090, 900, 0.5, chain=False, dur=1.0))
    s.add(line((628, 709), (705, 735), INK, 4, seed=85), line((1215, 735), (1292, 709), INK, 4, seed=86))
    s.add(fist(930, 720, 955, 560, (70, 80, 110), seed=87, at=s.t(2, 0.6)),
          fist(995, 720, 1012, 560, (30, 38, 62), seed=90, chain=False))
    e = Text(960, 205, "别人手牵手，他俩举拳头", 44, RED, "center", bold=1.2)
    s.add(e)
    # 五角大楼
    s.erase(s.t(3, 0.0), dur=0.45)
    cx, cy, r = 960, 470, 170
    pent = [(cx + r * math.cos(-math.pi / 2 + k * math.tau / 5), cy + r * math.sin(-math.pi / 2 + k * math.tau / 5))
            for k in range(5)]
    s.add(poly(pent, INK, 6, seed=91, at=s.t(3, 0.02)), Text(cx, cy - 26, "五角大楼", 46, INK, "center", bold=1.4))
    s.add(Text(90, 230, "Anthropic：", 48, RED, bold=1.4, at=s.t(3, 0.08)),
          Text(90, 305, "拒绝取消限制", 40, INK, bold=1),
          Text(110, 370, "· 自主武器", 40, INK, bold=1), Text(110, 430, "· 大规模国内监控", 40, INK, bold=1))
    s.add(Img(stamp_img("供应链风险", size=64, rot=-10), 420, 600, "pop", "c", at=s.t(3, 0.3)))
    s.add(arrow((1140, 470), (1260, 330), INK, 5, curve=-0.2, seed=92, at=s.t(3, 0.5)),
          Text(1280, 230, "OpenAI：", 48, INK, bold=1.4), Text(1280, 305, "数小时后签约", 40, INK, bold=1))
    s.add(Text(1280, 400, "奥特曼事后：", 34, GRAY, bold=0.5, at=s.t(3, 0.78)),
          Text(1280, 450, "“显得投机又草率”", 40, INK, bold=1.1))
    end_erase(s)


def sc_models(s):
    watermark(s)
    thermo(s, 0.06)
    s.add(Text(960, 60, "今天的模型", 64, INK, "center", bold=1.8, at=s.t(0, 0.0)))
    s.add(line((960, 170), (960, 900), INK, 4, seed=93),
          Text(480, 160, "GPT · OpenAI", 54, INK, "center", bold=1.6),
          Text(1420, 160, "Claude · Anthropic", 54, RED, "center", bold=1.6))
    L = ["最新：GPT-6 系列（2026.9）", "定位：数十亿人的超级助手", "全能：ChatGPT·图像·视频·Codex",
         "理念：迭代部署，边用边改", "商业：开始尝试广告"]
    R = ["最新：Claude Opus 5.5（2026.9）", "定位：企业和开发者", "强项：编程·智能体·Claude Code",
         "理念：宪法 AI + 负责任扩展", "商业：承诺不放广告"]
    ys = [270, 350, 430, 545, 660]
    for k in range(3):
        s.add(Text(110, ys[k], L[k], 36, INK, bold=0.9, at=s.t(1, 0.05 + k * 0.28)))
    for k in range(3):
        s.add(Text(1010, ys[k], R[k], 36, INK, bold=0.9, at=s.t(2, 0.05 + k * 0.28)))
    s.add(Text(1010, ys[3], R[3], 36, INK, bold=0.9, at=s.t(3, 0.05)))
    s.add(Text(110, ys[3], L[3], 36, INK, bold=0.9, at=s.t(3, 0.62)))
    e = Text(110, ys[4], L[4], 36, INK, bold=0.9, at=s.t(4, 0.05))
    s.add(e, circle_text(e, seed=94))
    e = Text(1010, ys[4], R[4], 36, INK, bold=0.9, at=s.t(4, 0.6))
    s.add(e, circle_text(e, seed=95), not_nonsense(1560, 780, rot=10))
    end_erase(s)


def sc_vision(s):
    watermark(s)
    thermo(s, 0.06)
    s.add(Text(960, 60, "愿 景", 72, INK, "center", bold=1.8, at=s.t(0, 0.0)))
    s.add(Portrait("sam_altman", 290, 1080, 0.74, at=s.t(1, 0.0)))
    bolt = [(560, 180), (520, 260), (552, 260), (525, 330), (590, 240), (556, 240), (585, 180)]
    s.add(poly(bolt, INK, 4, seed=96, chain=False, z=2), Fill(bolt, YELLOW, z=1))
    s.add(Text(620, 185, "智能像电一样\n廉价、充裕", 48, INK, bold=1.4, at=s.t(1, 0.1)))
    e = Text(620, 330, "人人都能拥有", 38, RED, bold=1.1)
    s.add(e, wavy(624, 860, 390, RED, 4, seed=98))
    s.add(Text(620, 420, "《智能时代》2024\n《温和的奇点》2025", 32, GRAY, bold=0.4, at=s.t(1, 0.45)))
    e = Text(620, 530, "押注史无前例的算力", 36, INK, bold=1, at=s.t(1, 0.75))
    s.add(e, circle_text(e, seed=99))
    s.add(Portrait("dario_amodei", 1620, 1080, 0.74, at=s.t(2, 0.0)))
    s.add(Text(1000, 185, "数据中心里的\n天才之国", 48, INK, bold=1.4, at=s.t(2, 0.08)))
    e = Text(1000, 330, "100 年 → 5~10 年", 50, RED, bold=1.4, at=s.t(2, 0.35))
    s.add(e, Text(1000, 400, "（生物医学进步）", 30, GRAY, bold=0.4))
    s.add(Text(1000, 450, "《充满爱意的机器》2024", 32, GRAY, bold=0.4, at=s.t(2, 0.55)))
    e = Text(1000, 520, "前提：先把安全做对", 38, INK, bold=1.1, at=s.t(2, 0.78))
    s.add(e, under(e, seed=100))
    s.add(Text(620, 640, "先让所有人用起来\n→ 社会边用边适应", 32, INK, bold=0.9, at=s.t(3, 0.05)),
          Text(1000, 640, "先弄懂、设好护栏\n→ 再全速前进", 32, INK, bold=0.9, at=s.t(3, 0.55)))
    end_erase(s)


def sc_ending(s):
    watermark(s)
    thermo(s, 0.06, 0.3, s.t(0, 0.6))
    s.add(Text(960, 60, "联合国安理会 · 2026.9.23", 56, INK, "center", bold=1.6, at=s.t(0, 0.0)))
    arc = [(960 + 560 * math.cos(a), 880 + 130 * math.sin(a)) for a in [math.pi * (0.05 + 0.9 * i / 40) for i in range(41)]]
    s.add(Portrait("sam_altman", 470, 1080, 0.72, at=s.t(0, 0.1), dur=1.4))
    s.add(Text(470, 530, "现场发言", 32, GRAY, "center", bold=0.5, chain=False))
    s.add(rect(1150, 230, 1650, 640, INK, 5, seed=101), Portrait("dario_amodei", 1400, 634, 0.55, crop_bottom=380, dur=1.3),
          Text(1400, 655, "视频连线", 30, GRAY, "center", bold=0.5))
    e = Text(960, 700, "共识：国际 AI 安全标准", 48, RED, "center", bold=1.4, at=s.t(0, 0.62))
    s.add(e, wavy(700, 1220, 770, RED, 5, seed=102))
    s.add(Stroke([(arc, False)], INK, 5, seed=103, smooth=True, chain=False))
    # 两条路
    s.erase(s.t(1, 0.0), dur=0.5)
    s.add(Stroke([([(960, 950), (960, 700)], False), ([(960, 700), (560, 390)], False),
                  ([(960, 700), (1360, 390)], False)], INK, 10, seed=104, at=s.t(1, 0.05)))
    s.add(Portrait("sam_altman", 540, 390, 0.4, dur=0.9), Portrait("dario_amodei", 1380, 390, 0.4, chain=False, dur=0.9))
    s.add(Text(960, 470, "同一个起点，两条路", 56, INK, "center", bold=1.6, at=s.t(1, 0.3)),
          Text(960, 560, "谁对谁错，交给时间", 38, RED, "center", bold=1.1, at=s.t(1, 0.62)))
    # 互动 + 品牌
    next_panel(s, 2)
    question(s, "你站哪边？", sent=2)
    end_card(s)       # 资料来源、照片署名读 episode.json


BUILDERS = {"title": sc_title, "bios": sc_bios, "openai2015": sc_openai, "meet2016": sc_meet,
            "golden": sc_golden, "rift": sc_rift, "leave": sc_leave, "race": sc_race, "clash2026": sc_clash,
            "models": sc_models, "vision": sc_vision, "ending": sc_ending}
