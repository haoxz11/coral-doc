#!/usr/bin/env python3
"""coral-doc 导入缓存：分桶布局的查询/写入/迁移工具。

缓存根目录 ~/.coral-doc/，两个维度分开分桶（桶 = 键哈希前 2 位十六进制，
每桶一个小 JSON 文件，避免单个文件随文档量无限膨胀）：

  libraries/<库地址sha256>/<sha256(nodeId)前2位>.json   桶内 {nodeId: 导入记录, ...}
  uploads/<实例目录>/<图片sha256前2位>.json              桶内 {图片sha256: 上传记录, ...}

子命令：
  hash            <图片文件路径>                          打印文件内容的 sha256（去重键）
  lookup          <库地址> <nodeId>                       查文档导入记录（无则输出 {}，退出码 1）
  record-import   <库地址> <nodeId> <字段=value>…         写入/更新文档记录（同键覆盖式更新）
  lookup-upload   <实例> <图片sha256>                     查图片上传记录（无则输出 {}，退出码 1）
  record-upload   <实例> <图片sha256> <url> <name>        写入图片上传记录
  migrate                                                 把 v1 单文件 imports.json 迁到分桶布局

读写一律走本脚本：原子写、损坏桶自动备份后按空处理；不要手改缓存文件。
"""

import hashlib
import json
import os
import sys
from datetime import datetime

CACHE_ROOT = os.path.expanduser("~/.coral-doc")
V1_FILE = os.path.join(CACHE_ROOT, "imports.json")


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def bucket_prefix(key: str) -> str:
    """桶名 = sha256(键) 前 2 位十六进制（nodeId 用；图片哈希直接取自身前 2 位）。"""
    return sha256_str(key)[:2]


def lib_dir(library: str) -> str:
    """库地址转目录：完整 sha256，避免特殊字符/过深路径。"""
    return os.path.join(CACHE_ROOT, "libraries", sha256_str(library))


def instance_dir_name(instance: str) -> str:
    """实例地址转目录名：剥 scheme、去尾斜杠；绝对路径形式的兜底键（库地址）改用哈希。"""
    s = instance.strip()
    if "://" in s:
        s = s.split("://", 1)[1]
    s = s.rstrip("/")
    if s.startswith("/"):
        return "lib-" + sha256_str(s)[:16]
    return s.replace("/", "_")


def upload_path(instance: str, image_hash: str) -> str:
    return os.path.join(CACHE_ROOT, "uploads", instance_dir_name(instance), image_hash[:2] + ".json")


def read_bucket(path: str) -> dict:
    """读桶：不存在 → 空；解析失败 → 备份为 <路径>.corrupt-<时间戳> 后按空处理（不静默丢弃）。"""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        bak = f"{path}.corrupt-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.replace(path, bak)
        print(f"warning: 缓存桶损坏，已备份为 {bak}，按空缓存继续（{e}）", file=sys.stderr)
        return {}


def write_bucket(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def cmd_lookup(library: str, doc_id: str) -> int:
    path = os.path.join(lib_dir(library), bucket_prefix(doc_id) + ".json")
    record = read_bucket(path).get(doc_id)
    if record is None:
        print("{}")
        return 1
    print(json.dumps(record, ensure_ascii=False))
    return 0


def cmd_record_import(library: str, doc_id: str, *pairs: str) -> int:
    path = os.path.join(lib_dir(library), bucket_prefix(doc_id) + ".json")
    data = read_bucket(path)
    record = data.get(doc_id, {})
    for pair in pairs:
        if "=" not in pair:
            print(f"error: 字段必须是 key=value 形式: {pair}", file=sys.stderr)
            return 2
        k, v = pair.split("=", 1)
        record[k] = v
    record["exported_at"] = now()  # 语义 = 最近一次导入时间，每次写入都刷新
    data[doc_id] = record
    write_bucket(path, data)
    print(json.dumps(record, ensure_ascii=False))
    return 0


def cmd_hash(path: str) -> int:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    print(h.hexdigest())
    return 0


def cmd_lookup_upload(instance: str, image_hash: str) -> int:
    record = read_bucket(upload_path(instance, image_hash)).get(image_hash)
    if record is None:
        print("{}")
        return 1
    print(json.dumps(record, ensure_ascii=False))
    return 0


def cmd_record_upload(instance: str, image_hash: str, url: str, name: str) -> int:
    path = upload_path(instance, image_hash)
    data = read_bucket(path)
    data[image_hash] = {"url": url, "name": name, "uploaded_at": now()}
    write_bucket(path, data)
    print(json.dumps(data[image_hash], ensure_ascii=False))
    return 0


def cmd_migrate() -> int:
    if not os.path.exists(V1_FILE):
        print(f"v1 文件不存在，无需迁移: {V1_FILE}")
        return 0
    with open(V1_FILE, encoding="utf-8") as f:
        v1 = json.load(f)
    if v1.get("version") != 1:
        print(f"无法识别的版本: {v1.get('version')}", file=sys.stderr)
        return 2
    lib_n = up_n = 0
    for library, lib in v1.get("libraries", {}).items():
        for doc_id, record in lib.get("imports", {}).items():
            path = os.path.join(lib_dir(library), bucket_prefix(doc_id) + ".json")
            data = read_bucket(path)
            data[doc_id] = record
            write_bucket(path, data)
            lib_n += 1
    for instance, ups in v1.get("uploads", {}).items():
        for image_hash, record in ups.items():
            path = upload_path(instance, image_hash)
            data = read_bucket(path)
            data[image_hash] = record
            write_bucket(path, data)
            up_n += 1
    bak = V1_FILE + ".v1.bak"
    os.replace(V1_FILE, bak)
    print(f"迁移完成：文档记录 {lib_n} 条、图片记录 {up_n} 条；原文件保留为 {bak}")
    return 0


def main(argv: list) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, args = argv[1], argv[2:]
    if cmd == "hash" and len(args) == 1:
        return cmd_hash(*args)
    if cmd == "lookup" and len(args) == 2:
        return cmd_lookup(*args)
    if cmd == "record-import" and len(args) >= 2:
        return cmd_record_import(*args)
    if cmd == "lookup-upload" and len(args) == 2:
        return cmd_lookup_upload(*args)
    if cmd == "record-upload" and len(args) == 4:
        return cmd_record_upload(*args)
    if cmd == "migrate" and not args:
        return cmd_migrate()
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
