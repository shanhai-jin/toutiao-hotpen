# -*- coding: utf-8 -*-
"""check_article.py — 「头条热笔」双模式成稿自检（原创实现）

用法：
    python check_article.py <文件.txt 或 目录>          # 头条长文模式（800-1500字，校导语）
    python check_article.py --micro <文件.txt 或 目录>   # 微头条模式（100-500字，不校导语）

检查三层：
  A. 格式层：字数区间 / 标题15-30字 / 零破折号 / 零英文残留 / 段落数 /
     单段≤4句且≤155字 / 段首不断裂 / 汉字数字=0
  B. 去AI痕层：AI高频套话=0（FAIL级） / 连接词指纹≥3（提示） / 句长过于均匀（提示）
  C. 结构层：长文导语 80-120 字（│ 开头行）

规则说明：
  - 问号数量为提示项，不阻断（强制问句下限会倒逼模板化，正是平台治理打击特征）
  - 任何 FAIL 项存在 → 结论 NEED FIX；全部通过 → ALL OK
  - 退出码恒为 0（便于批处理继续跑），以结论文本为准

本文件为「头条热笔」项目原创代码。
"""

import argparse
import glob
import io
import os
import pathlib
import re
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    import hotpen_cn_rules as cn_rules
except ImportError:
    cn_rules = None

# ---------- 模式参数 ----------
MODES = {
    "article": {"label": "article", "body_min": 800, "body_max": 1500, "para_min": 8, "lead": True},
    "micro": {"label": "micro", "body_min": 100, "body_max": 500, "para_min": 3, "lead": False},
}

# ---------- 去AI痕词库（头条热笔自建） ----------
AI_FILLERS = [
    "综上所述", "总而言之", "总的来说", "由此可见", "不难看出",
    "值得注意的是", "需要指出的是", "众所周知", "毫无疑问", "不可否认",
    "毋庸置疑", "简而言之", "换句话说", "归根结底", "总体来看",
    "可以说", "在一定程度上", "不得不说", "说白了就是",
]

CONNECTIVES = ["首先", "其次", "再者", "然而", "因此", "此外", "与此同时",
               "一方面", "另一方面", "最后"]

SENT_SPLIT = re.compile(r"[。！？]+")
DASH_CHARS = "—―﹘－"
ENGLISH_RE = re.compile(r"[A-Za-zＡ-Ｚａ-ｚ]+")


