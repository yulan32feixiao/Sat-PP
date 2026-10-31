#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 draft.json 构建「我的题库」（只收英语题）。

流程：清洗 → 过滤(4选项+答案) → 与官方/2026两库去重 → 归类 → mybank.bin
判分依据：只看复盘页标准答案（correct 字段）。
"""
import difflib
import gzip
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SAT = os.path.dirname(HERE)


def norm_text(s):
    """去重/比对用的规范形：小写、只留字母数字。"""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def clean_rw_option(t):
    t = re.sub(r"\(?\*\)?", " ", t)                 # (*) 徽章
    t = re.sub(r"\b[OoQ]\d{1,3}\b", " ", t)          # O15 类样本数碎片
    t = re.sub(r"\d+\s*/\s*\d+", " ", t)             # 0/15
    t = re.sub(r"[\u4e00-\u9fff]+", " ", t)          # 中文章节：你的/正确/选择率/样本…
    t = re.sub(r"\s+[ABCD]$", " ", t)                # 尾部孤立选项字母
    t = re.sub(r"^\s*[)()©®@ePp.。、:：|—-]+\s*", " ", t)
    # 徽章碎片：括号包单字母，如 (>x) (a) (c)
    t = re.sub(r"(?<!\w)[>(（()]{1,2}[a-z][)<）)（(]{1,2}(?!\w)", " ", t)
    t = re.sub(r"^\s*[a-z]{1,2}[)）]\s*", " ", t)    # ra) ic) oo)
    # 复盘页划线选项被渲染两遍：相邻词重叠折叠（manifes ifest → manifest）
    toks = t.split()
    out = []
    for tok in toks:
        if out and len(out[-1]) >= 4 and len(tok) >= 4:
            a, b = out[-1], tok
            for ov in range(min(len(a), len(b)), 2, -1):
                if a[-ov:] == b[:ov]:
                    out[-1] = a + b[ov:]
                    break
            else:
                out.append(tok)
        else:
            out.append(tok)
    t = " ".join(out)
    while re.search(r"\s+[a-zA-Z]$", t):             # 尾部孤立字母
        t = re.sub(r"\s+[a-zA-Z]$", "", t)
    t = re.sub(r"\s+", " ", t).strip(" .。、|—-o")
    # 末段清理：样本数碎片(017/116/6)、连串大写杂音(ANT)、纯标点/数字碎片(6、0)、()
    toks = [x for x in t.split()
            if not re.fullmatch(r"[0oO\d]{2,4}|[A-Z]{2,}", x)
            and not re.fullmatch(r"[\W\d]{1,3}", x)]
    t = " ".join(toks)
    return t


def classify_rw(stem):
    s = (stem or "").lower()
    if re.search(r"most logical and precise word|most nearly means", s):
        return "Words in Context", "vocab"
    if re.search(r"conventions of standard english", s):
        return "Standard English Conventions", "grammar"
    if re.search(r"most logical transition|transition", s):
        return "Transitions", "grammar"
    return "Reading", "reading"


def main():
    pages = json.load(open(os.path.join(HERE, "mybank_ocr", "draft.json")))
    import gzip
    mock = json.loads(gzip.decompress(open(os.path.join(SAT, "mock2026.bin"), "rb").read()))
    ref = []
    bb = os.path.join(SAT, "bank.bin")
    if os.path.exists(bb):
        ref += json.loads(gzip.decompress(open(bb, "rb").read()))
    ref += mock["questions"]
    ref_norm = [(norm_text(q.get("sti", ""))[-90:] + norm_text(q.get("ste", ""))[:90])
                for q in ref]
    ref_set = set(ref_norm)

    kept, skipped_dup, skipped_bad = [], 0, 0
    seen = set()
    for p in pages:
        if p["tag"] != "rw":
            continue
        if len(p["opts"]) != 4 or not p["correct"] or "|" in str(p["correct"]):
            skipped_bad += 1
            continue
        stem = re.sub(r"\s+", " ", p["stem"]).strip()
        stim = re.sub(r"\s+", " ", p["stimulus"]).strip()
        # 左栏OCR会带上界面中文页眉：掐掉开头直到第一个英文单词
        stim = re.sub(r"^[^A-Za-z\"“($]*", "", stim)
        opts = [clean_rw_option(o) for o in p["opts"]]
        if len(stem) < 12 or any(len(o) < 1 for o in opts):
            skipped_bad += 1
            continue
        key = norm_text(stim)[-90:] + norm_text(stem)[:90]
        # 库内去重：原文匹配或高相似模糊匹配
        dup = key in ref_set or any(
            difflib.SequenceMatcher(None, key, r).ratio() > 0.92 for r in ref_set)
        if dup or key in seen:
            skipped_dup += 1
            continue
        seen.add(key)
        sk, cat = classify_rw(stem)
        kept.append({
            "stimulus": stim, "stem": stem, "opts": opts,
            "answer": p["correct"], "sk": sk, "cat": cat,
        })

    questions = []
    for i, q in enumerate(kept, 1):
        qid = "my.rw.%03d" % i
        questions.append({
            "id": qid, "sec": 1, "cat": q["cat"], "sk": q["sk"], "df": "M",
            "ty": "mcq", "sti": q["stimulus"], "ste": q["stem"],
            "op": q["opts"], "an": [q["answer"]],
            "ra": "来源：Bluebook 式复盘页截图 OCR 转录；判分以页面所示标准答案为准。",
        })
    data = {
        "sets": [{"id": "my-rw", "setId": "my", "sec": 1,
                  "title": "我的英语题（截图转录）", "n": len(questions)}],
        "questions": questions,
        "meta": {"source": "本人做题复盘截图 OCR 转录（只收带标准答案的英语题）",
                 "importedAt": "2026-10-31"},
    }
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    open(os.path.join(SAT, "mybank.bin"), "wb").write(gzip.compress(js, 9))
    print("收录 %d 题 | 重复跳过 %d | 不合格跳过 %d" % (len(questions), skipped_dup, skipped_bad))
    from collections import Counter
    print("分类:", Counter(q["cat"] for q in questions))
    print("文件: mybank.bin %.2fMB" % (len(gzip.compress(js, 9)) / 1e6))


if __name__ == "__main__":
    main()
