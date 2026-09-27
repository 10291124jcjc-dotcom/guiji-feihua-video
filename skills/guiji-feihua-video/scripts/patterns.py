"""「硅基废话」常用版式 + 品牌固定元素。每期的 scenes.py 用 `from patterns import *` 引入。

约定：
- s.t(i, frac)：第 i 句开始后 frac 比例处的时间。元素挂在"念到它的那句"上。
- 模板只负责画一"版"（一块板），不擦板；场景最后调用 end_erase(s)，
  同一场景里换版用 next_panel(s, i)（在第 i 句开头擦板）。
- 人物用人物库 id（如 "sam_altman"）。人物朝向：person.json 的 facing，
  面朝右的放左边、面朝左的放右边，画面才是"两人对视"。
"""
import math, random
from PIL import Image, ImageDraw
from wb import (Scene, El, Stroke, Text, Img, Fill, Portrait, line, poly, rect, ellipse, arrow, underline,  # noqa
                wavy, hachure, speed_lines, crack, stick_person, bubble, year_box, stamp_img, sfx_img,
                not_nonsense, ellipse_pts, font, clamp, ease, INK, RED, GRAY, YELLOW, W, H)
import people

BRAND = "硅基废话"
SLOGAN = "都是废话，盖了章的除外"
AI_LABEL = "AI 合成配音"
TX, TTOP, TBOT = 1846, 600, 830         # 关系温度计位置（右下角）
COLD = (40, 90, 170)


