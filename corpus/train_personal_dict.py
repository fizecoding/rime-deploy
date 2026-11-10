# -*- coding: utf-8 -*-
"""用语料生成 Rime 个人词频词典。

用法: python3 train_personal_dict.py <corpus.txt> <frost_dir> <out_dict.yaml>

逻辑:
1. 把白霜已启用的词表转成 jieba 用户词典, 保证分词口径与输入法词库一致
2. 统计语料中 >=2 字纯中文词频
3. 已收录词: 权重提升 (不低于原权重)
4. 未收录词: pypinyin 注音后收录 (>=5 次才收)
"""
import math
import re
import sys
from collections import Counter
from pathlib import Path

import jieba
from pypinyin import lazy_pinyin

CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")

# 白霜 rime_frost.dict.yaml 中已启用的表 (与仓库默认 import_tables 一致, 不含 tencent)
FROST_TABLES = [
    "cn_dicts/8105", "cn_dicts/41448", "cn_dicts/GB18030-2022",
    "cn_dicts/base", "cn_dicts/ext", "cn_dicts/others", "cn_dicts/corrections",
]
# 细胞词库全部启用 (与 import_tables 后半段一致)
CELL = ["medication", "industry_product", "exthot", "chess", "chess2", "animal",
        "game", "idiom", "sport", "media", "name", "food", "history", "computer",
        "geography", "literature", "music", "movie", "buy", "compound", "composite"]

def load_frost_words(frost_dir: Path):
    """返回 {word: (pinyin, weight)}"""
    words = {}
    tables = [f"{t}.dict.yaml" for t in FROST_TABLES] + [f"cn_dicts_cell/{t}.dict.yaml" for t in CELL]
    for rel in tables:
        p = frost_dir / rel
        if not p.exists():
            continue
        started = False
        for line in p.read_text(encoding="utf-8").splitlines():
            if not started:
                if line.strip() == "...":
                    started = True
                continue
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3 and parts[2].strip().isdigit():
                w, py, wt = parts[0].strip(), parts[1].strip(), int(parts[2])
                # 同词多音取权重高的
                if w not in words or wt > words[w][1]:
                    words[w] = (py, wt)
    return words

def main():
    corpus_path = Path(sys.argv[1]).expanduser()
    frost_dir = Path(sys.argv[2]).expanduser()
    out_path = Path(sys.argv[3]).expanduser()

    frost_words = load_frost_words(frost_dir)
    print(f"白霜词表: {len(frost_words)} 词条")

    # jieba 用户词典: 用白霜词表对齐分词
    for w, (_py, wt) in frost_words.items():
        jieba.add_word(w, freq=max(1, min(wt, 500000)))

    counter = Counter()
    with open(corpus_path, encoding="utf-8") as f:
        for line in f:
            for tok in jieba.cut(line.strip(), HMM=True):
                if CJK.match(tok):
                    counter[tok] += 1

    freq_words = {w: c for w, c in counter.items() if c >= 3}
    print(f"语料词种: {len(counter)}, >=3 次的: {len(freq_words)}")

    boosted, added = [], []
    for w, c in freq_words.items():
        new_wt = int(1500 + 600 * math.sqrt(c))
        new_wt = min(new_wt, 80000)
        if w in frost_words:
            py, old_wt = frost_words[w]
            if new_wt > old_wt:
                boosted.append((w, py, new_wt))
        elif c >= 5 and len(w) <= 6:
            py = " ".join(lazy_pinyin(w))
            added.append((w, py, min(int(300 + 300 * math.sqrt(c)), 60000)))

    boosted.sort(key=lambda x: -x[2])
    added.sort(key=lambda x: -x[2])
    print(f"提权: {len(boosted)} 词, 新收录: {len(added)} 词")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Rime dictionary\n# encoding: utf-8\n")
        f.write("# 个人词频词典: 由微信语料训练生成 (train_personal_dict.py)\n")
        f.write("---\nname: personal\nversion: \"1.0\"\nsort: by_weight\n...\n")
        f.write("# 提权词 (白霜已收录, 按个人语料提升权重)\n")
        for w, py, wt in boosted:
            f.write(f"{w}\t{py}\t{wt}\n")
        f.write("# 新词 (白霜未收录, 个人高频)\n")
        for w, py, wt in added:
            f.write(f"{w}\t{py}\t{wt}\n")
    print(f"输出: {out_path}")

if __name__ == "__main__":
    main()
