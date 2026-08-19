import io
import zipfile
from pathlib import Path
from alphastrategy.bundle.hash import content_hash, bundle_id_from_hash

FIXTURE_DIR = Path(__file__).parent / "golden"


def _members_from_dir() -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    for p in FIXTURE_DIR.rglob("*"):
        if p.is_file():
            rel = p.relative_to(FIXTURE_DIR).as_posix()
            members[rel] = p.read_bytes()
    return members


def build_golden_asb() -> bytes:
    members = _members_from_dir()
    sha = content_hash(members)
    bid = bundle_id_from_hash(sha)
    members["bundle.yaml"] = (
        "schema_version: alphastrategy.bundle/v0\n"
        "dsl_version: alphaloop.dsl/v0\n"
        f"bundle_id: {bid}\n"
        f"content_hash: {sha}\n"
        "created_at: '2026-08-19T00:00:00Z'\n"
        "registry_uri: null\n"
    ).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in sorted(members.items()):
            zf.writestr(name, data)
    return buf.getvalue()


def mutate_member(asb_bytes: bytes, name: str, new: bytes) -> bytes:
    buf_in = io.BytesIO(asb_bytes)
    out = io.BytesIO()
    with zipfile.ZipFile(buf_in) as zin, zipfile.ZipFile(out, "w") as zout:
        for item in zin.infolist():
            data = new if item.filename == name else zin.read(item.filename)
            zout.writestr(item.filename, data)
    return out.getvalue()
