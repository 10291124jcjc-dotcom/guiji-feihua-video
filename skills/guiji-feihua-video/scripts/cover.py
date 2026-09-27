"""封面：python cover.py <期>  → <期>/<成片名>-封面-4x3.png（油管/B站/推特）和 -封面-3x4.png（抖音/视频号）

episode.json 的 "cover"：
  tag     左上角系列标签，如 "硅基废话 · AI 圈恩怨录"
  top     第一行（黑字），如 "奥特曼 vs 阿莫迪"；竖版可用 top_34 分两行 ["奥特曼", "vs 阿莫迪"]
  title   主标题（红色大字，≤7 字最好），如 "从战友到对手"
  left / right   人物库 id（可只填一个或不填）
  crack   两人之间画裂缝（对立题材用），默认 true
"""
import json, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb                                        # noqa: E402
import people                                    # noqa: E402
from wb import Text, Portrait, crack, speed_lines, underline, ellipse, not_nonsense, INK, RED, PAPER  # noqa: E402


def paper(w, h):
    base = np.full((h, w, 3), PAPER, np.float32) + np.random.default_rng(3).normal(0, 2.0, (h, w, 1))
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")


def put(cv, el):
    for e in (el if isinstance(el, list) else [el]):
        x0, y0 = e.bbox()[:2]
        im = e.final()
        sx, sy = max(0, -x0), max(0, -y0)
        ex, ey = min(im.width, cv.width - x0), min(im.height, cv.height - y0)
        if ex > sx and ey > sy:
            cv.alpha_composite(im, (x0 + sx, y0 + sy), (sx, sy, ex, ey))


def tag(cv, x, y, text):
    t = Text(x, y, text, 40, INK, bold=1.2)
    b = t.bbox()
    put(cv, [ellipse((b[0] + b[2]) / 2, (b[1] + b[3]) / 2 + 4, (b[2] - b[0]) / 2 + 20, 42, RED, 5, seed=3), t])


def fit(text, size, maxw):
    f = wb.font(size)
    while size > 40 and f.getlength(text) > maxw:
        size -= 6
        f = wb.font(size)
    return size


def cover_43(c):
    W, H = 1440, 1080
    cv = paper(W, H)
    put(cv, speed_lines(720, 620, 360, 300, n=70, seed=5))
    tag(cv, 70, 60, c.get("tag", "硅基废话"))
    if c.get("top"):
        put(cv, Text(720, 150, c["top"], fit(c["top"], 92, 1150), INK, "center", bold=2))
    ts = fit(c["title"], 150, 1100)
    t = Text(720, 280, c["title"], ts, RED, "center", bold=3)
    b = t.bbox()
    put(cv, [t, underline(b[0] + 30, b[2] - 30, 470, INK, 10, double=True, seed=9)])
    l, r = c.get("left"), c.get("right")
    if l and r:
        put(cv, Portrait(l, 330, H + 60, 0.88))
        put(cv, Portrait(r, 1110, H + 60, 0.88))
        if c.get("crack", True):
            put(cv, crack(720, 540, 1040, amp=26, seed=11))
    elif l or r:
        put(cv, Portrait(l or r, 720, H + 60, 0.95))
    put(cv, not_nonsense(min(1300, b[2] + 90), 250, rot=14))
    put(cv, wb.rect(18, 18, W - 18, H - 18, INK, 8, seed=7))
    return cv


def cover_34(c):
    W, H = 1080, 1440
    cv = paper(W, H)
    put(cv, speed_lines(540, 960, 330, 300, n=70, seed=6))
    tag(cv, 70, 60, c.get("tag", "硅基废话"))
    tops = c.get("top_34") or ([c["top"]] if c.get("top") else [])
    y = 180
    for line in tops:
        put(cv, Text(540, y, line, fit(line, 110, 900), INK, "center", bold=2.4))
        y += 140
    ts = fit(c["title"], 132, 900)
    t = Text(540, y + 20, c["title"], ts, RED, "center", bold=3)
    b = t.bbox()
    put(cv, [t, underline(130, 950, b[3] + 20, INK, 10, double=True, seed=9)])
    l, r = c.get("left"), c.get("right")
    if l and r:
        put(cv, Portrait(l, 270, H - 30, 0.9))
        put(cv, Portrait(r, 810, H - 30, 0.9))
        if c.get("crack", True):
            put(cv, crack(540, b[3] + 120, 1400, amp=24, seed=12))
    elif l or r:
        put(cv, Portrait(l or r, 540, H - 30, 1.0))
    put(cv, not_nonsense(860, b[3] + 100, rot=14))
    put(cv, wb.rect(18, 18, W - 18, H - 18, INK, 8, seed=7))
    return cv


def main():
    ep = os.path.abspath(sys.argv[1])
    people.set_episode(ep)
    meta = json.load(open(os.path.join(ep, "episode.json"), encoding="utf-8"))
    name = meta.get("output_name") or f"{meta.get('brand', '硅基废话')}｜{meta['title']}"
    c = meta["cover"]
    for suffix, fn in (("封面-4x3", cover_43), ("封面-3x4", cover_34)):
        p = os.path.join(ep, f"{name}-{suffix}.png")
        fn(c).convert("RGB").save(p)
        print(p)


if __name__ == "__main__":
    main()
