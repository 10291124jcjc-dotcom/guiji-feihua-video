"""配音。<期> = 期目录。旁白来自 <期>/narration.py 的 SCENES。

  python voice.py <期> tts                 用克隆音色合成全部旁白（只合成改过的句子）→ <期>/build/timing.json
  python voice.py <期> test "一句话"        试听 → <期>/build/voice_test.wav
  python voice.py <期> placeholder         免费占位配音（edge-tts 云希），只用于出样片，正式发布前换成克隆音色
  python voice.py <期> script              生成《录音稿.md》（想自己录的时候用）
  python voice.py <期> import              导入 <期>/录音/ 下的真人录音（01.m4a 一场一个文件，句间停顿 1 秒）
  python voice.py <期> create 样本.m4a      （仅百炼）上传样本创建音色；火山引擎在控制台网页复刻即可

密钥放在 .env（从期目录往上逐级查找，一般放在 视频/.env）：
  火山引擎（新版控制台）：VOLC_API_KEY=… ，VOLC_SPEAKER_ID=S_…
  （旧版控制台：VOLC_APP_ID + VOLC_ACCESS_TOKEN）
  阿里云百炼：DASHSCOPE_API_KEY=…    两家都填时用 TTS_PROVIDER=volc|dashscope 指定
密钥属于用户，只检查"填没填/格式对不对"，不要打印或读出内容。
"""
import asyncio, base64, glob, hashlib, importlib, json, os, subprocess, sys, time, uuid, wave
import urllib.request, urllib.error
import numpy as np

SR = 48000
PAD = 0.08
MIN_GAP = 0.25
EXTS = ("wav", "m4a", "mp3", "aac", "flac", "ogg", "amr")


# =============================================================== 期目录 & 配置
class Ep:
    def __init__(self, d):
        self.dir = os.path.abspath(d)
        os.chdir(self.dir)
        sys.path.insert(0, self.dir)
        self.scenes = importlib.import_module("narration").SCENES
        os.makedirs("build", exist_ok=True)


