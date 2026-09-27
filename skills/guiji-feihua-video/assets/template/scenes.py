"""分镜：每个场景一个函数 f(s)，BUILDERS 把场景 id 映射到函数。
可用的版式和元素见 skill 的 references/patterns.md、references/engine-api.md；
完整示例见 references/example-episode/scenes.py。"""
from patterns import *  # noqa: F401,F403


def sc_open(s):
    title_page(s, "标题", first=True)          # 第一个场景：画出水印
    thermo(s, 0.5, draw_at=s.t(1, 0.3))          # 可选：关系温度计（没有"关系"的题材就删掉）
    end_erase(s)


def sc_ending(s):
    watermark(s)
    thermo(s, 0.5)
    question(s, "你怎么看？", sent=len(s.ctx.st) - 1)
    end_card(s, sources="（同 episode.json 的 sources）", pids=[])


BUILDERS = {"open": sc_open, "ending": sc_ending}
