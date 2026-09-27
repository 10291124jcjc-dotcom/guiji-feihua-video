"""「硅基废话」白板 × 黑白漫画 动画引擎（详细用法见 references/engine-api.md）：元素按旁白节拍一笔一笔画出来。

元素统一接口：
  bbox()          → (x0, y0, x1, y1) 屏幕坐标（1x）
  render(p)       → RGBA 图（bbox 大小），p∈[0,1] 为绘制进度
  pen(p)          → 笔尖位置 (x, y) 或 None
  dur             → 绘制时长（秒），可自动估算
"""
import math, os, random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
SS = 2
INK = (24, 24, 26)
RED = (212, 46, 36)
GRAY = (120, 120, 126)
YELLOW = (246, 206, 70)
PAPER = (248, 247, 243)
KAI = "C:/Windows/Fonts/simkai.ttf"
HEI = "C:/Windows/Fonts/msyhbd.ttc"
PEN_SPEED = 1100          # 描边 px/s
FILL_SPEED = 7000         # 斜线填充 px/s
GAP = 0.12                # 抬笔间隙

_fonts = {}


def font(size, path=KAI):
    k = (size, path)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, int(size))
    return _fonts[k]


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


# =============================================================== 手绘路径
def _jit_seg(p0, p1, rnd, bow=0.012, jit=1.5):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0) or 1
    nx, ny = -(y1 - y0) / L, (x1 - x0) / L
    b = rnd.uniform(-bow, bow) * L
    n = max(2, int(L / 16))
    pts = []
    for i in range(n + 1):
        t = i / n
        off = b * 4 * t * (1 - t)
        pts.append((x0 + (x1 - x0) * t + nx * off, y0 + (y1 - y0) * t + ny * off))
    pts[0] = (pts[0][0] + rnd.uniform(-jit, jit), pts[0][1] + rnd.uniform(-jit, jit))
    pts[-1] = (pts[-1][0] + rnd.uniform(-jit, jit), pts[-1][1] + rnd.uniform(-jit, jit))
    return pts


def rough_poly(pts, rnd, closed=False):
    seq = list(pts) + ([pts[0]] if closed else [])
    out = []
    for i in range(len(seq) - 1):
        s = _jit_seg(seq[i], seq[i + 1], rnd)
        out += s if not out else s[1:]
    return out


def rough_curve(pts, rnd, amp=1.2):
    """平滑曲线（已密集采样）上加轻微抖动"""
    ph = rnd.uniform(0, 6)
    return [(x + math.sin(i * 0.35 + ph) * amp * 0.6 + rnd.uniform(-amp, amp) * 0.3,
             y + math.cos(i * 0.31 + ph) * amp * 0.6 + rnd.uniform(-amp, amp) * 0.3) for i, (x, y) in enumerate(pts)]


def ellipse_pts(cx, cy, rx, ry, rnd, turns=1.08, n=72):
    a0 = rnd.uniform(0, math.tau)
    k = rnd.uniform(-0.04, 0.04)
    out = []
    for i in range(int(n * turns) + 1):
        a = a0 + math.tau * i / n
        r = 1 + k * math.sin(a * 2) + rnd.uniform(-0.01, 0.01)
        out.append((cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r))
    return out


