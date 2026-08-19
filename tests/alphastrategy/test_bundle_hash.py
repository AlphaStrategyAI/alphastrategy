import hashlib
from alphastrategy.bundle.hash import content_hash, bundle_id_from_hash
from alphastrategy.bundle.archive import is_allowed_member

def test_hash_excludes_bundle_yaml_and_is_order_stable():
    a = {"bundle.yaml": b"x", "lineage.yaml": b"b", "strategy.dsl.yaml": b"a"}
    b = {"strategy.dsl.yaml": b"a", "lineage.yaml": b"b", "bundle.yaml": b"CHANGED"}
    assert content_hash(a) == content_hash(b)
    assert len(content_hash(a)) == 64
    assert bundle_id_from_hash(content_hash(a)).startswith("asb_")

def test_rejects_python_member():
    assert is_allowed_member("strategy.dsl.yaml") is True
    assert is_allowed_member("evil.py") is False
    assert is_allowed_member("../x") is False
    assert is_allowed_member("evidence/summary.yaml") is True
