"""新建一期：python new_episode.py <视频根目录> "标题"
  → <视频根目录>/episodes/<今天日期> <标题>/  （episode.json、narration.py、scenes.py 模板）
  同时确保 <视频根目录>/people/ 存在（新人物放这里，跨期复用）。"""
import datetime, json, os, shutil, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    root, title = os.path.abspath(sys.argv[1]), sys.argv[2]
    safe = "".join(c for c in title if c not in '\\/:*?"<>|').strip()
    d = os.path.join(root, "episodes", f"{datetime.date.today():%Y-%m-%d} {safe}")
    if os.path.exists(d):
        raise SystemExit(f"✗ 已存在：{d}")
    os.makedirs(os.path.join(root, "people"), exist_ok=True)
    shutil.copytree(os.path.join(SKILL, "assets", "template"), d)
    p = os.path.join(d, "episode.json")
    meta = json.load(open(p, encoding="utf-8"))
    meta["title"] = title
    meta["output_name"] = f"硅基废话｜{safe}"
    meta["cover"]["title"] = title
    json.dump(meta, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(d)


if __name__ == "__main__":
    main()