def bezier(p0, p1, p2, n=30):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def _cum(pts):
    c = [0.0]
    for i in range(1, len(pts)):
        c.append(c[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    return c


def _prefix(pts, cum, target):
    if target >= cum[-1]:
        return pts
    if target <= 0:
        return pts[:1]
    k = int(np.searchsorted(cum, target))
    k = max(1, min(k, len(pts) - 1))
    f = (target - cum[k - 1]) / max(1e-6, cum[k] - cum[k - 1])
    x = pts[k - 1][0] + (pts[k][0] - pts[k - 1][0]) * f
    y = pts[k - 1][1] + (pts[k][1] - pts[k - 1][1]) * f
    return pts[:k] + [(x, y)]


def clip_convex(p0, p1, poly):
    """线段与凸多边形求交（Cyrus-Beck）"""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        nx, ny = -(by - ay) * sgn, (bx - ax) * sgn       # 内法线
        num = nx * (x0 - ax) + ny * (y0 - ay)
        den = nx * dx + ny * dy
        if abs(den) < 1e-9:
            if num < 0:
                return None
            continue
        t = -num / den
        if den > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return (x0 + dx * t0, y0 + dy * t0), (x0 + dx * t1, y0 + dy * t1)


# =============================================================== 元素基类
class El:
    z = 1
    persistent = False
    dur = 0.5
    chain = True

    def __init__(self, at=None, dur=None, z=None, chain=None, persistent=None, tag=None):
        self.at = at
        if dur is not None:
            self.dur = dur
        if z is not None:
            self.z = z
        if chain is not None:
            self.chain = chain
        if persistent is not None:
            self.persistent = persistent
        self.tag = tag
        self.start = self.end = None
        self._final = None

    def final(self):
        if self._final is None:
            self._final = self.render(1.0)
        return self._final

    def pen(self, p):
        return None


class Stroke(El):
    """任意手绘线：paths = [(pts, closed), ...]，每条路径双遍描边（第二遍稍滞后）"""

    def __init__(self, paths, color=INK, w=4, passes=2, speed=PEN_SPEED, seed=0, smooth=False, **kw):
        super().__init__(**kw)
        rnd = random.Random(seed)
        self.color, self.w, self.passes = color, w, passes
        self.paths = []
        for pts, closed in paths:
            passes_pts = []
            for k in range(passes):
                if smooth:
                    pp = rough_curve(list(pts) + ([pts[0]] if closed else []), rnd, amp=1.2 + k * 0.6)
                else:
                    pp = rough_poly(pts, rnd, closed)
                passes_pts.append((pp, _cum(pp)))
            self.paths.append(passes_pts)
        self.L = sum(pp[0][1][-1] for pp in self.paths)
        if "dur" not in kw or kw["dur"] is None:
            self.dur = clamp(self.L / speed, 0.3, 3.0)
        xs = [x for pp in self.paths for pts, _ in pp for x, _ in pts]
        ys = [y for pp in self.paths for pts, _ in pp for _, y in pts]
        m = w * 2 + 4
        self._bb = (int(min(xs) - m), int(min(ys) - m), int(max(xs) + m) + 1, int(max(ys) + m) + 1)

    def bbox(self):
        return self._bb

    def _walk(self, p):
        target = p * self.L
        acc = 0.0
        out = []
        for pp in self.paths:
            la = pp[0][1][-1]
            if target <= acc:
                break
            out.append((pp, target - acc))
            acc += la
        return out

    def render(self, p):
        x0, y0, x1, y1 = self._bb
        im = Image.new("RGBA", ((x1 - x0) * SS, (y1 - y0) * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for pp, tgt in self._walk(p):
            for k, (pts, cum) in enumerate(pp):
                t = tgt if k == 0 else tgt - 0.05 * cum[-1]
                if t <= 0:
                    continue
                seg = _prefix(pts, cum, t)
                if len(seg) < 2:
                    continue
                ww = max(1, int(self.w * SS * (1 if k == 0 else 0.62)))
                d.line([((x - x0) * SS, (y - y0) * SS) for x, y in seg], fill=self.color, width=ww, joint="curve")
                r = ww / 2
                for (x, y) in (seg[0], seg[-1]):
                    d.ellipse([(x - x0) * SS - r, (y - y0) * SS - r, (x - x0) * SS + r, (y - y0) * SS + r],
                              fill=self.color)
        return im.reduce(SS)

    def pen(self, p):
        w = self._walk(p)
        if not w:
            return self.paths[0][0][0][0] if self.paths else None
        pp, tgt = w[-1]
        pts, cum = pp[0]
        return _prefix(pts, cum, tgt)[-1]


class Text(El):
    """手写文字：逐字写出（按行裁切露出），笔尖跟随"""

    def __init__(self, x, y, text, size=40, color=INK, align="left", bold=0.8, fnt=KAI, spacing=1.3, **kw):
        super().__init__(**kw)
        self.lines = text.split("\n")
        f = font(size, fnt)
        self.size = size
        lh = int(size * spacing)
        widths = [f.getlength(l) for l in self.lines]
        tw = int(max(widths)) + 12
        pad = int(size * 0.25) + 4
        self.img = Image.new("RGBA", (tw + pad * 2, lh * len(self.lines) + pad * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.img)
        self.line_x = []
        for i, l in enumerate(self.lines):
            lx = pad + ((tw - widths[i]) / 2 if align == "center" else (tw - widths[i]) if align == "right" else 0)
            # 纸色描边垫底：压在集中线/网点上也清楚
            d.text((lx, pad + i * lh), l, font=f, fill=PAPER + (230,), stroke_width=int(round(bold)) + 6,
                   stroke_fill=PAPER + (230,))
            d.text((lx, pad + i * lh), l, font=f, fill=color, stroke_width=max(0, int(round(bold))), stroke_fill=color)
            self.line_x.append(lx)
        self.pad, self.lh, self.f = pad, lh, f
        if align == "center":
            x -= self.img.width / 2
        elif align == "right":
            x -= self.img.width
        self.x, self.y = int(x - pad), int(y - pad)
        units = [sum(0.5 if ord(c) < 128 else 1.0 for c in l) for l in self.lines]
        self.units = units
        cs = clamp(size / 700, 0.055, 0.2)
        if kw.get("dur") is None:
            self.dur = max(0.35, sum(units) * cs)

    def bbox(self):
        return (self.x, self.y, self.x + self.img.width, self.y + self.img.height)

    def _state(self, p):
        target = p * sum(self.units)
        acc = 0
        for i, (l, u) in enumerate(zip(self.lines, self.units)):
            if target <= acc + u:
                # 当前行写到第几个字
                need = target - acc
                k, s = 0, 0.0
                while k < len(l) and s + (0.5 if ord(l[k]) < 128 else 1) <= need:
                    s += 0.5 if ord(l[k]) < 128 else 1
                    k += 1
                frac = 0 if k >= len(l) else (need - s) / (0.5 if ord(l[k]) < 128 else 1)
                wpx = self.f.getlength(l[:k]) + (self.f.getlength(l[k]) * frac if k < len(l) else 0)
                return i, wpx
            acc += u
        return len(self.lines) - 1, self.f.getlength(self.lines[-1]) + 1

    def render(self, p):
        if p >= 1:
            return self.img
        li, wpx = self._state(p)
        mask = Image.new("L", self.img.size, 0)
        md = ImageDraw.Draw(mask)
        top = 0 if li == 0 else self.pad + li * self.lh - int(self.size * 0.12)
        if li > 0:
            md.rectangle([0, 0, self.img.width, top], fill=255)
        bottom = self.img.height if li == len(self.lines) - 1 else self.pad + (li + 1) * self.lh - int(self.size * 0.12)
        md.rectangle([0, top, self.line_x[li] + wpx, bottom], fill=255)
        out = self.img.copy()
        out.putalpha(Image.fromarray(np.minimum(np.array(self.img.getchannel("A")), np.array(mask))))
        return out

    def pen(self, p):
        li, wpx = self._state(p)
        return (self.x + self.line_x[li] + wpx,
                self.y + self.pad + li * self.lh + self.size * (0.55 + 0.18 * math.sin(p * 40)))


class Img(El):
    """预渲染图片：wipe（从左往右画出）/ pop（印章砸下）/ fade"""

    def __init__(self, img, x, y, mode="wipe", anchor="tl", **kw):
        super().__init__(**kw)
        self.img, self.mode = img, mode
        if anchor == "c":
            x, y = x - img.width / 2, y - img.height / 2
        elif anchor == "b":
            x, y = x - img.width / 2, y - img.height
        self.x, self.y = int(x), int(y)
        if kw.get("dur") is None:
            self.dur = {"wipe": clamp(img.width / 700, 0.6, 1.6), "pop": 0.35, "fade": 0.4}[mode]
        if mode == "pop":
            self.z = kw.get("z") or 3

    def bbox(self):
        if self.mode == "pop":
            m = int(max(self.img.size) * 0.45)
            return (self.x - m, self.y - m, self.x + self.img.width + m, self.y + self.img.height + m)
        return (self.x, self.y, self.x + self.img.width, self.y + self.img.height)

    def render(self, p):
        if self.mode == "wipe":
            if p >= 1:
                return self.img
            out = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
            wx = int(self.img.width * ease(p) + 2)
            out.paste(self.img.crop((0, 0, wx, self.img.height)), (0, 0))
            return out
        if self.mode == "fade":
            out = self.img.copy()
            out.putalpha(self.img.getchannel("A").point(lambda v: int(v * clamp(p))))
            return out
        # pop：从 1.7 倍砸到 1 倍
        bb = self.bbox()
        canvas = Image.new("RGBA", (bb[2] - bb[0], bb[3] - bb[1]), (0, 0, 0, 0))
        s = 1 + 0.7 * (1 - ease(p))
        im = self.img.resize((max(1, int(self.img.width * s)), max(1, int(self.img.height * s))), Image.BILINEAR)
        if p < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * clamp(p * 2.5))))
        cx, cy = self.x + self.img.width / 2 - bb[0], self.y + self.img.height / 2 - bb[1]
        canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
        return canvas

    def pen(self, p):
        if self.mode != "wipe":
            return None
        return (self.x + self.img.width * ease(p), self.y + self.img.height * (0.5 + 0.38 * math.sin(p * 9 * math.pi)))


class Fill(El):
    """实心填充（气泡白底、红色水银等），瞬时淡入"""
    dur = 0.15
    chain = False

    def __init__(self, poly, color, alpha=255, **kw):
        super().__init__(**kw)
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        self._bb = (int(min(xs)) - 2, int(min(ys)) - 2, int(max(xs)) + 3, int(max(ys)) + 3)
        x0, y0 = self._bb[:2]
        im = Image.new("RGBA", ((self._bb[2] - x0) * SS, (self._bb[3] - y0) * SS), (0, 0, 0, 0))
        ImageDraw.Draw(im).polygon([((x - x0) * SS, (y - y0) * SS) for x, y in poly], fill=color + (alpha,))
        self.img = im.reduce(SS)

    def bbox(self):
        return self._bb

    def render(self, p):
        if p >= 1:
            return self.img
        out = self.img.copy()
        out.putalpha(self.img.getchannel("A").point(lambda v: int(v * clamp(p))))
        return out


# =============================================================== 漫画人像
from people import manga_imgs, BODY_W   # noqa: E402  人物库（见 people.py）


def _fade_edges(im):
    w, h = im.size
    a = np.array(im.getchannel("A")).astype(np.float32)
    fade = np.clip((h - np.arange(h)) / (h * 0.22), 0, 1)[:, None]
    side = np.clip(np.arange(w) / (w * 0.14), 0, 1)
    side = np.minimum(side, side[::-1])[None, :]
    im = im.copy()
    im.putalpha(Image.fromarray((a * fade * side).astype(np.uint8)))
    return im


class Portrait(El):
    """先勾墨线（扫描式露出），再铺网点"""
    dur = 1.8

    def __init__(self, who, cx, bottom, scale=0.85, crop_bottom=None, **kw):
        super().__init__(**kw)
        full, line = manga_imgs(who)
        w = int(BODY_W * scale)
        h = int(full.height * w / full.width)
        self.full = _fade_edges(full.resize((w, h), Image.LANCZOS))
        self.line = _fade_edges(line.resize((w, h), Image.LANCZOS))
        if crop_bottom:
            self.full = self.full.crop((0, 0, w, crop_bottom))
            self.line = self.line.crop((0, 0, w, crop_bottom))
            h = crop_bottom
        self.x, self.y = int(cx - w / 2), int(bottom - h)
        self.z = kw.get("z") or 1

    def bbox(self):
        return (self.x, self.y, self.x + self.full.width, self.y + self.full.height)

    def render(self, p):
        if p >= 1:
            return self.full
        w, h = self.full.size
        if p < 0.6:
            q = ease(p / 0.6)
            out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            wy = int(h * q) + 2
            out.paste(self.line.crop((0, 0, w, wy)), (0, 0))
            return out
        q = (p - 0.6) / 0.4
        out = self.line.copy()
        f = self.full.copy()
        f.putalpha(self.full.getchannel("A").point(lambda v: int(v * q)))
        out.alpha_composite(f)
        return out

    def pen(self, p):
        w, h = self.full.size
        if p < 0.6:
            q = ease(p / 0.6)
            return (self.x + w * (0.5 + 0.36 * math.sin(p * 60)), self.y + h * q)
        q = (p - 0.6) / 0.4
        return (self.x + w * (0.3 + 0.4 * abs(math.sin(q * 14))), self.y + h * (0.25 + 0.5 * q))


# =============================================================== 常用画法（返回元素）
def line(p0, p1, color=INK, w=4, **kw):
    return Stroke([([p0, p1], False)], color, w, **kw)


def poly(pts, color=INK, w=4, closed=True, **kw):
    return Stroke([(pts, closed)], color, w, **kw)


def rect(x0, y0, x1, y1, color=INK, w=4, **kw):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], color, w, True, **kw)


