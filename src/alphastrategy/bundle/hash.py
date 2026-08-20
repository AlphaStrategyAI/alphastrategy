import hashlib


def content_hash(members: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in members if p != "bundle.yaml"):
        h.update(path.encode("utf-8") + b"\0")
        h.update(members[path] + b"\0")
    return h.hexdigest()


def bundle_id_from_hash(sha256_hex: str) -> str:
    return "asb_" + sha256_hex[:16]
