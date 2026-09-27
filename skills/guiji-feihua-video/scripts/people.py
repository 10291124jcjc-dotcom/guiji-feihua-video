"""人物库：每个人物一个文件夹 <库>/<id>/，里面有 photo.jpg + person.json，
漫画化结果缓存在 <id>/cache/，跨期复用。

查找顺序（先找到先用）：
  1. <期目录>/people/<id>
  2. <视频根目录>/people/<id>      （期目录的上两级，即 视频/episodes/<期> → 视频/people）
  3. <skill>/assets/people/<id>     （自带的种子人物）

person.json 字段：
  name_zh, name_en
  photo           照片文件名
  crop            [x0, y0, x1, y1]  在原图上裁出半身像（宽:高≈3:4）
  mirror          是否水平翻转（让人物朝向画面中间）
  sure_fg/sure_bg 抠图提示：[["ell", [cx, cy, rx, ry]] 或 ["rect", [x0, y0, x1, y1]]]，坐标在 900×1200 工作图上
  fade_corner     可选 {"from_y": 700, "ramp": 100, "width": 160}：把工作图右下角渐隐（用于清理残留背景）
  credit          {"file", "author", "license", "url"}：片尾和简介必须署名
"""
import json, math, os
import cv2
import numpy as np
from PIL import Image

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK_W, WORK_H = 900, 1200
BODY_W = 540                      # 漫画人像的基准宽度（Portrait scale=1 时）

_search = []


def set_episode(ep_dir):
    global _search
    ep_dir = os.path.abspath(ep_dir)
    _search = [os.path.join(ep_dir, "people"),
               os.path.join(os.path.dirname(os.path.dirname(ep_dir)), "people"),
               os.path.join(SKILL_DIR, "assets", "people")]


def library_dir():
    """新人物默认存放的位置：视频根目录/people"""
    if not _search:
        set_episode(os.getcwd())
    return _search[1]


def find(pid):
    if not _search:
        set_episode(os.getcwd())
    for base in _search:
        d = os.path.join(base, pid)
        if os.path.exists(os.path.join(d, "person.json")):
            return d
    raise SystemExit(f"✗ 人物库里没有 {pid}：先运行 add_person.py 添加（查找过：{_search}）")


def load(pid):
    d = find(pid)
    with open(os.path.join(d, "person.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["dir"] = d
    cfg["id"] = pid
    return cfg


def imread(path):
    return cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)


def work_image(cfg):
    img = imread(os.path.join(cfg["dir"], cfg["photo"]))
    x0, y0, x1, y1 = cfg["crop"]
    return cv2.resize(img[y0:y1, x0:x1], (WORK_W, WORK_H), interpolation=cv2.INTER_AREA)


def _shape(mask, kind, v, val):
    if kind == "ell":
        cx, cy, rx, ry = v
        cv2.ellipse(mask, (int(cx), int(cy)), (int(rx), int(ry)), 0, 0, 360, val, -1)
    else:
        x0, y0, x1, y1 = [int(t) for t in v]
        mask[y0:y1, x0:x1] = val


def cutout(img, cfg):
    """GrabCut 抠图 → 0/255 的 alpha（轻微羽化）"""
    mask = np.full(img.shape[:2], cv2.GC_PR_BGD, np.uint8)
    mask[40:, 60:-60] = cv2.GC_PR_FGD
    for k, v in cfg.get("sure_bg", []):
        _shape(mask, k, v, cv2.GC_BGD)
    for k, v in cfg.get("sure_fg", []):
        _shape(mask, k, v, cv2.GC_FGD)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(img, mask, None, bgd, fgd, 8, cv2.GC_INIT_WITH_MASK)
    m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)          # 只留最大连通域
    if n > 1:
        big = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        m = np.where(lab == big, 255, 0).astype(np.uint8)
    inv = 255 - m                                                    # 填内部小洞
    n, lab, stats, _ = cv2.connectedComponentsWithStats(inv)
    for i in range(1, n):
        x, y, w, h, _a = stats[i]
        if x > 0 and y > 0 and x + w < m.shape[1] and y + h < m.shape[0]:
            m[lab == i] = 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    m = cv2.GaussianBlur(m, (0, 0), 2.0)
    m = np.where(m > 127, 255, 0).astype(np.uint8)
    return cv2.GaussianBlur(m, (0, 0), 1.0)