def ellipse(cx, cy, rx, ry, color=INK, w=4, seed=0, turns=1.08, **kw):
    pts = ellipse_pts(cx, cy, rx, ry, random.Random(seed + 99), turns)
    return Stroke([(pts, False)], color, w, seed=seed, smooth=True, **kw)


def arrow(p0, p1, color=INK, w=4, curve=0.2, seed=0, **kw):
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2 - (y1 - y0) * curve, (y0 + y1) / 2 + (x1 - x0) * curve
    body = bezier(p0, (mx, my), p1, 30)
    ang = math.atan2(y1 - body[-4][1], x1 - body[-4][0])
    heads = []
    for s in (-1, 1):
        a = ang + math.pi + s * 0.5
        heads.append(([(x1, y1), (x1 + math.cos(a) * 24, y1 + math.sin(a) * 24)], False))
    return Stroke([(body, False)] + heads, color, w, seed=seed, smooth=True, **kw)


def underline(x0, x1, y, color=RED, w=6, double=False, seed=0, **kw):
    paths = [([(x0, y), (x1, y - 4)], False)]
    if double:
        paths.append(([(x0 + 30, y + 16), (x1 - 30, y + 13)], False))
    return Stroke(paths, color, w, seed=seed, **kw)


def wavy(x0, x1, y, color=RED, w=5, amp=8, seed=0, **kw):
    n = int((x1 - x0) / 6)
    pts = [(x0 + (x1 - x0) * i / n, y + amp * math.sin(i / n * (x1 - x0) / 28)) for i in range(n + 1)]
    return Stroke([(pts, False)], color, w, seed=seed, smooth=True, **kw)


