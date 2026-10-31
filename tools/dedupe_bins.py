#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题库级联去重（用户策略，2026-10-31确认）：
  1) 官方库内部重复 → 官方库里也删（只留一份）
  2) 其他库与官方重复 → 保留官方版，其他库删掉
  3) 2026 与 2025 重复 → 算 2026 的，2025 删掉
  4) 各库内部互相重复 → 删（保留一份）
  顺序 = 官方 → 2026 → 我的题库 → 2025（越新越优先）。
指纹 = 规范化(文章尾80+题干头80+选项A头40)；近重复用4-gram倒排预筛+SequenceMatcher(≥0.93)。
幂等：重跑导入后执行本脚本可重放。"""
import difflib
import gzip
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SAT = os.path.dirname(HERE)


def norm2(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def fp(q):
    return norm2(q.get("sti", ""))[-80:] + norm2(q.get("ste", ""))[:80] + norm2(q.get("op", [""])[0] if q.get("op") else "")[:40]


def shingles(k, n=8):
    if len(k) < n:
        return {k}
    return {k[i:i + n] for i in range(0, len(k) - n + 1, 2)}


def load(name):
    p = os.path.join(SAT, name)
    if not os.path.exists(p):
        return None
    return json.loads(gzip.decompress(open(p, "rb").read()))


def save(name, d):
    js = json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode()
    open(os.path.join(SAT, name), "wb").write(gzip.compress(js, 9))


class NearIndex:
    """已收录指纹的8-gram倒排索引+候选集评分；
    只对共享shingle≥40%的少数候选做SequenceMatcher(≥0.93判近重)。"""

    def __init__(self):
        self.keys = []
        self.sets = []
        self.index = defaultdict(set)
        self.exact = set()

    def add(self, k):
        i = len(self.keys)
        self.keys.append(k)
        self.exact.add(k)
        sh = shingles(k)
        self.sets.append(sh)
        for s in sh:
            self.index[s].add(i)

    def has_near(self, k):
        if len(k) < 40:
            return False
        qs = shingles(k)
        score = defaultdict(int)
        for s in qs:
            for i in self.index.get(s, ()):
                score[i] += 1
        if not score:
            return False
        need = max(4, int(len(qs) * 0.4))
        cands = sorted([i for i, c in score.items() if c >= need], key=lambda i: -score[i])[:8]
        for i in cands:
            if difflib.SequenceMatcher(None, k, self.keys[i]).ratio() > 0.93:
                return True
        return False


def main():
    bank = load("bank.bin")
    m26 = load("mock2026.bin")
    mine = load("mybank.bin")
    m25 = load("mock2025.bin")
    stats = {}

    # ---- 1) 官方内部去重 ----
    idx = NearIndex()
    seen, kept, dup = set(), [], 0
    for q in bank:
        k = fp(q)
        if k in seen:
            dup += 1
            continue
        seen.add(k)
        idx.add(k)
        kept.append(q)
    stats["官方内部删除"] = dup
    bank = kept

    # ---- 2/3/4) 其他库 ----
    def dedup_against(pool_questions, label):
        n0 = len(pool_questions)
        removed_vs_known, removed_internal = 0, 0
        kept, seen = [], set()
        for q in pool_questions:
            k = fp(q)
            if k in idx.exact:
                removed_vs_known += 1
                continue
            if idx.has_near(k):
                removed_vs_known += 1
                continue
            if k in seen:
                removed_internal += 1
                continue
            seen.add(k)
            idx.add(k)
            kept.append(q)
        stats[label] = {"对已收录库删除": removed_vs_known, "库内删除": removed_internal, "保留": len(kept)}
        return kept

    q26 = dedup_against(m26["questions"], "2026库(vs官方)")
    m26["questions"] = q26
    qmine = dedup_against(mine["questions"], "我的题库(vs官方+2026)")
    mine["questions"] = qmine
    q25 = dedup_against(m25["questions"], "2025库(vs官方+2026+我的)")
    m25["questions"] = q25

    # ---- set 计数修正 ----
    for d in (m26, m25):
        for s in d["sets"]:
            remaining = [q for q in d["questions"] if q["setId"] == s["setId"]]
            after1 = sum(1 for q in remaining if q["mod"] == 1)
            after2 = sum(1 for q in remaining if q["mod"] == 2)
            before = s["m1"] + s["m2"]
            s["dedupRemoved"] = before - (after1 + after2)
            s["m1"], s["m2"] = after1, after2

    save("bank.bin", bank)
    save("mock2026.bin", m26)
    save("mybank.bin", mine)
    save("mock2025.bin", m25)

    total = len(bank) + len(m26["questions"]) + len(mine["questions"]) + len(m25["questions"])
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print(f"去重后总题量: {total} (官方{len(bank)} / 2026 {len(m26['questions'])} / 我的{len(mine['questions'])} / 2025 {len(m25['questions'])})")


if __name__ == "__main__":
    main()