# =============================================================== 品牌固定元素
class Mercury(El):
    chain = False
    z = 1

    def __init__(self, lv0, lv1, t0, t1, start, **kw):
        super().__init__(at=start, dur=max(0.05, t1 - start), tag="thermo", **kw)
        self.lv0, self.lv1, self.t0, self.t1 = lv0, lv1, t0, t1

    def bbox(self):
        return (TX - 40, TTOP - 10, TX + 40, TBOT + 70)

    def level(self, t):
        if t <= self.t0:
            return self.lv0
        return self.lv0 + (self.lv1 - self.lv0) * ease((t - self.t0) / max(0.01, self.t1 - self.t0))

    def render(self, p):
        lv = self.level(self.start + p * self.dur)
        x0, y0, x1, y1 = self.bbox()
        im = Image.new("RGBA", ((x1 - x0) * 2, (y1 - y0) * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        top = TBOT - lv * (TBOT - TTOP - 14)
        d.rectangle([(TX - 8 - x0) * 2, (top - y0) * 2, (TX + 8 - x0) * 2, (TBOT + 10 - y0) * 2], fill=RED)
        d.ellipse([(TX - 22 - x0) * 2, (TBOT + 8 - y0) * 2, (TX + 22 - x0) * 2, (TBOT + 52 - y0) * 2], fill=RED)
        return im.reduce(2)


def thermo(s, lv0, lv1=None, t_change=None, draw_at=None, label="关系温度"):
    """关系温度计（0=冰点，1=火热）。lv0→lv1 在 t_change 时变化；draw_at=None 表示开场已画好。
    跨场景保持连续：上一场景结束的 lv1 = 下一场景的 lv0。"""
    at = draw_at if draw_at is not None else -50.0
    lv1 = lv0 if lv1 is None else lv1
    t0 = t_change if t_change is not None else at
    # 并行、固定时长：不管当时画面上在排什么队，都在 draw_at 后约 1.2 秒内画完
    k = dict(chain=False, tag="thermo")
    s.add(Stroke([([(TX - 15, TBOT), (TX - 15, TTOP), (TX + 15, TTOP), (TX + 15, TBOT)], False)], INK, 4, seed=61,
                 at=at, dur=0.5, **k),
          ellipse(TX, TBOT + 30, 30, 30, INK, 4, seed=62, turns=1.02, at=at + 0.45, dur=0.3, **k),
          Stroke([([(TX + 15, TTOP + 30 + j * 60), (TX + 30, TTOP + 30 + j * 60)], False) for j in range(4)],
                 INK, 3, seed=63, at=at + 0.5, dur=0.25, **k),
          Text(TX, TTOP - 58, label, 26, INK, "center", bold=0.6, at=at + 0.7, dur=0.4, **k),
          Text(TX + 44, TTOP + 14, "热", 24, RED, "center", bold=0.6, at=at + 0.75, dur=0.15, **k),
          Text(TX + 44, TBOT - 26, "冷", 24, COLD, "center", bold=0.6, at=at + 0.9, dur=0.15, **k))
    s.add(Mercury(lv0, lv1, t0, t0 + 1.4, at + (0.8 if draw_at is not None else 0)))


def watermark(s, draw_at=None):
    """右上角水印 + AI 合成标识。每个场景都要调用；只在第一个场景传 draw_at 让它被画出来。"""
    at = draw_at if draw_at is not None else -50.0
    k = dict(chain=False, tag="wm")
    s.add(Text(1745, 38, BRAND, 40, INK, "center", bold=1.2, at=at, dur=0.6, **k),
          ellipse(1745, 64, 140, 36, INK, 3, seed=81, turns=1.05, at=at + 0.55, dur=0.4, **k),
          Text(1745, 110, AI_LABEL, 20, GRAY, "center", bold=0, at=at + 0.9, dur=0.3, **k))


def circle_text(el, color=RED, seed=0, pad=18, **kw):
    """红笔圈住一个文字元素"""
    x0, y0, x1, y1 = el.bbox()
    return ellipse((x0 + x1) / 2, (y0 + y1) / 2 + 4, (x1 - x0) / 2 + pad, (y1 - y0) / 2 + pad * 0.3, color, 5,
                   seed=seed, **kw)


def under(el, color=RED, w=6, seed=0, **kw):
    """给文字元素画下划线"""
    x0, y0, x1, y1 = el.bbox()
    return underline(x0 + 14, x1 - 14, y1 - 6, color, w, seed=seed, **kw)


def fist(x_sh, y_sh, x_f, y_f, sleeve=(60, 70, 100), seed=0, **kw):
    """举起的拳头：袖子线 + 圆拳（配合小尺寸 Portrait 用）"""
    arm = Stroke([([(x_sh, y_sh), ((x_sh + x_f) / 2 + 8, (y_sh + y_f) / 2), (x_f, y_f + 26)], False)], sleeve, 16,
                 passes=1, seed=seed, **kw)
    return [arm, Fill(ellipse_pts(x_f, y_f, 24, 26, random.Random(seed), 1.0, 30), (240, 206, 176), z=2, chain=False),
            ellipse(x_f, y_f, 24, 26, INK, 4, seed=seed + 1, turns=1.02, z=3),
            Stroke([([(x_f - 14, y_f - 10 + k * 8), (x_f + 12, y_f - 12 + k * 8)], False) for k in range(3)],
                   INK, 2, passes=1, seed=seed + 2, z=3)]


def end_erase(s):
    """场景结尾擦板（温度计、水印保留）。每个场景最后都要调用。"""
    s.erase(s.T - 0.62, keep=("thermo", "wm"))


def next_panel(s, sent, dur=0.45):
    """同一场景内换一块板：在第 sent 句开头擦掉当前内容（年份框、温度计、水印保留）"""
    s.erase(s.t(sent, 0.0), dur=dur, keep=("thermo", "wm", "year"))


def person_name(pid):
    return people.load(pid).get("name_zh", pid)


def person_org(pid):
    return people.load(pid).get("org", "")


# =============================================================== 版式模板
# 所有模板都用"并行 + 明确时间"：每个元素 chain=False，at 相对它所属那句的时间，
# dur 取短值。这样句子再短，画面也跟得上旁白（新闻类视频句子通常很短）。
P = dict(chain=False)


def _txt_dur(text, per=0.06, lo=0.35, hi=1.4):
    return max(lo, min(hi, len(text) * per))


def title_page(s, title, left=None, right=None, crack_sent=None, name_sent=1, first=True):
    """开场标题页：大标题 + 双下划线；可选左右两个人物 + 名字；可选中间裂缝（对立感）。
    first=True 时同时画出水印（整期第一个场景用）。"""
    watermark(s, draw_at=0.05 if first else None)
    t0 = s.t(0, 0.0)
    td = _txt_dur(title, 0.12, 0.6, 1.3)
    t = Text(960, 110, title, 120, INK, "center", bold=2, at=t0, dur=td, **P)
    x0, _, x1, _ = t.bbox()
    s.add(t, underline(x0 + 40, x1 - 40, 262, RED, 9, double=True, seed=21, at=t0 + td, dur=0.5, **P))
    for x, pid in ((440, left), (1480, right)):
        if pid:
            s.add(Portrait(pid, x, 1080, 0.82, at=s.t(0, 0.3), dur=1.2, **P))
    if name_sent < len(s.ctx.st):
        for x, pid in ((440, left), (1480, right)):
            if pid:
                n0 = s.t(name_sent, 0.05)
                s.add(Text(x, 385, person_name(pid), 44, INK, "center", bold=1, at=n0, dur=0.6, **P),
                      Text(x, 440, person_org(pid), 34, GRAY, "center", bold=0.6, at=n0 + 0.6, dur=0.4, **P))
    if crack_sent is not None:
        s.add(crack(960, 340, 930, seed=8, at=s.t(crack_sent, 0.4), dur=0.8, **P))


def profile_pair(s, left, right, left_rows, right_rows, left_sent=0, right_sent=1, mark_last=True):
    """两人档案页：左人+右侧文字卡，右人+左侧文字卡。rows 是若干行短句（不带圆点，自动加）。"""
    for pid, px, tx, rows, sent, mark in ((left, 320, 600, left_rows, left_sent, "circle"),
                                          (right, 1590, 1000, right_rows, right_sent, "under")):
        t0 = s.t(sent, 0.0)
        s.add(Portrait(pid, px, 1080, 0.8, at=t0, dur=1.2, **P),
              Text(tx, 170, person_name(pid), 54, INK, bold=1.4, at=t0 + 0.05, dur=0.7, **P))
        e = None
        n = max(1, len(rows))
        for k, r in enumerate(rows):
            e = Text(tx, 262 + k * 66, "· " + r, 34, INK, bold=0.8, at=s.t(sent, 0.15 + 0.7 * k / n),
                     dur=_txt_dur(r, 0.05, 0.3, 0.9), **P)
            s.add(e)
        if e is not None and mark_last:
            s.add((circle_text if mark == "circle" else under)(e, seed=5 if mark == "circle" else 6,
                                                              at=e.end, dur=0.4, **P))


def compare_table(s, title, left_head, right_head, rows, head_sent=0, mark=None, stamp_row=None):
    """左右对比表。rows = [(左文字, 右文字, 左出现的句, 右出现的句)]，句也可以写成 (句, 比例)。
    mark = 要红圈强调的行号；stamp_row = 在该行右侧盖「不是废话」章。"""
    t0 = s.t(head_sent, 0.0)
    s.add(Text(960, 60, title, 64, INK, "center", bold=1.8, at=t0, dur=_txt_dur(title, 0.1, 0.5, 1.0), **P),
          line((960, 170), (960, 900), INK, 4, seed=93, at=t0 + 0.4, dur=0.4, **P),
          Text(480, 160, left_head, 54, INK, "center", bold=1.6, at=t0 + 0.5, dur=0.6, **P),
          Text(1420, 160, right_head, 54, RED, "center", bold=1.6, at=t0 + 0.8, dur=0.6, **P))
    y = 270
    for k, (lt, rt, la, ra) in enumerate(rows):
        la = la if isinstance(la, tuple) else (la, 0.05)
        ra = ra if isinstance(ra, tuple) else (ra, 0.5)
        le = Text(110, y, lt, 36, INK, bold=0.9, at=s.t(*la), dur=_txt_dur(lt), **P)
        re = Text(1010, y, rt, 36, INK, bold=0.9, at=s.t(*ra), dur=_txt_dur(rt), **P)
        s.add(le, re)
        if mark == k:
            s.add(circle_text(le, seed=94, at=le.end, dur=0.4, **P), circle_text(re, seed=95, at=re.end, dur=0.4, **P))
        if stamp_row == k:
            s.add(not_nonsense(1560, y + 120, rot=10, at=re.end + 0.3, **P))
        y += 100 if len(rows) > 5 else 112


def timeline(s, title, events, left=None, right=None, title_sent=0):
    """横向时间线：events = [(年份, 说明（可含\\n）, 句, 比例)]，最多 4 个节点。两侧可放小人像。"""
    t0 = s.t(title_sent, 0.0)
    t = Text(960, 70, title, 72, INK, "center", bold=1.8, at=t0, dur=_txt_dur(title, 0.1, 0.5, 1.0), **P)
    s.add(t, under(t, seed=8, at=t.end, dur=0.3, **P))
    for pid, px in ((left, 220), (right, 1650)):
        if pid:
            s.add(Portrait(pid, px, 1080, 0.6, at=t0 + 0.2, dur=1.0, **P))
    n = len(events)
    xs = [960] if n == 1 else [560 + i * (800 / (n - 1)) for i in range(n)]
    first_at = min(s.t(events[0][2], max(0.0, events[0][3] - 0.05)), t0 + 0.8)
    s.add(line((440, 300), (1480, 296), INK, 5, seed=60, at=first_at, dur=0.5, **P))
    for k, ((yr, txt, i, f), x) in enumerate(zip(events, xs)):
        a = s.t(i, f)
        s.add(ellipse(x, 298, 12, 12, RED, 7, seed=61 + k, turns=1.3, at=a, dur=0.2, **P),
              Text(x, 318, yr, 42, RED, "center", bold=1.2, at=a + 0.2, dur=0.4, **P),
              Text(x, 375, txt, 34, INK, "center", bold=0.8, at=a + 0.5, dur=_txt_dur(txt, 0.05, 0.3, 0.9), **P))


def big_number(s, number, caption, sent=0, frac=0.05, note=None, stamp=True, pid=None):
    """数字冲击页：超大红色数字 + 说明 + 红圈 + 可选「不是废话」章；可选左侧人物"""
    cx = 1100 if pid else 960
    a = s.t(sent, frac)
    if pid:
        s.add(Portrait(pid, 380, 1080, 0.8, at=s.t(sent, 0.0), dur=1.0, **P))
    n = Text(cx, 250, number, 190, RED, "center", bold=3, at=a, dur=0.6, **P)
    s.add(n, circle_text(n, seed=31, pad=30, at=a + 0.6, dur=0.4, **P),
          Text(cx, 590, caption, 54, INK, "center", bold=1.4, at=a + 0.7, dur=_txt_dur(caption, 0.07, 0.4, 1.0), **P))
    if note:
        s.add(Text(cx, 680, note, 32, GRAY, "center", bold=0.4, at=a + 1.2, dur=_txt_dur(note, 0.04, 0.3, 0.8), **P))
    if stamp:
        x0, y0, x1, y1 = n.bbox()
        s.add(not_nonsense(min(1560, x1 + 190), max(170, y0 - 10), rot=12, at=a + 1.1, **P))   # 放在红圈外


def quote(s, pid, text, sent, side="right", author=True, size=38):
    """金句页：人物 + 漫画对白气泡（text 用 \\n 分行，每行 ≤18 字）。side=人物在哪边。只放真实说过的话。"""
    px = 1500 if side == "right" else 420
    a = s.t(sent, 0.0)
    s.add(Portrait(pid, px, 1080, 0.8, at=a, dur=1.0, **P))
    lines = text.split("\n")
    w = max(len(l) for l in lines) * size * 0.55 + 90
    hgt = len(lines) * size * 0.75 + 70
    bx = 820 if side == "right" else 1100
    tail = (px - 260, 560) if side == "right" else (px + 260, 560)
    b = bubble(bx, 330, w, hgt, tail, text, size, seed=16, at=a + 0.3)
    for e in b:                       # 气泡各部分并行，文字写得快一点
        e.chain = False
        e.at = a + 0.3 if not isinstance(e, Text) else a + 0.6
        if isinstance(e, Text):
            e.dur = _txt_dur(text, 0.05, 0.5, 1.6)
        elif isinstance(e, Stroke):
            e.dur = 0.4
    s.add(b)
    if author:
        s.add(Text(bx + w - 60, 330 + hgt + 20, "—— " + person_name(pid), 30, RED, "right", bold=0.8,
                   at=a + 0.7 + _txt_dur(text, 0.05, 0.5, 1.6), dur=0.5, **P))


def climax(s, left, right, sfx="咔嚓！", sent=0, frac=0.0, with_crack=True):
    """名场面：集中线 + 两人 + 裂缝 + 拟声字。只在整期最高潮用 1~2 次，用多了就不炸了。"""
    a = s.t(sent, frac)
    s.add(speed_lines(960, 560, 520, 400, seed=14, at=a, **P),
          Portrait(left, 380, 1080, 0.8, at=a + 0.2, dur=0.9, **P),
          Portrait(right, 1330, 1080, 0.8, at=a + 0.2, dur=0.9, **P))
    if with_crack:
        s.add(crack(960, 150, 950, seed=15, at=a + 0.5, dur=0.6, **P))
    s.add(Img(sfx_img(sfx), 960, 600, "pop", "c", at=a + 1.0, **P))


def bullets(s, title, items, pid=None, side="left", title_sent=0, mark_last=True):
    """要点清单：items = [(文字, 句, 比例)]。可选一侧人像。"""
    tx = 700 if (pid and side == "left") else 160
    t0 = s.t(title_sent, 0.0)
    s.add(Text(tx, 120, title, 64, INK, bold=1.8, at=t0, dur=_txt_dur(title, 0.1, 0.5, 1.0), **P))
    if pid:
        s.add(Portrait(pid, 330 if side == "left" else 1590, 1080, 0.8, at=t0 + 0.2, dur=1.0, **P))
    e = None
    for k, (txt, i, f) in enumerate(items):
        e = Text(tx, 260 + k * 92, "· " + txt, 44, INK, bold=1.1, at=s.t(i, f), dur=_txt_dur(txt, 0.07, 0.35, 1.0), **P)
        s.add(e)
    if e is not None and mark_last:
        s.add(under(e, seed=41, at=e.end, dur=0.35, **P))


def question(s, q, sent, sub="评论区聊聊"):
    """结尾提问页"""
    t = Text(960, 300, q, 130, INK, "center", bold=2.4, at=s.t(sent, 0.02))
    x0, _, x1, _ = t.bbox()
    s.add(t, wavy(x0 + 30, x1 - 30, 480, RED, 6, seed=105), Text(960, 520, sub, 56, RED, "center", bold=1.4))


def _meta():
    import json, os
    p = os.path.join(os.getcwd(), "episode.json")      # build.py 会切到期目录
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def end_card(s, sources=None, pids=None, extra_note=None, at=None):
    """片尾品牌卡（旁白结束后，静音）。sources / pids 不填就读 episode.json 的 sources / people
    （people 里的人物会自动生成照片署名）。时长由 episode.json 的 end_card_seconds 决定（默认 6.5 秒）。"""
    m = _meta()
    sources = sources if sources is not None else m.get("sources", "")
    pids = pids if pids is not None else m.get("people", [])
    te = at if at is not None else s.ctx.end + 0.5
    s.erase(te, dur=0.5)
    note = "配音为作者本人声音经 AI 克隆合成；“据报道”内容以原始报道为准"
    if extra_note:
        note += "；" + extra_note
    credits = ("人物照片来自 Wikimedia Commons，经裁剪、抠图、漫画化处理：\n" + people.credit_line(pids)) if pids else ""
    body = "资料来源：" + sources + ("\n" + credits if credits else "") + "\n" + note
    # 几路并行、明确时间：所有内容在 te+3.3 秒前画完，之后静止停留到结尾，
    # 保证资料来源和照片署名能被看清（CC BY 授权要求署名可见）
    s.add(Text(960, 250, BRAND, 150, INK, "center", bold=2.6, at=te + 0.6, chain=False, dur=0.8),
          ellipse(960, 345, 380, 120, RED, 6, seed=106, turns=1.06, at=te + 1.4, chain=False, dur=0.5),
          Text(960, 800, body, 22, GRAY, "center", bold=0, at=te + 1.0, chain=False, dur=0.9),
          Text(960, 500, SLOGAN, 48, INK, "center", bold=1.2, at=te + 1.9, chain=False, dur=0.7),
          Text(960, 610, "点赞 · 关注 · 评论区见", 40, GRAY, "center", bold=0.6, at=te + 2.5, chain=False, dur=0.6),
          not_nonsense(1400, 520, rot=12, at=te + 2.8, chain=False))