def hachure(polygon, color=RED, gap=12, w=3, angle=-0.8, seed=0, **kw):
    xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    R = max(max(xs) - min(xs), max(ys) - min(ys))
    paths = []
    for k in range(-int(R / gap) - 2, int(R / gap) + 3):
        ox, oy = math.cos(angle + math.pi / 2) * k * gap, math.sin(angle + math.pi / 2) * k * gap
        p0 = (cx + ox - math.cos(angle) * R, cy + oy - math.sin(angle) * R)
        p1 = (cx + ox + math.cos(angle) * R, cy + oy + math.sin(angle) * R)
        seg = clip_convex(p0, p1, polygon)
        if seg and math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1]) > 3:
            paths.append(([seg[0], seg[1]] if k % 2 else [seg[1], seg[0]], False))
    return Stroke(paths, color, w, passes=1, speed=FILL_SPEED, seed=seed, **kw)


def speed_lines(cx, cy, rx, ry, n=80, seed=3, **kw):
    rnd = random.Random(seed)
    paths = []
    for i in range(n):
        a = math.tau * i / n + rnd.uniform(-0.02, 0.02)
        r0 = rnd.uniform(1.0, 1.3)
        p0 = (cx + math.cos(a) * rx * r0, cy + math.sin(a) * ry * r0)
        p1 = (cx + math.cos(a) * 1500, cy + math.sin(a) * 1500)
        paths.append(([p0, p1], False))
    kw.setdefault("z", 0)
    kw.setdefault("dur", 0.45)
    return Stroke(paths, (40, 40, 44), rnd.uniform(2, 4), passes=1, speed=40000, seed=seed, **kw)


