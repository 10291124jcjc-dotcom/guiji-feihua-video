"""「硅基废话」出片工具。<期> = 期目录（含 episode.json / narration.py / scenes.py）

  python build.py <期> render [场景id ...]      全部（或只重渲这几个场景）→ 拼接 → 混音 → 成片 + SRT
  python build.py <期> preview <场景id> 3 8.5   导出该场景第 3、8.5 秒的静帧 → <期>/build/preview_*.png
  python build.py <期> audit                    检查每个场景：有没有段落被压缩 / 元素画到擦板后 / 超出场景
  python build.py <期> chapters                 打印每个场景在成片里的起始时间（油管章节用）
  python build.py <期> sheet 42.5 3 [4]         从成片截取 42.5 秒起 3 秒、每秒 4 帧 → 拼成一张检查图
  python build.py <期> check                    成片信息：时长、分辨率、音量
  python build.py <期> cut 版本名 场景id ...    按场景剪短版（例：推特版），接缝处音频淡入淡出
"""
import importlib, json, math, os, subprocess, sys
from multiprocessing import Pool
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline                                   # noqa: E402
import wb                                         # noqa: E402
import people                                     # noqa: E402

DEFAULT_END_CARD = 6.5


# ------------------------------------------------------------ 期目录
class Episode:
    def __init__(self, ep_dir):
        self.dir = os.path.abspath(ep_dir)
        with open(os.path.join(self.dir, "episode.json"), encoding="utf-8") as f:
            self.meta = json.load(f)
        self.build = os.path.join(self.dir, "build")
        os.makedirs(self.build, exist_ok=True)
        name = self.meta.get("output_name") or f"{self.meta.get('brand', '硅基废话')}｜{self.meta['title']}"
        self.final = os.path.join(self.dir, name + ".mp4")
        self.srt = os.path.join(self.dir, name + ".srt")
        people.set_episode(self.dir)
        if self.dir not in sys.path:
            sys.path.insert(0, self.dir)
        os.chdir(self.dir)                         # timing.json 里的音频路径是相对期目录的

    def scenes(self):
        return importlib.import_module("scenes").BUILDERS

    def plan(self):
        p = os.path.join(self.build, "timing.json")
        if not os.path.exists(p):
            raise SystemExit("✗ 还没有配音：先运行 python voice.py <期> tts")
        with open(p, encoding="utf-8") as f:
            timing = json.load(f)
        out = []
        for i, sc in enumerate(timing):
            c = timeline.Ctx(sc["sents"])
            dur = c.end + timeline.TAIL
            if i == len(timing) - 1:
                dur += self.meta.get("end_card_seconds", DEFAULT_END_CARD)
            out.append((sc["id"], sc["sents"], int(math.ceil(dur * wb.FPS))))
        return out


# ------------------------------------------------------------ 字幕（漫画对白框）
_sub_cache = {}


