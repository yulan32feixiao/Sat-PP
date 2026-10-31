#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析复盘截图 → 结构化题目（draft.json）。

布局：左栏原文(psm6)，右栏题干+四选项+汇总面板。
右栏按 y 间距 >95px 聚类成块：块序列 = [题干, 选项A, B, C, D, 汇总面板]。
正确答案 = 含浅绿底色带的选项块（像素检测），辅以面板"正确答案"字母。
选项文本清理：剥离选择率/样本数/徽章字符。
"""
import glob
import io
import json
import os
import re
import subprocess

from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mybank_ocr")

NOISE = re.compile(
    r"(\d+(?:\.\d+)?%)|(\d+/\d+\s*人?)|((?:你的?|正确)答案)|(选择率)|(正确率样本)|(正确样本)|"
    r"(本题暂无答案解析)|(常见作答比例)|(^[\s()（）.。、:：|]*$)|(^[©®@eA-Da-d]{1,3}$)")


def ocr_words(img, lang="chi_sim+eng", psm="6"):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    r = subprocess.run(["tesseract", "stdin", "stdout", "-l", lang,
                        "--psm", psm, "tsv"],
                       input=buf.getvalue(), capture_output=True)
    words = []
    for line in r.stdout.decode("utf-8", "replace").splitlines()[1:]:
        p = line.split("\t")
        if len(p) == 12 and p[11].strip():
            words.append((int(p[7]), int(p[6]), p[11]))
    return words


def lines_from(words):
    lines = {}
    for y, x, t in words:
        lines.setdefault(round(y / 20), []).append((y, x, t))
    out = []
    for k in sorted(lines):
        ws = sorted(lines[k], key=lambda a: a[1])
        txt = " ".join(t for _, _, t in ws)
        # chi_sim 把汉字逐字输出，词间空格破坏中文匹配 —— 折叠 CJK 相邻空格
        txt = re.sub(r"([\u4e00-\u9fff（）：、。%]):?\s+(?=[\u4e00-\u9fff（）：、。%])",
                     r"\1", txt)
        txt = re.sub(r"(?<=[A-Za-z0-9,.]) (?=[A-Za-z0-9,.])", " ", txt)
        out.append((ws[0][0], txt))
    return out


def blocks_from(lines, gap=95):
    blocks, cur, last = [], [], None
    for y, t in lines:
        if last is not None and y - last > gap and cur:
            blocks.append(cur)
            cur = []
        cur.append((y, t))
        last = y
    if cur:
        blocks.append(cur)
    return blocks


def green_bands(img_right):
    im = img_right.convert("RGB").resize((img_right.width // 4, img_right.height // 4))
    px = im.load()
    w, h = im.size
    bands, cur = [], None
    for y in range(h):
        g = sum(1 for x in range(0, w, 2)
                if px[x, y][1] > px[x, y][0] + 6 and px[x, y][1] > px[x, y][2] + 6
                and px[x, y][1] > 150)
        if g * 2 > w * 0.3:
            cur = [y, y] if cur is None else [cur[0], y]
        else:
            if cur and cur[1] - cur[0] >= 3:
                bands.append((cur[0] * 4, cur[1] * 4))
            cur = None
    if cur and cur[1] - cur[0] >= 3:
        bands.append((cur[0] * 4, cur[1] * 4))
    return bands


def clean_opt(text):
    t = text
    t = NOISE.sub(" ", t)
    t = re.sub(r"^[\s(（©®@e\[]*(?:[A-Da-d1-4][)）.。、:：]?)?\s*", "", t)  # 徽章
    t = re.sub(r"\s+", " ", t).strip(" .。|、")
    return t


def parse_page(path, cut_frac=0.5):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    left = im.crop((0, 0, int(w * cut_frac), h))
    right = im.crop((int(w * cut_frac), 0, w, h))

    stim = " ".join(t for y, t in lines_from(ocr_words(left))
                    if len(t.strip()) > 3 and "READ-ONLY" not in t
                    and not re.match(r"^(Section|Directions|Highlights|Kevin)", t))
    stim = re.sub(r"\s+", " ", stim).strip()

    rlines = lines_from(ocr_words(right))
    # 顶部UI区（页眉/按钮行）直接按 y 扔掉
    rlines = [(y, t) for y, t in rlines if y > 420]
    blocks = blocks_from(rlines)
    bands = green_bands(right)

    core = [b for b in blocks if not any(
        re.search(r"收进错题本|返回成绩|统计样本|选择率已显示", t) for _, t in b)]
    # 面板 = 含"你的答案"或"本题暂无答案解析"的块
    panel = None
    panel_i = next((i for i, b in enumerate(core)
                    if any("你的答案" in t or "暂无答案解析" in t for _, t in b)), None)
    if panel_i is not None:
        panel = core[panel_i]
        core = core[:panel_i]

    # 题干 = 最后一块之外的first块；选项 = 题干后面最多4块
    if not core:
        return {"file": os.path.basename(path), "stem": "", "stimulus": stim,
                "opts": [], "correct": None, "panel": None}
    stem = " ".join(t for _, t in core[0]).strip()
    opt_blocks = core[1:5]

    opts = [clean_opt(" ".join(t for _, t in b)) for b in opt_blocks]

    # 正确答案：绿带命中选项块
    correct = None
    for i, b in enumerate(opt_blocks):
        y0, y1 = b[0][0], b[-1][0]
        for (gy0, gy1) in bands:
            if gy0 - 40 <= y1 and gy1 + 40 >= y0:
                correct = "ABCD"[i]
                break
        if correct:
            break
    # 面板校验：底部汇总"你的答案X 正确答案Y"——取面板里最后一个独立A-D字母
    panel_txt = " ".join(t for _, t in panel) if panel else ""
    letters = re.findall(r"(?<![A-Za-z])([A-D])(?![A-Za-z])", panel_txt)
    panel_correct = letters[-1] if letters else None
    if correct and panel_correct and correct != panel_correct:
        correct = panel_correct + "|" + correct   # 冲突标记，人工复核
    elif not correct:
        correct = panel_correct

    return {"file": os.path.basename(path), "stem": stem, "stimulus": stim,
            "opts": opts, "correct": correct,
            "panel": panel_txt[:120]}


def main():
    jobs = {
        "rw": sorted(glob.glob("/Users/feixiao/Desktop/sat训练题库/Screenshot*.png")),
        "math": sorted(glob.glob("/Users/feixiao/Desktop/sat Math素材/Screenshot*.png")),
    }
    pages = []
    for tag, fs in jobs.items():
        for f in fs:
            p = parse_page(f)
            p["tag"] = tag
            pages.append(p)
    full = [p for p in pages if len(p["opts"]) == 4 and p["correct"]
            and not str(p["correct"]).startswith("|")]
    conflict = [p for p in pages if p["correct"] and str(p["correct"]).startswith("|")]
    print("总页 %d | 4选项+答案 %d | 答案冲突 %d | 无答案 %d | 选项不全 %d" %
          (len(pages), len(full), len(conflict),
           sum(1 for p in pages if not p["correct"]),
           sum(1 for p in pages if len(p["opts"]) != 4)))
    json.dump(pages, open(os.path.join(OUT, "draft.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    import sys
    main()