def crack(x, y0, y1, amp=34, seed=7, **kw):
    rnd = random.Random(seed)
    pts, y = [], y0
    while y < y1:
        pts.append((x + rnd.uniform(-amp, amp), y))
        y += rnd.uniform(40, 80)
    pts.append((x, y1))
    return [Stroke([(pts, False)], RED, 13, passes=1, seed=seed, **kw),
            Stroke([(pts, False)], INK, 5, seed=seed + 1, chain=False, **{k: v for k, v in kw.items() if k not in ("at", "chain")})]


def stick_person(cx, bottom, h=150, seed=0, arms="down", **kw):
    r = h * 0.14
    hy = bottom - h + r
    neck = hy + r
    hip = bottom - h * 0.38
    paths = [(ellipse_pts(cx, hy, r, r, random.Random(seed), 1.05, 36), False),
             ([(cx, neck), (cx, hip)], False),
             ([(cx, hip), (cx - h * 0.16, bottom)], False), ([(cx, hip), (cx + h * 0.16, bottom)], False)]
    ay = neck + h * 0.12
    if arms == "down":
        paths += [([(cx, ay), (cx - h * 0.2, ay + h * 0.22)], False), ([(cx, ay), (cx + h * 0.2, ay + h * 0.22)], False)]
    elif arms == "wide":   # 伸手去牵旁边的人
        paths += [([(cx, ay), (cx - h * 0.34, ay + h * 0.12)], False), ([(cx, ay), (cx + h * 0.34, ay + h * 0.12)], False)]
    return Stroke(paths, INK, 4, seed=seed, **kw)


