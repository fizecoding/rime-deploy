# -*- coding: utf-8 -*-
"""从解密后的微信 Mac 4.x 消息库中提取本人发送的文本消息。

用法: python3 extract_my_messages.py <decrypted_message_dir> <my_wxid> <out_txt> [out_json]
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

import zstandard

MSG_DBS = ["message_0.db", "message_1.db", "message_2.db"]
GROUP_PREFIX = re.compile(r"^[a-zA-Z0-9_-]{3,64}@[a-zA-Z0-9_.-]{2,32}:\n")   # 群聊 wxid 前缀
GH_PREFIX = re.compile(r"^gh_[a-zA-Z0-9_-]{5,40}:\n")                        # 公众号前缀
ANY_PREFIX = re.compile(r"^[^\n]{1,80}:\n")

def _to_text(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return v

def get_content(row_message, row_compress):
    """返回 (text, used_compress)"""
    row_message = _to_text(row_message)
    if row_message:
        return row_message, False
    if row_compress:
        try:
            raw = zstandard.ZstdDecompressor().decompress(row_compress)
            return raw.decode("utf-8", "replace"), True
        except Exception:
            return None, False
    return None, False

def clean(text, is_own_group_prefix):
    t = text.strip()
    if not t:
        return None
    # 群聊消息带 "发送者wxid:\n" 前缀（含自己发的），剥掉
    if GROUP_PREFIX.match(t) or GH_PREFIX.match(t):
        t = t.split(":\n", 1)[1].strip()
    elif is_own_group_prefix and ANY_PREFIX.match(t):
        t = ANY_PREFIX.sub("", t).strip()
    if not t:
        return None
    # 引用回复开头 "「xxx」 的新消息" / 系统性内容跳过
    if t.startswith("「") and "」" in t[:80] and ("\n" in t):
        pass  # 引用消息正文在后面，保留全文
    return t

def main():
    msg_dir = Path(sys.argv[1]).expanduser()
    my_wxid = sys.argv[2]
    out_txt = Path(sys.argv[3]).expanduser()
    out_json = Path(sys.argv[4]).expanduser() if len(sys.argv) > 4 else None

    records = []
    stats = {"tables": 0, "my_text_msgs": 0, "compressed": 0, "dropped": 0}

    for db_name in MSG_DBS:
        db_path = msg_dir / db_name
        if not db_path.exists():
            continue
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = con.cursor()

        own = cur.execute("SELECT rowid FROM Name2Id WHERE user_name = ?", (my_wxid,)).fetchone()
        if not own:
            print(f"[{db_name}] Name2Id 中未找到 {my_wxid}，跳过")
            con.close()
            continue
        own_id = own[0]

        tables = [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]

        for table in tables:
            stats["tables"] += 1
            try:
                rows = cur.execute(
                    f"SELECT create_time, message_content, compress_content FROM {table} "
                    f"WHERE real_sender_id = ? AND local_type = 1", (own_id,)).fetchall()
            except sqlite3.DatabaseError as e:
                print(f"  [warn] {db_name}/{table}: {e}")
                continue
            for create_time, mc, cc in rows:
                text, used_c = get_content(mc, cc)
                if used_c:
                    stats["compressed"] += 1
                if not text:
                    stats["dropped"] += 1
                    continue
                cleaned = clean(text, is_own_group_prefix=True)
                if not cleaned:
                    stats["dropped"] += 1
                    continue
                records.append({"ts": create_time, "text": cleaned})
                stats["my_text_msgs"] += 1
        con.close()

    records.sort(key=lambda r: r["ts"])
    with open(out_txt, "w", encoding="utf-8") as f:
        for r in records:
            f.write(r["text"].replace("\r", "") + "\n")
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=0)

    total_chars = sum(len(r["text"]) for r in records)
    print(json.dumps(stats, ensure_ascii=False))
    print(f"输出: {out_txt}")
    print(f"消息数: {len(records)}  总字符: {total_chars}")
    if records:
        span = (records[0]["ts"], records[-1]["ts"])
        import datetime
        print(f"时间范围: {datetime.datetime.fromtimestamp(span[0])} ~ {datetime.datetime.fromtimestamp(span[1])}")

if __name__ == "__main__":
    main()