def _manga_layers(img, alpha, cfg):
    g = cv2.createCLAHE(2.0, (8, 8)).apply(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    sm = cv2.bilateralFilter(g, 9, 50, 7).astype(np.float32) / 255
    gf = g.astype(np.float32) / 255
    dd = cv2.GaussianBlur(gf, (0, 0), 1.0) - 0.98 * cv2.GaussianBlur(gf, (0, 0), 1.6)
    line = np.where(dd >= -0.006, 1.0, 1 + np.tanh(90 * (dd + 0.006)))           # XDoG 墨线
    line = cv2.GaussianBlur(line.astype(np.float32), (0, 0), 0.5)
    yy, xx = np.mgrid[0:sm.shape[0], 0:sm.shape[1]].astype(np.float32)
    a = math.radians(45)
    u = (xx * math.cos(a) + yy * math.sin(a)) / 6
    v = (-xx * math.sin(a) + yy * math.cos(a)) / 6
    dist = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    dark = np.clip((0.62 - sm) / 0.34, 0, 1)
    tone = np.where(dist < np.sqrt(dark) * 0.62, 0.0, 1.0)                         # 网点：越暗点越大
    tone = np.where(sm < 0.22, 0.0, tone)
    tone = np.where(sm > 0.66, 1.0, tone)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    outer = cv2.GaussianBlur(cv2.dilate(alpha, k), (0, 0), 1.0).astype(np.float32) / 255
    am = alpha.astype(np.float32) / 255
    out = {}
    for kind, val in (("full", np.clip(tone * line, 0, 1)), ("line", np.clip(line, 0, 1))):
        val = cv2.GaussianBlur(val.astype(np.float32), (0, 0), 0.6)
        v2 = val * am + 0.08 * (1 - am)                                            # 外圈是墨色描边
        rgba = np.zeros((*am.shape, 4), np.uint8)
        rgba[..., :3] = np.clip(v2 * 255, 0, 255)[..., None]
        if kind == "full":
            rgba[..., 3] = np.clip(np.maximum(am, outer) * 255, 0, 255)
        else:
            ink_a = np.clip((1 - v2) * 1.6, 0, 1)
            rgba[..., 3] = np.clip(np.maximum(ink_a * am, outer * (1 - am)) * 255, 0, 255)
        fc = cfg.get("fade_corner")
        if fc:
            hh = rgba.shape[0]
            wd = int(fc.get("width", 160))
            rw = np.clip((np.arange(hh) - fc.get("from_y", 700)) / float(fc.get("ramp", 100)), 0, 1)[:, None]
            cw = np.linspace(0, 1, wd)[None, :] ** 0.7
            rgba[:, -wd:, 3] = (rgba[:, -wd:, 3].astype(np.float32) * (1 - rw * cw)).astype(np.uint8)
        im = Image.fromarray(rgba, "RGBA")
        if cfg.get("mirror"):
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        out[kind] = im
    return out["full"], out["line"]


_mem = {}


def manga_imgs(pid, force=False):
    """返回 (完整网点图, 仅墨线图)，900×1200 的 RGBA。结果缓存在人物文件夹的 cache/ 里。"""
    if pid in _mem and not force:
        return _mem[pid]
    cfg = load(pid)
    cache = os.path.join(cfg["dir"], "cache")
    fp, lp = os.path.join(cache, "mg_full.png"), os.path.join(cache, "mg_line.png")
    stamp = os.path.join(cache, "cfg.json")
    key = json.dumps({k: cfg.get(k) for k in ("photo", "crop", "mirror", "sure_fg", "sure_bg", "fade_corner")},
                     sort_keys=True)
    fresh = (not force and os.path.exists(fp) and os.path.exists(lp) and os.path.exists(stamp)
             and open(stamp, encoding="utf-8").read() == key)
    if not fresh:                                  # person.json 改过就自动重做
        img = work_image(cfg)
        full, line = _manga_layers(img, cutout(img, cfg), cfg)
        os.makedirs(cache, exist_ok=True)
        full.save(fp)
        line.save(lp)
        with open(stamp, "w", encoding="utf-8") as f:
            f.write(key)
    _mem[pid] = (Image.open(fp).convert("RGBA"), Image.open(lp).convert("RGBA"))
    return _mem[pid]


def debug_mask(pid, out_path):
    """抠图调试图：抠掉的部分压暗，叠 50px 网格和坐标，用来调 sure_fg / sure_bg"""
    cfg = load(pid)
    img = work_image(cfg)
    a = cutout(img, cfg)
    v = img.copy()
    v[a < 128] = (v[a < 128] * 0.3).astype(np.uint8)
    for x in range(0, WORK_W, 50):
        cv2.line(v, (x, 0), (x, WORK_H - 1), (0, 0, 255) if x % 100 == 0 else (0, 160, 255), 1)
    for y in range(0, WORK_H, 50):
        cv2.line(v, (0, y), (WORK_W - 1, y), (0, 0, 255) if y % 100 == 0 else (0, 160, 255), 1)
    for x in range(0, WORK_W, 100):
        cv2.putText(v, str(x), (x + 2, 20), 0, 0.6, (0, 0, 255), 2)
    for y in range(100, WORK_H, 100):
        cv2.putText(v, str(y), (2, y - 4), 0, 0.6, (0, 0, 255), 2)
    for kind, shapes, col in (("fg", cfg.get("sure_fg", []), (0, 200, 0)), ("bg", cfg.get("sure_bg", []), (200, 0, 200))):
        for k, s in shapes:
            if k == "ell":
                cv2.ellipse(v, (int(s[0]), int(s[1])), (int(s[2]), int(s[3])), 0, 0, 360, col, 2)
            else:
                cv2.rectangle(v, (int(s[0]), int(s[1])), (int(s[2]), int(s[3])), col, 2)
    ok, b = cv2.imencode(".png", v)
    b.tofile(out_path)
    return out_path


def credit_line(pids):
    parts = []
    for pid in pids:
        c = load(pid)
        cr = c.get("credit", {})
        parts.append(f"{c.get('name_en', pid)} —— {cr.get('author', '?')}（{cr.get('license', '?')}）")
    return "；".join(parts)