def bubble(cx, cy, rx, ry, tail, text, size=40, seed=0, at=None, **kw):
    """漫画对白气泡：白底 + 手绘椭圆 + 尾巴 + 文字"""
    pts = ellipse_pts(cx, cy, rx, ry, random.Random(seed), 1.0, 64)
    tx, ty = tail
    a = math.atan2(ty - cy, tx - cx)
    b0 = (cx + math.cos(a - 0.18) * rx * 0.92, cy + math.sin(a - 0.18) * ry * 0.92)
    b1 = (cx + math.cos(a + 0.18) * rx * 0.92, cy + math.sin(a + 0.18) * ry * 0.92)
    return [Stroke([(pts, False)], INK, 4, seed=seed, smooth=True, at=at, z=3, **kw),
            Fill(pts, (255, 255, 255), z=2, **kw),                       # 与轮廓同时出现，垫在下面
            Fill([b0, (tx, ty), b1], (255, 255, 255), z=2, **kw),
            Stroke([([b0, (tx, ty), b1], False)], INK, 4, seed=seed + 1, z=3, **kw),
            Text(cx, cy - size * 0.66 * text.count("\n") - size * 0.6, text, size, INK, "center", bold=1, z=3, **kw)]


def year_box(x, y, text, seed=11, at=0.0, **kw):
    f = font(58)
    w = f.getlength(text) + 60
    box = [(x, y), (x + w, y - 5), (x + w + 6, y + 92), (x - 4, y + 98)]
    return [rect(x, y, x + w, y + 94, INK, 5, seed=seed, at=at, **kw),
            hachure(box, YELLOW, gap=13, w=4, seed=seed, **kw),
            Text(x + w / 2, y + 12, text, 58, INK, "center", bold=1.4, **kw)]


def stamp_img(text, color=RED, size=72, rot=10, seed=4):
    f = ImageFont.truetype(HEI, size)
    tw = f.getlength(text)
    w, h = int(tw + 60), int(size * 1.7)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([5, 5, w - 5, h - 5], 12, outline=color + (235,), width=8)
    d.text((w / 2, h / 2), text, font=f, fill=color + (235,), anchor="mm")
    grain = (np.random.default_rng(seed).random((h, w)) > 0.16).astype(np.uint8)
    a = np.array(im)
    a[..., 3] = a[..., 3] * grain
    return Image.fromarray(a).rotate(rot, expand=True, resample=Image.BICUBIC)


def sfx_img(text, size=110, rot=-6):
    """漫画拟声字：白字粗黑描边 + 投影"""
    f = ImageFont.truetype(HEI, size)
    tw = f.getlength(text)
    w, h = int(tw + 60), int(size * 1.6)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((34, 26), text, font=f, fill=INK, stroke_width=9, stroke_fill=INK)
    d.text((26, 18), text, font=f, fill=(255, 255, 255), stroke_width=8, stroke_fill=INK)
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)


def not_nonsense(x, y, rot=10, at=None, **kw):
    """品牌梗：「不是废话」红章"""
    return Img(stamp_img("不是废话", rot=rot).resize((300, 150), Image.LANCZOS), x, y, "pop", "c", at=at, **kw)


