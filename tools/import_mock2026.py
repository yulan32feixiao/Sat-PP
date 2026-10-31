#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入「更新到26年10月SAT最新真题题库+答案」里的全部 2026 年卷子。

产出:
  mock2026.bin   gzip 的 JSON: {"sets":[...], "questions":[...]}
  fig2026/*.png  数学配图（按题号命名，页面按需加载）

来源 PDF 是考后回忆重排版（Word→LibreOffice），文字层完整、带【答案】【解析】标记。
解析策略：PyMuPDF 逐页取行级文本(含上下标检测)和图片矩形，按 y 坐标流式拼接，
用状态机切 Module / 题号 / 选项 / 答案 / 解析，图片归属最近的当前题。
"""
import gzip, json, os, re, sys
from collections import Counter

import pymupdf

SRC = "/Users/feixiao/Desktop/SAT dl/更新到26年10月SAT最新真题题库+答案"
OUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # sat/
YEAR = os.environ.get("IMPORT_YEAR", "2026")
FIG_DIR = os.environ.get("IMPORT_FIGDIR", os.path.join(OUT_DIR, "fig2026"))
BIN_OUT = os.environ.get("IMPORT_BIN", os.path.join(OUT_DIR, "mock2026.bin"))
PREFIX_ID = os.environ.get("IMPORT_PREFIX", "m26")

RW_DIR = os.path.join(SRC, "阅读文法")
MA_DIR = os.path.join(SRC, "数学")

# 我在 2026-10-31 审查时人工验算过的套子: setId -> 说明
AUDITED = {
    "202610-1": "阅读7题+数学18题答案逐一验算全对（2026-10-31 审查）",
}

WATERMARK = re.compile(r"^\s*留学考试资料库\s*$")
MODULE_RE = re.compile(r"^Module\s*([12])\s*$", re.I)
QNUM_RE = re.compile(r"^(\d{1,2})\s*\.\s*$")
OPT_RE = re.compile(r"^([A-D])\s*[\.、]\s*(.*)$")
ANS_RE = re.compile(r"^【答案】\s*(.+?)\s*$")
EXP_RE = re.compile(r"^【解析】\s*$")
# 阅读语法题干开头（用于切 passage / stem）
STEM_RE = re.compile(
    r"^(Which choice|According to the text|As used in the text|Based on the|"
    r"The author|What |Which statement|Which finding|Which question|Which result|"
    r"Which point|Which option|Which consideration|Complete the|In line|The text|"
    r"Which of the following|Over the course|Which choice most|Which detail)", re.I)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---- 数学符号修复 ----
# 源 PDF 是 Word 重排版，上标格式已丢（整行同字号），只能按记号法还原：
#   x2−169 -> x<sup>2</sup>−169        变量后紧跟数字 = 指数
#   2,100(a)x -> 2,100(a)<sup>x</sup>  数字/小数括号后跟单字母 = 指数
_MATH_VAR = "xynmakpqrstdfg hvwub".replace(" ", "")
RE_VAR_EXP = re.compile(r"(?<![A-Za-z<])([%s])(\d{1,2})(?=[^0-9(]|$)" % _MATH_VAR)
RE_PAREN_EXP = re.compile(r"([\d\.)])\(([\d\.]*[a-z]?[\d\.]*)\)([a-z])(?!\()" )


def fix_math_notation(html):
    if "src=" in html:
        return html
    out = []
    pos = 0
    for m in re.finditer(r"<[^>]+>", html):
        out.append(_fix_seg(html[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_fix_seg(html[pos:]))
    return "".join(out)


def _fix_seg(seg):
    seg = RE_PAREN_EXP.sub(r"\1(\2)<sup>\3</sup>", seg)
    # 括号指数先处理，避免变量指数把 (1.035)x 的 x 改掉
    seg = RE_VAR_EXP.sub(r"\1<sup>\2</sup>", seg)
    return seg


def line_html(line_spans):
    """一行 spans -> HTML。小字号且基线抬高的 span 视为上标，包 <sup>。"""
    if not line_spans:
        return ""
    sizes = Counter(round(sp["size"], 1) for sp in line_spans)
    dom = sizes.most_common(1)[0][0]
    out, i = [], 0
    while i < len(line_spans):
        sp = line_spans[i]
        sup = sp["size"] < dom * 0.85
        buf = esc(sp["text"])
        if sup:
            # 合并连续上标
            j = i + 1
            while j < len(line_spans) and line_spans[j]["size"] < dom * 0.85:
                buf += esc(line_spans[j]["text"]); j += 1
            out.append("<sup>" + buf + "</sup>")
            i = j
        else:
            out.append(buf); i += 1
    return "".join(out).strip()


def paragraphs(lines_html, width_hint=42):
    """把行列表合成段落：短行且以句末标点收尾视为分段。"""
    if not lines_html:
        return ""
    maxw = max(len(re.sub(r"<[^>]+>", "", h)) for h in lines_html) or 1
    paras, cur = [], []
    for h in lines_html:
        cur.append(h)
        plain = re.sub(r"<[^>]+>", "", h)
        if len(plain) < maxw * 0.62 and re.search(r'[.?!:”\)】]$', plain):
            paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    return "".join("<p>%s</p>" % p for p in paras if p.strip())


def join_flow(lines_html):
    """题干/选项用：直接拼成一段。"""
    s = ""
    prev = None
    for h in lines_html:
        if prev is not None:
            # PDF 断行连字符
            if prev.endswith("-"):
                s = s[:-1]
            else:
                s += " "
        s += h
        prev = h
    return s.strip()


def classify_rw(stem_text):
    """按题干把 RW 题归到官方技能名（用于界面标签，非官方标注）。"""
    t = stem_text
    if re.search(r"most logical and precise word|most nearly means", t, re.I):
        return "Words in Context", "vocab"
    if re.search(r"conventions of Standard English", t, re.I):
        return "Standard English Conventions", "grammar"
    if re.search(r"most logical transition|transition that", t, re.I):
        return "Transitions", "grammar"
    if re.search(r"most effectively uses data|data from the table", t, re.I):
        return "Quantitative Evidence", "reading"
    if re.search(r"main purpose|function of the underlined|best describes the main", t, re.I):
        return "Craft and Structure", "reading"
    if re.search(r"most logically completes|logical conclusion|inference", t, re.I):
        return "Inference", "reading"
    if re.search(r"best states the main purpose|supports the (claim|hypothesis)|weakens", t, re.I):
        return "Information and Ideas", "reading"
    return "Reading & Writing", "reading"


def parse_pdf(path, sec):
    doc = pymupdf.open(path)
    items = []  # 按阅读顺序: {kind:text/img, page, y, ...}
    for pno, page in enumerate(doc):
        d = page.get_text("dict")
        for block in d["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                html = line_html(line["spans"])
                if not html:
                    continue
                items.append({"kind": "t", "page": pno, "y": line["bbox"][1],
                              "text": html,
                              "plain": re.sub(r"<[^>]+>", "", html)})
        for info in page.get_images(full=True):
            xref = info[0]
            for rect in page.get_image_rects(xref):
                if rect.width < 18 or rect.height < 18:
                    continue
                items.append({"kind": "i", "page": pno, "y": rect.y0,
                              "xref": xref, "rect": rect, "native_w": info[2]})
        page_items = [it for it in items if it["page"] == pno]
        page_items.sort(key=lambda it: it["y"])
        # 按页排序重写 items（跨页顺序 = 页码顺序）
    # 重新按页+ y 排序
    items.sort(key=lambda it: (it["page"], it["y"]))

    # ---- 状态机 ----
    cur_mod = [0]     # 当前模块号（0 = 还没遇到 Module 标题）
    questions = []          # 每个: {num, mod, body:[seg], figs:[], opts:{}, ans, exp:[]}
    cur = None
    mode = "body"           # body | opt | exp
    cur_opt = None

    def close_q():
        nonlocal cur, mode, cur_opt
        cur = None; mode = "body"; cur_opt = None

    for it in items:
        if it["kind"] == "i":
            if cur is not None:
                if mode == "opt" and cur_opt:
                    # 图片选项：频率表这类题，四个选项各是一张图
                    cur["opts"][cur_opt].append({"__fig__": it})
                else:
                    cur["figs"].append(it)
            continue
        txt = it["plain"].strip()
        html = it["text"]
        if not txt:
            continue
        if WATERMARK.match(txt):
            continue
        m = MODULE_RE.match(txt)
        if m:
            close_q()
            cur_mod[0] = int(m.group(1))
            continue
        if QNUM_RE.match(txt) and cur_mod[0]:
            n = int(QNUM_RE.match(txt).group(1))
            # 解析段落里可能出现 "= 11." 这种被单独排成一行的句尾，只有
            # 紧接上一题编号 +1 的数字才认作新题号。
            if cur is None or n == cur["num"] + 1:
                close_q()
                cur = {"num": n, "mod": cur_mod[0],
                       "body": [], "figs": [], "opts": {}, "opt_order": [], "ans": "", "exp": []}
                questions.append(cur)
                mode = "body"
                continue
        if cur is None:
            continue
        m = ANS_RE.match(txt)
        if m:
            cur["ans"] = m.group(1)
            mode = "exp"
            continue
        if EXP_RE.match(txt) or txt in ("【解析】", "答案解析：", "题目文本翻译："):
            mode = "exp"
            continue
        m = OPT_RE.match(txt)
        if m and mode != "exp":
            letter = m.group(1)
            rest = re.sub(r"<[^>]+>", "", html)
            # 选项字母行: 用原文重建（去掉行首 "A."）
            stripped = re.sub(r"^[A-D]\s*[\.、]\s*", "", html, count=1)
            cur["opts"][letter] = [stripped] if stripped.strip() else []
            cur["opt_order"].append(letter)
            cur_opt = letter
            mode = "opt"
            continue
        if mode == "opt" and cur_opt:
            cur["opts"][cur_opt].append(html)
        elif mode == "exp":
            cur["exp"].append(html)
        else:
            # 图按 y 位置插进 body 序列
            cur["body"].append({"t": "txt", "html": html, "y": it["y"], "page": it["page"]})
    close_q()
    return questions, doc


def fig_html(fig_items, qid, fig_index, stats):
    """导出一张配图，返回 <img>。"""
    outs = []
    for k, it in enumerate(fig_items):
        page = it["_page_obj"]
        rect = it["rect"]
        zoom = min(2.5, max(1.0, 640.0 / rect.width))
        pix = page.get_pixmap(clip=rect, matrix=pymupdf.Matrix(zoom, zoom))
        name = "%s_%d.png" % (qid, k)
        pix.save(os.path.join(FIG_DIR, name))
        stats["figs"] += 1
        # 有效分辨率: 原始嵌入像素 / 显示英寸
        native = it.get("native_w") or pix.width
        eff_ppi = native / max(rect.width / 72.0, 0.1)
        if eff_ppi < 100:
            stats["low_figs"] += 1
        outs.append('<img src="fig2026/%s" alt="figure" style="max-width:100%%;border:1px solid #e2e8f0;border-radius:6px;margin:6px 0">' % name)
    return outs


def assemble_blocks(q):
    """题内所有元素(文本行+图)按位置拼成块序列: [("P",[行...]) | ("F",fig)]。"""
    segs = [dict(s, kind="txt") for s in q["body"]]
    for f in q["figs"]:
        segs.append({"kind": "fig", "page": f["page"], "y": f["y"], "fig": f})
    segs.sort(key=lambda s: (s["page"], s["y"]))
    blocks, buf = [], []
    for s in segs:
        if s["kind"] == "txt":
            buf.append(s["html"])
        else:
            if buf:
                blocks.append(("P", buf)); buf = []
            blocks.append(("F", s["fig"]))
    if buf:
        blocks.append(("P", buf))
    return blocks


def build_questions(questions, doc, set_id, sec, stats):
    out = []

    def render_fig(fig, maxw=640):
        page = doc[fig["page"]]
        rect = fig["rect"]
        zoom = min(2.5, max(1.0, maxw / rect.width))
        pix = page.get_pixmap(clip=rect, matrix=pymupdf.Matrix(zoom, zoom))
        pix.save(os.path.join(FIG_DIR, fig["_qid"] + ".png"))
        stats["figs"] += 1
        eff_ppi = (fig.get("native_w") or pix.width) / max(rect.width / 72.0, 0.1)
        if eff_ppi < 100:
            stats["low_figs"] += 1
        return ('<img src="fig2026/%s.png" alt="figure" style="max-width:%dpx;'
                'border:1px solid #e2e8f0;border-radius:6px;margin:6px 0">' % (fig["_qid"], maxw))

    def blocks_to_html(blocks):
        out_h = []
        for kind, payload in blocks:
            if kind == "P":
                out_h.append(paragraphs(payload))
            else:
                out_h.append(render_fig(payload))
        return "".join(x for x in out_h if x)

    for q in questions:
        mod = q["mod"]
        qid = PREFIX_ID + ".%s.%s%d.%d" % (set_id, "rw" if sec == 1 else "ma", mod, q["num"])
        for k, f in enumerate(q["figs"]):
            f["_qid"] = "%s_%d" % (qid, k)

        # 选项：文本行与图片标记混合（图片选项 = 频率表这类）
        def option_html(lines, letter):
            texts, html, fk = [], [], 0
            for x in lines:
                if isinstance(x, dict) and "__fig__" in x:
                    if texts:
                        html.append(("T", join_flow(texts))); texts = []
                    f = dict(x["__fig__"])
                    f["_qid"] = "%s_o%s_%d" % (qid, letter, fk); fk += 1
                    html.append(("F", render_fig(f, maxw=340)))
                else:
                    texts.append(x)
            if texts:
                html.append(("T", join_flow(texts)))
            return "".join(p for _, p in html)

        opts = [option_html(q["opts"].get(L, []), L) for L in ["A", "B", "C", "D"]]
        opts = [fix_math_notation(o) if "src=" not in o else o for o in opts]
        has_content = any(o.strip() for o in opts)
        ans_raw = (q["ans"] or "").strip()
        is_letter = bool(re.fullmatch(r"[A-D]", ans_raw or ""))

        if is_letter or has_content:
            ty = "mcq"
            ans_list = [ans_raw.upper()] if is_letter else [ans_raw]
        else:
            ty = "spr"
            ans_list = [a.strip() for a in re.split(r"[,，、]", ans_raw) if a.strip()]
            opts = []

        blocks = assemble_blocks(q)

        if sec == 1:
            # 题干起点只在文本行里找，再换算到块坐标切 passage / stem
            text_lines = [h for kind, pl in blocks if kind == "P" for h in pl]
            stem_idx = None
            for i, h in enumerate(text_lines):
                if STEM_RE.match(re.sub(r"<[^>]+>", "", h).strip()):
                    stem_idx = i
                    break
            if stem_idx is None:
                for i in range(len(text_lines) - 1, -1, -1):
                    if re.sub(r"<[^>]+>", "", text_lines[i]).strip().endswith("?"):
                        stem_idx = i
                        break
            if stem_idx is None:
                stem_idx = max(0, len(text_lines) - 1)
            cut_block, cut_line, seen = None, None, 0
            for bi, (kind, pl) in enumerate(blocks):
                if kind != "P":
                    continue
                if seen + len(pl) > stem_idx:
                    cut_block, cut_line = bi, stem_idx - seen
                    break
                seen += len(pl)
            if cut_block is None:            # 切点在最后（或只剩图）
                sti = blocks_to_html(blocks)
                ste = "（阅读文本，见左侧）"
            else:
                pas_blocks = blocks[:cut_block] + [("P", blocks[cut_block][1][:cut_line])]
                stem_blocks = [("P", blocks[cut_block][1][cut_line:])] + blocks[cut_block + 1:]
                sti = blocks_to_html(pas_blocks)
                ste = re.sub(r"</?p>", " ", blocks_to_html(stem_blocks)).strip() \
                      or "（阅读文本，见左侧）"
            sk, cat = classify_rw(ste)
        else:
            sti = ""
            ste = blocks_to_html(blocks)
            sk, cat = "Math (2026真题)", "math"

        df = "M" if mod == 1 else "H"   # 由模块位置推断，非官方难度标注
        exp_html = paragraphs(q["exp"])
        if sec == 2:
            ste = fix_math_notation(ste)
            exp_html = fix_math_notation(exp_html)
            opts = [fix_math_notation(o) for o in opts]

        out.append({
            "id": qid, "sec": sec, "cat": cat, "sk": sk, "df": df, "ty": ty,
            "sti": sti, "ste": ste, "op": opts, "an": ans_list,
            "ra": exp_html, "setId": set_id, "mod": mod, "num": q["num"],
        })
    return out


MONTH_ORDER = {"10": 10, "9": 9, "8": 8, "6": 6, "5": 5, "3": 3}
FALLBACK_SEQ = {}


def set_meta(fname, sec):
    """文件名 -> setId / 排序键 / 标题 / 备注。"""
    base = os.path.splitext(fname)[0]
    m = re.search(YEAR + r"年(\d+)月(?:亚太|北美)?第(\d+)套", base)
    if not m:
        # 无"第N套"的文件名（去重合集等），用月份+文件序号兜底，避免同月多份撞ID
        m2 = re.search(YEAR + r"年(\d+)月", base)
        if not m2:
            return None
        month = m2.group(1)
        FALLBACK_SEQ[month] = FALLBACK_SEQ.get(month, 0) + 1
        nth = "99"
    else:
        month, nth = m.group(1), m.group(2)
    region = "ap" if "亚太" in base else ("na" if "北美" in base else "--")
    sid = YEAR + "%s-%s%s" % (month, nth, "" if region == "--" else "-" + region)
    if nth == "99":
        sid += "-f" + str(FALLBACK_SEQ[month])   # 同月多份合集的区分序号
    if "Easy" in base or "easy" in base:
        sid += "-easy"   # M2-Easy 卷与同场主卷的题目 ID 会撞，必须区分
    note = ""
    for pat, lab in [("只有26题", "原卷仅收26题"), ("M1 18题", "M1 18题+M2 17题（不全）"),
                     ("只有19题", "仅19题（不全）"), ("M2 -Easy", "M2-Easy 低分段版本"),
                     ("M1 23题", "M1 23题+M2 14题（不全）")]:
        if pat in base:
            note = lab
            break
    title = base
    order = (MONTH_ORDER.get(month, 0), int(nth))
    return sid, order, title, note, region


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    sets, all_q = [], []
    problems = []
    for sec, folder in [(1, RW_DIR), (2, MA_DIR)]:
        for fname in sorted(os.listdir(folder)):
            if not fname.startswith(YEAR) or not fname.endswith(".pdf"):
                continue
            if "纯题目" in fname:
                continue
            meta = set_meta(fname, sec)
            if meta is None:
                problems.append(f"{fname}: 文件名无法识别年份/场次，跳过")
                continue
            sid, order, title, note, region = meta
            path = os.path.join(folder, fname)
            try:
                raw, doc = parse_pdf(path, sec)
            except Exception as e:
                problems.append("%s: 解析失败 %s" % (fname, e))
                continue
            stats = {"figs": 0, "low_figs": 0}
            qs = build_questions(raw, doc, sid, sec, stats)
            # 统计与质检
            m1 = [q for q in qs if q["mod"] == 1]
            m2 = [q for q in qs if q["mod"] == 2]
            exp_m = 27 if sec == 1 else 22
            for q in qs:
                if not q["an"]:
                    problems.append("%s Q%d(M%d): 缺答案" % (title, q["num"], q["mod"]))
                if q["ty"] == "mcq" and len([o for o in q["op"] if o]) != 4:
                    problems.append("%s Q%d(M%d): 选项数=%d" % (title, q["num"], q["mod"],
                                                                 len([o for o in q["op"] if o])))
                if not q["ste"]:
                    problems.append("%s Q%d(M%d): 题干为空" % (title, q["num"], q["mod"]))
            base_sid = re.sub(r"-(ap|na)$", "", sid)
            sets.append({
                "id": sid + ("rw" if sec == 1 else "ma"),
                "setId": sid, "sec": sec, "title": title, "region": region,
                "month": order[0], "nth": order[1], "note": note,
                "m1": len(m1), "m2": len(m2), "expected": exp_m,
                "figs": stats["figs"], "lowFigs": stats["low_figs"],
                "audit": AUDITED.get(base_sid, ""),
                "n": len(qs),
            })
            all_q.extend(qs)
            print("%-46s M1=%2d M2=%2d figs=%d low=%d" % (title, len(m1), len(m2),
                                                           stats["figs"], stats["low_figs"]))

    data = {
        "sets": sorted(sets, key=lambda s: (-s["month"], -s["nth"], s["sec"])),
        "questions": all_q,
        "meta": {
            "source": f"第三方考后回忆重排版（留学考试资料库），{YEAR}年卷 {YEAR}-导入",
            "answerProvenance": "答案与中文解析为题库编纂方提供，非 College Board 官方答案键",
            "importedAt": "2026-10-31",
        },
    }
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    gz = gzip.compress(js, 9)
    out = BIN_OUT
    open(out, "wb").write(gz)
    print("\nsets=%d questions=%d  json=%.1fMB -> mock2026.bin=%.2fMB"
          % (len(sets), len(all_q), len(js) / 1e6, len(gz) / 1e6))
    if problems:
        print("\n=== 质检问题 (%d) ===" % len(problems))
        for p in problems[:60]:
            print(" -", p)
        open(os.path.join(OUT_DIR, "tools", "_import_problems.txt"), "w").write("\n".join(problems))


if __name__ == "__main__":
    main()
