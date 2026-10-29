# -*- coding: utf-8 -*-
"""fetch_hot.py — 「头条热笔」多源热榜抓取（原创实现）

用途：一键抓取多个公开热榜，输出合并 JSON，供推选题环节使用。
数据源：uapis.cn 公开热榜接口（只读 GET，无密钥、无上传、无任何个人数据外发）。

用法：
    python fetch_hot.py 输出路径/hot_raw.json            # 默认五源
    python fetch_hot.py 输出路径/hot_raw.json --types baidu,toutiao

接口说明：
    GET https://uapis.cn/api/v1/misc/hotboard?type=<源>
    返回 {"type","update_time","list":[{index,title,url,hot_value,extra}]}
    接口如变更，请查阅 uapis.cn 官方文档后更新 BASE 与 TYPES。
"""

import argparse
import io
import json
import os
import sys
import urllib.request
import urllib.parse

BASE = "https://uapis.cn/api/v1/misc/hotboard"
TYPES = ["baidu", "weibo", "douyin", "toutiao", "zhihu"]
TIMEOUT = 15
UA = "toutiao-hotpen/1.0 (open-source skill; local read-only fetch)"


_opener = urllib.request.build_opener()
_opener.addheaders = [("User-Agent", UA)]


def fetch_one(source):
    url = BASE + "?" + urllib.parse.urlencode({"type": source})
    with _opener.open(url, timeout=TIMEOUT) as conn:
        payload = conn.read().decode("utf-8")
    data = json.loads(payload)
    items = []
    for it in data.get("list", []):
        items.append({
            "source": source,
            "rank": it.get("index"),
            "title": (it.get("title") or "").strip(),
            "url": it.get("url", ""),
            "hot_value": it.get("hot_value", ""),
        })
    return items, data.get("update_time", "")


def main():
    ap = argparse.ArgumentParser(description="头条热笔 · 多源热榜抓取")
    ap.add_argument("out", help="输出 JSON 路径")
    ap.add_argument("--types", default=",".join(TYPES),
                    help="逗号分隔的源，默认全部：%s" % ",".join(TYPES))
    args = ap.parse_args()

    sources = [s.strip() for s in args.types.split(",") if s.strip()]
    merged = {"fetched_at": "", "sources": {}, "items": []}
    ok_sources = []

    for s in sources:
        try:
            items, updated = fetch_one(s)
            merged["sources"][s] = {"count": len(items), "update_time": updated}
            merged["items"].extend(items)
            ok_sources.append(s)
            print("[OK] %s：%d 条" % (s, len(items)))
        except Exception as e:  # 单源失败不阻断其他源
            merged["sources"][s] = {"error": str(e)[:200]}
            print("[ERR] %s：%s" % (s, str(e)[:120]))

    # 交叉热度排序：同题多源同现排前（推选题环节的三源同现=首推依据）
    from collections import Counter
    title_count = Counter(it["title"] for it in merged["items"])
    merged["items"].sort(key=lambda x: (-title_count[x["title"]], x["source"], x["rank"] or 999))
    merged["cross_source_topics"] = [
        {"title": t, "sources": c} for t, c in title_count.most_common() if c >= 2
    ]

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)

    print("\n完成：共 %d 条，来自 %d/%d 个源 → %s" % (
        len(merged["items"]), len(ok_sources), len(sources), args.out))
    if merged["cross_source_topics"]:
        print("多源同现话题 %d 个（优先核查这些）：" % len(merged["cross_source_topics"]))
        for t in merged["cross_source_topics"][:5]:
            print("  [%d源] %s" % (t["sources"], t["title"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