# =============================================================== 笔 / 板擦 图形
def _pen_img():
    im = Image.new("RGBA", (220 * SS, 220 * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = SS
    # 以笔尖 (20,200) 为原点，笔身朝右上
    def P(x, y):
        return (x * k, y * k)
    d.ellipse([P(8, 188), P(40, 206)], fill=(0, 0, 0, 40))                         # 影子
    d.polygon([P(20, 200), P(46, 150), P(70, 174)], fill=(200, 204, 212), outline=INK)   # 金属笔尖
    d.line([P(20, 200), P(52, 168)], fill=INK, width=2 * k)
    d.ellipse([P(50, 164), P(58, 172)], fill=INK)
    d.polygon([P(46, 150), P(70, 174), P(78, 166), P(54, 142)], fill=(150, 154, 162), outline=INK)  # 笔夹
    d.polygon([P(54, 142), P(78, 166), P(196, 48), P(172, 24)], fill=INK)          # 黑色笔杆
    d.polygon([P(172, 24), P(196, 48), P(206, 38), P(182, 14)], fill=RED)          # 红色尾端（品牌色）
    return im.reduce(SS), (20, 200)


def _eraser_img():
    im = Image.new("RGBA", (260 * SS, 170 * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = SS
    d.rounded_rectangle([20 * k, 30 * k, 240 * k, 110 * k], 14 * k, fill=(40, 40, 44))
    d.rounded_rectangle([20 * k, 96 * k, 240 * k, 140 * k], 10 * k, fill=(236, 236, 230), outline=INK, width=3 * k)
    d.text((130 * k, 70 * k), "硅基废话", font=ImageFont.truetype(KAI, 34 * k), fill=(240, 240, 235), anchor="mm")
    return im.reduce(SS).rotate(8, expand=True, resample=Image.BICUBIC)


PEN, PEN_TIP = _pen_img()
ERASER = _eraser_img()


# =============================================================== 场景时间轴
class Scene:
    def __init__(self, ctx, nframes):
        self.ctx = ctx            # render.Ctx：句子开始时间 st / 时长 du
        self.n = nframes
        self.T = nframes / FPS
        self.els = []
        self.erases = []          # (t0, t1, 目标元素集合)
        self._erased = set()
        self.squeezed = []        # 被压缩的段落：(擦板时间, 压缩系数, 原本超出秒数)
        self.cursor = 0.0

    def t(self, i, frac=0.0):
        return self.ctx.st[i] + self.ctx.du[i] * frac

    def add(self, *els):
        """chain=True：接在上一笔之后画；chain=False 且没给 at：和上一个元素同时开始"""
        for e in els:
            if isinstance(e, (list, tuple)):
                self.add(*e)
                continue
            if e.chain:
                req = e.at if e.at is not None else self.cursor
                e.start = max(req, self.cursor)
            else:
                e.start = e.at if e.at is not None else (self.els[-1].start if self.els else 0.0)
            e.end = e.start + e.dur
            if e.chain:
                self.cursor = max(self.cursor, e.end + GAP)
            elif e.start >= 0:
                self.cursor = max(self.cursor, e.end)
            self.els.append(e)
        return self

    def erase(self, t0, dur=0.55, keep=("thermo", "wm", "year")):
        """擦掉这一段画的所有元素（tag 在 keep 里的保留）。
        如果这一段没来得及在 t0 前画完，就把这一段的时间轴整体压缩，保证擦板前全部画完。"""
        panel_start = self.erases[-1][1] if self.erases else 0.0
        panel = [e for e in self.els if e.tag not in keep and id(e) not in self._erased]
        deadline = t0 - 0.25
        late = max((e.end for e in panel), default=0)
        if late > deadline:
            movable = [e for e in panel if e.start >= panel_start]
            if movable:
                s0 = min(e.start for e in movable)
                k = max(0.05, (deadline - s0) / max(1e-6, late - s0))
                for e in movable:
                    e.start = s0 + (e.start - s0) * k
                    e.dur = max(0.08, e.dur * k)
                    e.end = e.start + e.dur
                self.squeezed.append((round(t0, 2), round(k, 2), round(late - deadline, 2)))
        targets = {id(e) for e in panel}
        self._erased |= targets
        self.erases.append((t0, t0 + dur, targets))
        self.cursor = max(t0 + dur + 0.1, self.cursor if self.cursor < t0 else t0 + dur + 0.1)

    def erased_at(self, e, t):
        """返回 None=正常；x=正在擦（x 左侧已擦掉）；True=已擦完"""
        for t0, t1, tg in self.erases:
            if id(e) in tg and t >= t0:
                if t >= t1:
                    return True
                return W * ease((t - t0) / (t1 - t0)) * 1.1 - 60
        return None


def paper():
    rnd = np.random.default_rng(2)
    base = np.full((H, W, 3), PAPER, np.float32) + rnd.normal(0, 2.0, (H, W, 1))
    ghost = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(ghost)
    r = random.Random(5)
    for _ in range(9):
        x, y = r.uniform(0, W), r.uniform(0, H)
        gd.line([(x, y), (x + r.uniform(200, 500), y + r.uniform(-40, 40))], fill=12, width=r.randint(20, 50))
    ghost = np.array(ghost.filter(ImageFilter.GaussianBlur(18)), np.float32)[..., None]
    base -= ghost * 0.55
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")


class Renderer:
    """逐帧渲染一个场景：已完成的元素烘焙进图层，正在画的元素每帧重绘"""

    def __init__(self, scene, overlays):
        self.s = scene
        self.overlays = overlays     # fn(canvas, t) → 画字幕/水印等
        self.bg = paper()
        self.baked = {}              # z → 图层
        self.baked_ids = []
        self.pen_last = None
        self.pen_last_t = -9

    def _rebuild(self, t):
        self.baked = {}
        keep = []
        for e in self.s.els:
            if id(e) in self.baked_ids and self.s.erased_at(e, t) is None:
                self._bake(e)
                keep.append(id(e))
        self.baked_ids = keep

    def _bake(self, e):
        layer = self.baked.setdefault(e.z, Image.new("RGBA", (W, H), (0, 0, 0, 0)))
        x0, y0 = e.bbox()[:2]
        _paste(layer, e.final(), x0, y0)

    def frame(self, t):
        s = self.s
        # 擦除开始时重建烘焙层
        if any(t0 <= t < t0 + 1.0 / FPS + 1e-6 for t0, _, _ in s.erases):
            self._rebuild(t)
        for e in s.els:
            if id(e) not in self.baked_ids and e.end <= t and s.erased_at(e, t) is None:
                self._bake(e)
                self.baked_ids.append(id(e))
        cv = self.bg.copy()
        pen = None
        erasing_x = None
        zs = sorted(set([e.z for e in s.els]) | set(self.baked))
        for z in zs:
            if z in self.baked:
                cv.alpha_composite(self.baked[z])
            for e in s.els:
                if e.z != z:
                    continue
                er = s.erased_at(e, t)
                if er is True:
                    continue
                if er is not None:                       # 正在被擦
                    erasing_x = er
                    if e.start > t:
                        continue
                    im = e.final() if t >= e.end else e.render(clamp((t - e.start) / e.dur))
                    x0, y0 = e.bbox()[:2]
                    cut = int(er - x0)
                    if cut < im.width:
                        _paste(cv, im.crop((max(0, cut), 0, im.width, im.height)), x0 + max(0, cut), y0)
                    continue
                if e.start <= t < e.end:
                    p = clamp((t - e.start) / e.dur)
                    x0, y0 = e.bbox()[:2]
                    _paste(cv, e.render(p), x0, y0)
                    pp = e.pen(p)
                    if pp:
                        pen = pp
        self.overlays(cv, t)
        # 板擦
        if erasing_x is not None:
            ey = 420 + 180 * math.sin(erasing_x / 180)
            _paste(cv, ERASER, int(erasing_x - 60), int(ey - ERASER.height / 2))
            self.pen_last = None
        # 笔：画的时候显示；短暂停顿时滑向下一笔的起点，否则收起
        if pen is None and erasing_x is None:
            nxt = [e for e in s.els if e.start > t and e.pen(0.0) is not None]
            nxt = min(nxt, key=lambda e: e.start) if nxt else None
            if self.pen_last and nxt and nxt.start - t < 0.7:
                q = clamp(1 - (nxt.start - t) / 0.7)
                target = nxt.pen(0.0)
                pen = (self.pen_last[0] + (target[0] - self.pen_last[0]) * ease(q),
                       self.pen_last[1] + (target[1] - self.pen_last[1]) * ease(q))
            elif self.pen_last and t - self.pen_last_t < 0.35:
                q = (t - self.pen_last_t) / 0.35
                pen = (self.pen_last[0] + 260 * ease(q), self.pen_last[1] + 200 * ease(q))
        else:
            if pen:
                self.pen_last, self.pen_last_t = pen, t
        if pen and erasing_x is None:
            _paste(cv, PEN, int(pen[0] - PEN_TIP[0]), int(pen[1] - PEN_TIP[1]))
        return cv


def _paste(cv, im, x, y):
    x, y = int(x), int(y)
    w, h = im.size
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(w, W - x), min(h, H - y)
    if ex > sx and ey > sy:
        cv.alpha_composite(im, (x + sx, y + sy), (sx, sy, ex, ey))