def env():
    """从当前目录往上找 .env，再看 ~/.guiji/.env；环境变量优先"""
    e, d, seen = {}, os.getcwd(), []
    while True:
        seen.append(os.path.join(d, ".env"))
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    seen.append(os.path.join(os.path.expanduser("~"), ".guiji", ".env"))
    for p in reversed(seen):                       # 近的覆盖远的
        if os.path.exists(p):
            for line in open(p, encoding="utf-8-sig"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    if v and not v.startswith("在这里"):
                        e[k.strip()] = v
    for k in ("TTS_PROVIDER", "VOLC_API_KEY", "VOLC_APP_ID", "VOLC_ACCESS_TOKEN", "VOLC_SPEAKER_ID",
              "VOLC_RESOURCE_ID", "DASHSCOPE_API_KEY", "DASHSCOPE_VOICE"):
        if os.environ.get(k):
            e[k] = os.environ[k]
    return e


def provider():
    e = env()
    p = e.get("TTS_PROVIDER", "").lower() or (
        "volc" if (e.get("VOLC_API_KEY") or e.get("VOLC_APP_ID")) else "dashscope" if e.get("DASHSCOPE_API_KEY") else "")
    if p == "volc":
        miss = []
        if not e.get("VOLC_API_KEY") and not (e.get("VOLC_APP_ID") and e.get("VOLC_ACCESS_TOKEN")):
            miss.append("VOLC_API_KEY")
        if not e.get("VOLC_SPEAKER_ID"):
            miss.append("VOLC_SPEAKER_ID")
        if miss:
            raise SystemExit("✗ .env 里还缺：" + "、".join(miss))
        return p, e, e["VOLC_SPEAKER_ID"]
    if p == "dashscope":
        if not e.get("DASHSCOPE_API_KEY"):
            raise SystemExit("✗ .env 里还缺 DASHSCOPE_API_KEY")
        vid = e.get("DASHSCOPE_VOICE")
        if not vid:
            raise SystemExit("✗ 还没有百炼音色：先 python voice.py <期> create 样本.m4a，再把输出的音色 ID 写进 .env 的 DASHSCOPE_VOICE")
        return p, e, vid
    raise SystemExit("✗ 还没配置克隆音色的密钥（.env）。只想先出样片可以用 placeholder 占位配音。")


def http(url, body, headers, raw=False, tries=6):
    data = json.dumps(body).encode()
    for k in range(tries):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                c = r.read()
                return c if raw else json.loads(c)
        except urllib.error.HTTPError as ex:
            msg = ex.read().decode("utf-8", "replace")
            if ex.code in (429, 500, 502, 503, 504) and k < tries - 1:
                time.sleep(2 * (k + 1))
                continue
            raise SystemExit(f"✗ 接口报错 HTTP {ex.code}：{msg[:500]}")
        except urllib.error.URLError as ex:
            if k < tries - 1:
                time.sleep(2 * (k + 1))
                continue
            raise SystemExit(f"✗ 网络错误：{ex}")


# =============================================================== 音频工具
def decode(path, af=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path] + (["-af", af] if af else []) + ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()


def load_clean(path):
    """解码 + 高通 + 降噪 + 响度统一（-16 LUFS）"""
    return decode(path, "highpass=f=80,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11")


def frames_db(a, hop=0.01):
    n = int(SR * hop)
    m = len(a) // n
    rms = np.sqrt(np.mean(a[:m * n].reshape(m, n) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms), hop


def silences(a):
    db, hop = frames_db(a)
    thr = max(np.percentile(db, 10) + 10, np.percentile(db, 90) - 32)
    runs, start = [], None
    for k, q in enumerate(np.append(db < thr, False)):
        if q and start is None:
            start = k
        elif not q and start is not None:
            runs.append((start * hop, k * hop))
            start = None
    return runs, thr


def trim(a, thr_db=None):
    if thr_db is None:
        thr_db = silences(a)[1]
    db, hop = frames_db(a)
    loud = np.where(db >= thr_db)[0]
    if len(loud) == 0:
        return a
    s = max(0, int((loud[0] * hop - PAD) * SR))
    e = min(len(a), int(((loud[-1] + 1) * hop + PAD) * SR))
    out = a[s:e].copy()
    f = int(0.01 * SR)
    out[:f] *= np.linspace(0, 1, f)
    out[-f:] *= np.linspace(1, 0, f)
    return out


def save_wav(a, path, sr=SR):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


def wav_dur(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def write_timing(timing):
    with open(os.path.join("build", "timing.json"), "w", encoding="utf-8") as f:
        json.dump(timing, f, ensure_ascii=False, indent=1)
    total = sum(s["dur"] for sc in timing for s in sc["sents"])
    print(f"✓ 旁白共 {sum(len(sc['sents']) for sc in timing)} 句，总长 {total / 60:.1f} 分钟。下一步：python build.py <期> render")


# =============================================================== 克隆音色合成
VOLC = "https://openspeech.bytedance.com/api/v3/tts"
DASH = "https://dashscope.aliyuncs.com/api/v1/services"
DASH_MODEL = "qwen3-tts-vc-2026-01-22"


def volc_auth(e, app_header):
    if e.get("VOLC_API_KEY"):
        return {"X-Api-Key": e["VOLC_API_KEY"]}
    return {app_header: e["VOLC_APP_ID"], "X-Api-Access-Key": e["VOLC_ACCESS_TOKEN"]}


def synth_bytes(text):
    p, e, vid = provider()
    if p == "volc":
        headers = {**volc_auth(e, "X-Api-App-Id"), "X-Api-Resource-Id": e.get("VOLC_RESOURCE_ID", "seed-icl-2.0"),
                   "X-Api-Request-Id": str(uuid.uuid4())}
        body = {"user": {"uid": "guiji"}, "req_params": {"text": text, "speaker": vid,
                                                          "audio_params": {"format": "mp3", "sample_rate": 24000}}}
        content = http(f"{VOLC}/unidirectional", body, headers, raw=True)
        chunks = []
        for line in content.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line.startswith("{"):
                continue
            d = json.loads(line)
            if d.get("code", 0) not in (0, 20000000):
                raise SystemExit(f"✗ 合成出错 code={d.get('code')}：{d.get('message')}")
            if d.get("data"):
                chunks.append(base64.b64decode(d["data"]))
        if not chunks:
            raise SystemExit(f"✗ 合成没有返回音频：{content[:300]!r}")
        return b"".join(chunks), p, vid
    r = http(f"{DASH}/aigc/multimodal-generation/generation", {"model": DASH_MODEL, "input": {"text": text, "voice": vid}},
             {"Authorization": f"Bearer {e['DASHSCOPE_API_KEY']}"})
    audio = (r.get("output") or {}).get("audio") or {}
    if audio.get("url"):
        with urllib.request.urlopen(audio["url"], timeout=120) as f:
            return f.read(), p, vid
    if audio.get("data"):
        return base64.b64decode(audio["data"]), p, vid
    raise SystemExit(f"✗ 合成返回里没有音频：{json.dumps(r, ensure_ascii=False)[:300]}")


def synth_to_wav(text, path):
    data, _, _ = synth_bytes(text)
    tmp = path + ".src"
    open(tmp, "wb").write(data)
    a = trim(decode(tmp))
    os.remove(tmp)
    save_wav(a, path)
    return len(a) / SR


def cmd_tts(ep):
    p, _, vid = provider()
    out = os.path.join("build", "voice")
    os.makedirs(out, exist_ok=True)
    timing, n_new = [], 0
    for i, (sid, sents) in enumerate(ep.scenes, 1):
        items = []
        for j, text in enumerate(sents, 1):
            text = text.replace("|", "")
            h = hashlib.md5(f"{p}|{vid}|{text}".encode()).hexdigest()[:10]
            path = os.path.join(out, f"{i:02d}_{j:02d}_{h}.wav")
            if not os.path.exists(path):
                synth_to_wav(text, path)
                n_new += 1
                print(f"  合成 {i:02d}-{j:02d}  {text[:20]}…", flush=True)
            items.append({"text": text, "file": path, "dur": wav_dur(path)})
        timing.append({"id": sid, "sents": items})
    print(f"新合成 {n_new} 句（其余沿用缓存）")
    write_timing(timing)


def cmd_create(sample):
    """百炼：上传 10~30 秒样本创建音色"""
    e = env()
    if not e.get("DASHSCOPE_API_KEY"):
        raise SystemExit("✗ create 只用于阿里云百炼；火山引擎请在控制台「声音复刻」网页里复刻，把 S_ 开头的音色 ID 填进 .env")
    a = trim(load_clean(sample))
    a = a[:30 * SR]
    wav = os.path.join("build", "clone_sample.wav")
    save_wav(a[::2], wav, SR // 2)
    b64 = base64.b64encode(open(wav, "rb").read()).decode()
    r = http(f"{DASH}/audio/tts/customization",
             {"model": "qwen-voice-enrollment", "input": {"action": "create", "target_model": DASH_MODEL,
                                                          "preferred_name": "guiji",
                                                          "audio": {"data": f"data:audio/wav;base64,{b64}"}}},
             {"Authorization": f"Bearer {e['DASHSCOPE_API_KEY']}"})
    vid = (r.get("output") or {}).get("voice")
    if not vid:
        raise SystemExit(f"✗ 创建失败：{json.dumps(r, ensure_ascii=False)[:300]}")
    print(f"✓ 音色创建成功。请在 .env 里加一行：DASHSCOPE_VOICE={vid}")


# =============================================================== 占位配音（edge-tts）
def cmd_placeholder(ep):
    try:
        import edge_tts
    except ImportError:
        raise SystemExit("✗ 需要先安装：python -m pip install edge-tts")
    out = os.path.join("build", "placeholder")
    os.makedirs(out, exist_ok=True)

    async def one(text, path):
        for k in range(15):
            try:
                await edge_tts.Communicate(text, "zh-CN-YunxiNeural", rate="+8%").save(path)
                return
            except Exception:
                await asyncio.sleep(3 + k)
        raise SystemExit("✗ edge-tts 连续失败，稍后重试")

    async def run():
        timing = []
        for i, (sid, sents) in enumerate(ep.scenes, 1):
            items = []
            for j, text in enumerate(sents, 1):
                text = text.replace("|", "")
                h = hashlib.md5(text.encode()).hexdigest()[:10]
                mp3 = os.path.join(out, f"{i:02d}_{j:02d}_{h}.mp3")
                wav = mp3[:-4] + ".wav"
                if not os.path.exists(wav):
                    await one(text, mp3)
                    save_wav(trim(decode(mp3)), wav)
                items.append({"text": text, "file": wav, "dur": wav_dur(wav)})
            timing.append({"id": sid, "sents": items})
        return timing
    write_timing(asyncio.run(run()))
    print("⚠ 这是占位配音，只用于看样片；正式发布前运行 tts 换成克隆音色")


# =============================================================== 真人录音
def cmd_script(ep):
    lines = ["# 录音稿", "", "- 每个场景录成一个文件：`01.m4a`、`02.m4a`…，放进期目录的 `录音` 文件夹",
             "- 句与句之间停顿约 1 秒（程序靠停顿自动切句）",
             "- 念错了：整场重录，或只重录那一句，命名为 `场景-句号`（如 `03-02.m4a`）", ""]
    for i, (sid, sents) in enumerate(ep.scenes, 1):
        lines += [f"## 场景 {i:02d}（文件名 `{i:02d}`）", ""] + [f"{j}. {s.replace('|', '')}" for j, s in enumerate(sents, 1)] + [""]
    open("录音稿.md", "w", encoding="utf-8").write("\n".join(lines))
    os.makedirs("录音", exist_ok=True)
    print("✓ 已生成 录音稿.md，并创建了 录音/ 文件夹")


def _find(stem):
    for ext in EXTS:
        hit = glob.glob(os.path.join("录音", f"{stem}.{ext}"))
        if hit:
            return hit[0]
    return None


def _split(a, n, name):
    runs, thr = silences(a)
    dur = len(a) / SR
    inner = [(s, e) for s, e in runs if s > 0.05 and e < dur - 0.05 and e - s >= MIN_GAP]
    if len(inner) < n - 1:
        raise SystemExit(f"✗ {name}：只找到 {len(inner)} 个明显停顿，但这一场有 {n} 句，请在句间多停顿一下")
    cuts = sorted(sorted(inner, key=lambda r: r[1] - r[0], reverse=True)[:n - 1])
    b = [0.0] + [(s + e) / 2 for s, e in cuts] + [dur]
    return [trim(a[int(b[k] * SR):int(b[k + 1] * SR)], thr) for k in range(n)]


def cmd_import(ep):
    out = os.path.join("build", "recorded")
    os.makedirs(out, exist_ok=True)
    timing, missing = [], []
    for i, (sid, sents) in enumerate(ep.scenes, 1):
        whole = _find(f"{i:02d}")
        parts = _split(load_clean(whole), len(sents), f"{i:02d}") if whole else [None] * len(sents)
        items = []
        for j in range(1, len(sents) + 1):
            single = _find(f"{i:02d}-{j:02d}") or _find(f"{i:02d}-{j}")
            if single:
                parts[j - 1] = trim(load_clean(single))
            if parts[j - 1] is None:
                missing.append(f"{i:02d}-{j:02d}")
                continue
            path = os.path.join(out, f"{i:02d}_{j:02d}.wav")
            save_wav(parts[j - 1], path)
            items.append({"text": sents[j - 1].replace("|", ""), "file": path, "dur": len(parts[j - 1]) / SR})
        timing.append({"id": sid, "sents": items})
    if missing:
        raise SystemExit("✗ 还缺这些录音（场景-句号）：" + "、".join(missing))
    for i, sc in enumerate(timing, 1):
        rates = [len(s["text"]) / s["dur"] for s in sc["sents"]]
        med = float(np.median(rates))
        for j, r in enumerate(rates, 1):
            if r > med * 1.8 or r < med / 1.8:
                print(f"  ⚠ {i:02d}-{j:02d} 语速异常（{r:.1f} 字/秒），可能切错了，请试听 build/recorded/{i:02d}_{j:02d}.wav")
    write_timing(timing)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, rest = sys.argv[2], sys.argv[3:]
    if cmd == "create" and rest:
        rest[0] = os.path.abspath(rest[0])       # 先按用户当前目录解析，Ep() 会切换目录
    ep = Ep(sys.argv[1])
    if cmd == "tts":
        cmd_tts(ep)
    elif cmd == "test":
        text = rest[0] if rest else "大家好，这是用我自己的声音克隆出来的配音，听听像不像。"
        d = synth_to_wav(text, os.path.join("build", "voice_test.wav"))
        print(f"✓ 已生成 {os.path.join(ep.dir, 'build', 'voice_test.wav')}（{d:.1f} 秒）")
    elif cmd == "placeholder":
        cmd_placeholder(ep)
    elif cmd == "script":
        cmd_script(ep)
    elif cmd == "import":
        cmd_import(ep)
    elif cmd == "create" and rest:
        cmd_create(rest[0])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