def read_text(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()


def iter_targets(target):
    if os.path.isdir(target):
        for p in sorted(glob.glob(os.path.join(target, "*.txt"))):
            yield p
    else:
        yield target


def parse_article(text):
    """解析成稿：首行标题、次行署名、可选│导语、其余为正文段落。"""
    lines = [ln.rstrip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln.strip() != "" or True]
    # 去掉纯空行前的结构性空行，保留段落结构
    title = ""
    sig = ""
    lead = ""
    body_paras = []
    nonempty = [ln.strip() for ln in text.splitlines() if ln.strip()]
    idx = 0
    if nonempty:
        title = nonempty[0]
        idx = 1
        if len(nonempty) > 1 and not nonempty[1].startswith("│"):
            sig = nonempty[1]
            idx = 2
        if idx < len(nonempty) and nonempty[idx].startswith("│"):
            lead = nonempty[idx].lstrip("│").strip()
            idx += 1
    for ln in nonempty[idx:]:
        body_paras.append(ln)
    return title, sig, lead, body_paras


def para_sentences(para):
    return [s for s in SENT_SPLIT.split(para) if s.strip()]


def check_file(path, mode):
    m = MODES[mode]
    issues = []   # FAIL 级
    warns = []    # 提示级
    text = read_text(path)
    title, sig, lead, paras = parse_article(text)

    body = "".join(paras)
    n_body = len(re.sub(r"\s", "", body))
    n_title = len(re.sub(r"\s", "", title))
    n_q = body.count("？") + body.count("?")

    # A. 格式层
    if not (m["body_min"] <= n_body <= m["body_max"]):
        issues.append("正文字数 %d 不在 %d-%d 区间" % (n_body, m["body_min"], m["body_max"]))
    if not (15 <= n_title <= 30):
        issues.append("标题 %d 字，需 15-30 字" % n_title)
    for part, seg in (("标题", title), ("正文", body)):
        for ch in DASH_CHARS:
            if ch in seg:
                issues.append("%s含破折号（%s）" % (part, ch))
                break
        if ENGLISH_RE.search(seg):
            found = ENGLISH_RE.search(seg).group(0)
            issues.append("%s含英文残留（%s…）" % (part, found[:10]))

    if len(paras) < m["para_min"]:
        issues.append("段落 %d 段，少于下限 %d" % (len(paras), m["para_min"]))
    for idx, para in enumerate(paras, 1):
        sents = para_sentences(para)
        if len(sents) > 4:
            issues.append("段%d超过4句（%d句）" % (idx, len(sents)))
        if len(re.sub(r"\s", "", para)) > 155:
            issues.append("段%d超过155字" % idx)
        # 段首断裂：陈述短句单独成句（反问句"你敢信吗？"开头属合法钩子，不拦）
        if len(sents) >= 2 and len(sents[0]) <= 7 and sents[0].endswith("。"):
            issues.append("段%d段首断裂（短句单独成句：%s）" % (idx, sents[0]))

    # 汉字数字
    if cn_rules is not None:
        hits = cn_rules.scan(body) + cn_rules.scan(title)
        if hits:
            uniq = sorted(set(w for w, _ in hits))
            issues.append("含汉字数字（应改阿拉伯数字）: " + "、".join(uniq[:8]))

    # C. 结构层：导语
    if m["lead"]:
        if not lead:
            issues.append("缺少导语行（以 │ 开头的独立行）")
        else:
            n_lead = len(re.sub(r"\s", "", lead))
            if not (80 <= n_lead <= 120):
                issues.append("导语 %d 字，需 80-120 字" % n_lead)

    # B. 去AI痕层
    filler_hits = []
    low = body
    for w in AI_FILLERS:
        if w in low:
            filler_hits.append(w)
    if filler_hits:
        issues.append("AI高频套话命中 %d 处: %s" % (len(filler_hits), "、".join(sorted(set(filler_hits))[:6])))

    conn_hits = sorted(set(w for w in CONNECTIVES if w in body))
    if len(conn_hits) >= 3:
        warns.append("连接词指纹 %d 个（%s），疑似模板化行文"
                     % (len(conn_hits), "、".join(conn_hits[:6])))

    sents = []
    for p in paras:
        sents.extend(len(re.sub(r"\s", "", s)) for s in para_sentences(p) if s.strip())
    if len(sents) >= 6:
        std = statistics.pstdev(sents)
        if std < 6.0:
            warns.append("句长标准差 %.1f（<6，句式过于均匀，低突发性特征）" % std)

    if n_q < 3:
        warns.append("问号仅 %d 个（<3，提示不阻断）" % n_q)

    # 汇总
    status = "ALL OK" if not issues else "NEED FIX"
    head = "[%s][%s] %s 标题%d字 正文%d字 %d段 问号%d" % (
        "OK" if not issues else "FAIL", m["label"], path, n_title, n_body, len(paras), n_q)
    out = [head]
    for it in issues:
        out.append("    - " + it)
    for w in warns:
        out.append("    * [提示] " + w)
    out.append("    " + status)
    return "\n".join(out), (not issues)


def main():
    ap = argparse.ArgumentParser(description="头条热笔 · 成稿双模式自检")
    ap.add_argument("targets", nargs="+", help="文件.txt 或 目录")
    ap.add_argument("--micro", action="store_true", help="微头条模式（100-500字）")
    args = ap.parse_args()
    mode = "micro" if args.micro else "article"

    all_ok = True
    for t in args.targets:
        for p in iter_targets(t):
            if not os.path.isfile(p):
                print("[SKIP] 不存在: %s" % p)
                continue
            out, ok = check_file(p, mode)
            print(out)
            all_ok = all_ok and ok
    return 0


if __name__ == "__main__":
    sys.exit(main())
