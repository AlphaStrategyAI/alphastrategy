from pathlib import Path
import zipfile
from alphastrategy.errors import ImportRejected

_ALLOWED = {
    "bundle.yaml", "strategy.dsl.yaml", "market-profile.yaml",
    "parameters.yaml", "risk-envelope.yaml", "lineage.yaml",
}


def is_allowed_member(name: str) -> bool:
    if ".." in name or name.startswith("/") or "\\" in name:
        return False
    lower = name.lower()
    if lower.endswith((".py", ".so", ".dll", ".exe")):
        return False
    if name in _ALLOWED:
        return True
    return name.startswith("evidence/") or name.startswith("conformance/")


def read_asb(path: Path) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if not is_allowed_member(name):
                raise ImportRejected(f"illegal member: {name}")
            members[name] = zf.read(name)
    return members
