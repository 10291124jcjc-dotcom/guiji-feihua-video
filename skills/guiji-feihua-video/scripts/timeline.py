"""时间轴：句子排布、字幕切分、混音（人声 + 自动闪避的合成铺底音乐）"""
import os, subprocess, wave
import numpy as np

FPS = 30
LEAD = 0.6          # 每个场景开头留白
SENT_GAP = 0.45     # 句间停顿
TAIL = 0.9          # 每个场景结尾留白（擦板在这里发生）


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def _weight(s):
    return sum(0.55 if ord(ch) < 128 else 1.0 for ch in s)


def chunks(text, st, dur, limit=30):
    """把长句按标点切成单行字幕，按字数比例分配时间 → [(t0, t1, 文本)]"""
    text = text.replace("|", "")
    pieces, cur = [], ""
    for ch in text:
        cur += ch
        if ch in "，。；：！？、":
            pieces.append(cur)
            cur = ""
    if cur:
        pieces.append(cur)
    groups, g = [], ""
    for p in pieces:
        if g and _weight(g + p) > limit:
            groups.append(g)
            g = p
        else:
            g += p
    if g:
        groups.append(g)
    total = sum(_weight(x) for x in groups) or 1
    out, t = [], st
    for x in groups:
        d = dur * _weight(x) / total
        out.append((t, t + d, x.rstrip("，。；、")))
        t += d
    return out


class Ctx:
    """一个场景的句子时间轴：st[i] 第 i 句开始时间，du[i] 时长；sub() 当前字幕"""

    def __init__(self, sents):
        self.st, self.du = [], []
        t = LEAD
        for s in sents:
            self.st.append(t)
            self.du.append(s["dur"])
            t += s["dur"] + SENT_GAP
        self.end = t - SENT_GAP
        self.texts = [s["text"] for s in sents]
        self.subs = []
        for st, du, tx in zip(self.st, self.du, self.texts):
            cs = chunks(tx, st, du)
            cs[-1] = (cs[-1][0], cs[-1][1] + SENT_GAP * 0.7, cs[-1][2])
            self.subs += cs
        self.t = 0

    def sub(self):
        for a, b, tx in self.subs:
            if a <= self.t < b:
                return tx
        return None


def build_audio(plan, build_dir, srt_path):
    """plan = [(scene_id, sents, nframes)] → build_dir/mix.wav（人声 + 铺底音乐），并写 SRT 字幕"""
    sr = 48000
    total = sum(n for _, _, n in plan) / FPS
    voice = np.zeros(int(total * sr) + sr, np.float32)
    srt, t0, k = [], 0.0, 1
    for sid, sents, n in plan:
        c = Ctx(sents)
        for i, s in enumerate(sents):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", s["file"], "-f", "s16le", "-ac", "1", "-ar", str(sr),
                                  "-"], capture_output=True).stdout
            a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
            st = int((t0 + c.st[i]) * sr)
            voice[st:st + len(a)] += a[:max(0, len(voice) - st)]
            for a0, a1, tx in chunks(s["text"], c.st[i], s["dur"]):
                srt.append((k, t0 + a0, t0 + a1, tx))
                k += 1
        t0 += n / FPS
    # 铺底音乐：柔和和弦（Am - F - C - G），人声出现时自动压低
    tt = np.arange(len(voice)) / sr
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [130.81, 196.0, 261.63], [196.0, 246.94, 293.66]]
    music = np.zeros_like(voice)
    seg = 4.0
    for ci in range(int(total / seg) + 2):
        s0, s1 = int(ci * seg * sr), int((ci + 1) * seg * sr + sr)
        if s0 >= len(music):
            break
        s1 = min(s1, len(music))
        lt = tt[s0:s1] - ci * seg
        env = np.clip(lt / 1.2, 0, 1) * np.clip((seg + 1 - lt) / 1.2, 0, 1)
        for f in chords[ci % 4]:
            for det in (0.997, 1.003):
                music[s0:s1] += np.sin(2 * np.pi * f * det * lt) * env * 0.05
            music[s0:s1] += np.sin(2 * np.pi * f / 2 * lt) * env * 0.03
    frame = sr // 10
    lvl = np.abs(voice[:len(voice) // frame * frame]).reshape(-1, frame).max(axis=1)
    duck = np.convolve(np.where(lvl > 0.02, 0.45, 1.0), np.ones(8) / 8, mode="same")
    duck = np.repeat(duck, frame)
    duck = np.pad(duck, (0, len(music) - len(duck)), constant_values=1.0)
    fade = np.clip((total - tt) / 3.0, 0, 1) * np.clip(tt / 2.0, 0, 1)
    mix = voice + music * duck * fade * 0.55
    mix = np.clip(mix / max(1.0, np.abs(mix).max() / 0.95), -1, 1)
    path = os.path.join(build_dir, "mix.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())

    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(srt_path, "w", encoding="utf-8") as f:
        for k, a, b, s in srt:
            f.write(f"{k}\n{ts(a)} --> {ts(b)}\n{s}\n\n")
    return path
