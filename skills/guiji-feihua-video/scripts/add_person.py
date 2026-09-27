"""人物库管理（照片只用 Wikimedia Commons 上可改编、可商用的授权：CC BY / CC BY-SA / CC0 / 公有领域）

  python add_person.py search "Jensen Huang"                       列出 Commons 上的候选照片（授权、尺寸）
  python add_person.py add <库目录> <id> "File:xxx.jpg" --zh 黄仁勋 --en "Jensen Huang" --org NVIDIA [--facing left|right]
        下载照片（≈1100px）→ 写 person.json（默认抠图提示）→ 生成调试图 _mask.png 和漫画预览 _manga.png
  python add_person.py check <库目录> <id>                          改完 person.json 后重新生成调试图和预览

<库目录> 一般是 视频/people。调参方法见 references/people.md。
"""
import json, os, re, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "GuijiFeihuaVideo/1.0 (personal educational videos; contact via Wikimedia user page)"}
API = "https://commons.wikimedia.org/w/api.php"
OK_LICENSES = ("CC BY", "CC-BY", "CC0", "Public domain", "PD", "CC BY-SA", "CC-BY-SA")


def get(url, tries=5):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:                      # Commons 偶尔 429，慢一点重试
            if k == tries - 1:
                raise SystemExit(f"✗ 下载失败：{e}")
            time.sleep(4 * (k + 1))


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def search(q):
    url = API + "?" + urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": 30,
        "prop": "imageinfo", "iiprop": "size|extmetadata", "iiextmetadatafilter": "LicenseShortName|Artist",
        "format": "json"})
    data = json.loads(get(url))
    rows = []
    for p in (data.get("query") or {}).get("pages", {}).values():
        ii = p["imageinfo"][0]
        lic = ii["extmetadata"].get("LicenseShortName", {}).get("value", "?")
        ok = any(lic.startswith(x) for x in OK_LICENSES) and "NC" not in lic and "ND" not in lic
        rows.append((ok, p["title"], ii["width"], ii["height"], lic, strip_html(ii["extmetadata"].get("Artist", {}).get("value"))))
    rows.sort(key=lambda r: (not r[0], -r[2] * r[3]))
    for ok, title, w, h, lic, artist in rows:
        print(f"{'✓' if ok else '✗'} {title} | {w}x{h} | {lic} | {artist[:40]}")
    print("\n✓ = 授权可用。优先选：正脸或 3/4 侧脸、单人、背景简单、清晰的半身照。")


def add(lib, pid, file_title, zh, en, org="", facing="right"):
    d = os.path.join(lib, pid)
    os.makedirs(d, exist_ok=True)
    if not file_title.startswith("File:"):
        file_title = "File:" + file_title
    url = API + "?" + urllib.parse.urlencode({
        "action": "query", "titles": file_title, "prop": "imageinfo", "iiprop": "url|size|extmetadata",
        "iiurlwidth": 1100, "iiextmetadatafilter": "LicenseShortName|Artist|Credit", "format": "json"})
    page = next(iter(json.loads(get(url))["query"]["pages"].values()))
    if "imageinfo" not in page:
        raise SystemExit(f"✗ Commons 上找不到 {file_title}")
    ii = page["imageinfo"][0]
    lic = ii["extmetadata"].get("LicenseShortName", {}).get("value", "?")
    if not (any(lic.startswith(x) for x in OK_LICENSES) and "NC" not in lic and "ND" not in lic):
        raise SystemExit(f"✗ 授权 {lic} 不允许改编或商用，换一张")
    img = get(ii.get("thumburl") or ii["url"])
    open(os.path.join(d, "photo.jpg"), "wb").write(img)
    from PIL import Image
    im = Image.open(os.path.join(d, "photo.jpg"))
    w, h = im.size
    # 默认裁剪：顶部居中取 3:4
    cw = min(w, int(h * 0.75))
    ch = int(cw / 0.75)
    x0 = (w - cw) // 2
    cfg = {
        "name_zh": zh, "name_en": en, "org": org, "photo": "photo.jpg",
        "crop": [x0, 0, x0 + cw, min(h, ch)], "mirror": False, "facing": facing,
        "sure_fg": [["ell", [450, 480, 150, 210]], ["rect", [120, 1020, 780, 1200]]],
        "sure_bg": [["rect", [0, 0, 70, 700]], ["rect", [830, 0, 900, 700]], ["rect", [0, 0, 900, 20]]],
        "fade_corner": None,
        "credit": {"file": file_title[5:], "author": strip_html(ii["extmetadata"].get("Artist", {}).get("value")) or "?",
                   "license": lic, "url": ii.get("descriptionurl", "")},
    }
    json.dump(cfg, open(os.path.join(d, "person.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✓ 已下载 {w}x{h}，授权 {lic}，作者 {cfg['credit']['author']}")
    check(lib, pid)


def check(lib, pid):
    import people
    people._search = [lib]
    d = people.find(pid)
    m = people.debug_mask(pid, os.path.join(d, "_mask.png"))
    full, _ = people.manga_imgs(pid, force=True)
    bg = full.copy()
    from PIL import Image
    canvas = Image.new("RGBA", bg.size, (248, 247, 243, 255))
    canvas.alpha_composite(bg)
    canvas.convert("RGB").save(os.path.join(d, "_manga.png"))
    print(f"调试图：{m}\n  绿框=一定是人物，紫框=一定是背景，压暗部分=被抠掉的区域（坐标是 900×1200 工作图）")
    print(f"漫画预览：{os.path.join(d, '_manga.png')}")


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
    elif a[0] == "search":
        search(" ".join(a[1:]))
    elif a[0] == "add":
        lib, pid, ft = a[1], a[2], a[3]
        opts = dict(zip(a[4::2], a[5::2]))
        add(lib, pid, ft, opts.get("--zh", pid), opts.get("--en", pid), opts.get("--org", ""),
            opts.get("--facing", "right"))
    elif a[0] == "check":
        check(a[1], a[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