def sub_img(text):
    if text in _sub_cache:
        return _sub_cache[text]
    f = wb.font(44)
    w, h = int(f.getlength(text) + 80), 86
    box = wb.rect(20, 14, 20 + w, 14 + h, wb.INK, 5, seed=len(text))
    bx0, by0 = box.bbox()[:2]
    im = Image.new("RGBA", (w + 40, h + 28), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([20, 14, 20 + w, 14 + h], fill=(255, 255, 255, 240))
    im.alpha_composite(box.final(), (max(0, bx0), max(0, by0)))
    ImageDraw.Draw(im).text((20 + w / 2, 14 + h / 2), text, font=f, fill=wb.INK, anchor="mm",
                            stroke_width=1, stroke_fill=wb.INK)
    _sub_cache[text] = im
    return im


def make_overlays(ctx):
    def ov(cv, t):
        ctx.t = t
        s = ctx.sub()
        if s:
            im = sub_img(s)
            wb._paste(cv, im, 960 - im.width / 2, 1058 - im.height)
    return ov


def build_scene(ep, sid, sents, nframes):
    ctx = timeline.Ctx(sents)
    s = wb.Scene(ctx, nframes)
    ep.scenes()[sid](s)
    return s, ctx


# ------------------------------------------------------------ 渲染
def render_scene(args):
    ep_dir, idx, sid, sents, nframes, last, only = args
    ep = Episode(ep_dir)
    s, ctx = build_scene(ep, sid, sents, nframes)
    r = wb.Renderer(s, make_overlays(ctx))
    black = Image.new("RGBA", (wb.W, wb.H), (0, 0, 0, 255))
    if only is not None:
        want = sorted(int(x * wb.FPS) for x in only)
        for fr in range(max(want) + 1):            # 逐帧推进，保证"已画完"的状态正确
            cv = r.frame(fr / wb.FPS)
            if fr in want:
                p = os.path.join(ep.build, f"preview_{sid}_{fr / wb.FPS:.1f}.png")
                cv.convert("RGB").save(p)
                print(p)
        return
    out = os.path.join(ep.build, f"seg_{idx:02d}.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{wb.W}x{wb.H}", "-r", str(wb.FPS), "-i", "-", "-c:v", "libx264",
                             "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    T = nframes / wb.FPS
    for fr in range(nframes):
        t = fr / wb.FPS
        cv = r.frame(t)
        if idx == 0 and t < 0.3:
            cv = Image.blend(black, cv, t / 0.3)
        if last and T - t < 0.6:
            cv = Image.blend(black, cv, max(0.0, (T - t) / 0.6))
        proc.stdin.write(cv.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    if s.squeezed:
        print(f"  ! {sid} 有段落画不完被自动加速：{s.squeezed}（擦板时间, 压缩系数, 原超出秒数）", flush=True)
    print("done", sid, round(T, 1), "s", flush=True)


def cmd_render(ep, only_ids):
    p = ep.plan()
    known = ep.scenes()
    missing = [sid for sid, _, _ in p if sid not in known]
    if missing:
        raise SystemExit(f"✗ scenes.py 的 BUILDERS 里缺这些场景：{missing}")
    jobs = [(ep.dir, i, sid, sents, n, i == len(p) - 1, None) for i, (sid, sents, n) in enumerate(p)
            if not only_ids or sid in only_ids]
    jobs.sort(key=lambda j: -j[4])
    with Pool(min(len(jobs), max(1, (os.cpu_count() or 4) - 1))) as pool:
        pool.map(render_scene, jobs, chunksize=1)
    lst = os.path.join(ep.build, "segs.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for i in range(len(p)):
            f.write(f"file 'seg_{i:02d}.mp4'\n")
    audio = timeline.build_audio(p, ep.build, ep.srt)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", audio,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", ep.final],
                   check=True)
    print("OK", ep.final)


def cmd_audit(ep):
    ok = True
    p = ep.plan()
    for i, (sid, sents, n) in enumerate(p):
        s, _ = build_scene(ep, sid, sents, n)
        over = [type(e).__name__ for e in s.els if e.end > s.T + 0.01]
        if i == len(p) - 1:                        # 片尾卡：最后一笔至少提前 2 秒画完，署名才看得清
            last = max(e.end for e in s.els)
            if last > s.T - 2.0:
                over.append(f"片尾卡最后一笔在结束前 {s.T - last:.1f} 秒才画完（需 ≥2 秒）")
        late = []
        for t0, _t1, tg in s.erases:
            late += [type(e).__name__ for e in s.els if id(e) in tg and e.start >= t0]
        flag = "  " if not (s.squeezed or over or late) else "! "
        ok &= flag == "  "
        print(f"{flag}{sid:14s} {s.T:6.1f}s  压缩={s.squeezed or '无'}  超出场景={over or '无'}  擦板后才画={late or '无'}")
    print("✓ 全部正常" if ok else "有 ! 的场景：画面比旁白慢，建议把那一段的元素改成并行（chain=False + 明确的 at）")


def offsets(ep):
    t, out = 0.0, []
    for sid, _, n in ep.plan():
        out.append((sid, t, n / wb.FPS))
        t += n / wb.FPS
    return out, t


def cmd_chapters(ep):
    names = ep.meta.get("chapters", {})
    offs, total = offsets(ep)
    for sid, t, _ in offs:
        print(f"{int(t // 60)}:{int(t % 60):02d} {names.get(sid, sid)}")
    print(f"（总长 {int(total // 60)}:{int(total % 60):02d}）")


def cmd_sheet(ep, start, dur, fps=4):
    n = int(dur * fps)
    cols = 4
    rows = max(1, math.ceil(n / cols))
    out = os.path.join(ep.build, f"sheet_{start:.1f}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-i", ep.final, "-t", str(dur), "-vf",
                    f"fps={fps},scale=480:-1,tile={cols}x{rows}", "-frames:v", "1", out], check=True)
    print(out)


def cmd_check(ep):
    kw = dict(capture_output=True, text=True, encoding="utf-8", errors="replace")   # Windows 下默认 GBK 会解码失败
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height",
                        "-of", "compact", ep.final], **kw)
    print(r.stdout.strip())
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", ep.final, "-af", "volumedetect", "-vn", "-f", "null", "-"], **kw)
    for l in r.stderr.splitlines():
        if "mean_volume" in l or "max_volume" in l:
            print(l.split("]")[-1].strip())


def cmd_cut(ep, name, ids):
    offs, _ = offsets(ep)
    segs = [(t, t + d) for sid, t, d in offs if sid in ids]
    if not segs:
        raise SystemExit("✗ 没找到这些场景")
    f, cat = "", ""
    for i, (a, b) in enumerate(segs):
        fo = round(b - a - 0.15, 3)
        f += (f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{i}];"
              f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.1,afade=t=out:st={fo}:d=0.15[a{i}];")
        cat += f"[v{i}][a{i}]"
    f += f"{cat}concat=n={len(segs)}:v=1:a=1[v][a]"
    out = ep.final.replace(".mp4", f"-{name}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ep.final, "-filter_complex", f, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "192k", "-movflags", "+faststart", out], check=True)
    total = sum(b - a for a, b in segs)
    print(f"OK {out}（{int(total // 60)}:{int(total % 60):02d}）")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    ep = Episode(sys.argv[1])
    cmd, rest = sys.argv[2], sys.argv[3:]
    if cmd == "render":
        cmd_render(ep, set(rest))
    elif cmd == "preview":
        p = ep.plan()
        ids = [x[0] for x in p]
        i = ids.index(rest[0])
        render_scene((ep.dir, i, *p[i], i == len(p) - 1, [float(x) for x in rest[1:]]))
    elif cmd == "audit":
        cmd_audit(ep)
    elif cmd == "chapters":
        cmd_chapters(ep)
    elif cmd == "sheet":
        cmd_sheet(ep, float(rest[0]), float(rest[1]), int(rest[2]) if len(rest) > 2 else 4)
    elif cmd == "check":
        cmd_check(ep)
    elif cmd == "cut":
        cmd_cut(ep, rest[0], set(rest[1:]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
