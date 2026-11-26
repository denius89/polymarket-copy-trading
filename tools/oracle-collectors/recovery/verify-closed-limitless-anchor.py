"""Verify adoption of an existing Base cursor without changing its height or hash."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

spec = importlib.util.spec_from_file_location(
    "checkpoint", Path(__file__).with_name("closed-limitless-checkpoint.py")
)
checkpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint)

anchor_hash = "0x" + "ab" * 32
cursor_hash = "0x" + "cd" * 32
anchor = {"chainId": 8453, "number": "120", "hash": anchor_hash}
legacy_scope = {"sessionId": "fixture-session", "writer": "fixture-writer"}
scope = {**legacy_scope, "activationAnchor": anchor}


def witness(method, selector, transactions):
    assert method == "eth_getBlockByNumber" and transactions is False
    height = 125 if selector == "finalized" else int(selector, 16)
    block = {
        "number": hex(height),
        "hash": anchor_hash if height == 120 else cursor_hash,
        "timestamp": hex(100 if height == 120 else 110),
    }
    return block, block.copy()


with TemporaryDirectory() as folder:
    path = Path(folder).resolve() / "checkpoint.json"
    initial = {"scope": legacy_scope, "height": 123, "hash": cursor_hash}
    path.write_text(json.dumps(initial))
    path.chmod(0o600)

    def resume(approval=(anchor_hash, 105), persist=True):
        job = checkpoint.Checkpoint(path, scope, 120, witness, lambda item: None, activation_anchor=approval)
        with job.lock():
            return job.resume(persist_seed=persist), job.digest

    assert resume(persist=False) == (123, cursor_hash)
    assert json.loads(path.read_text()) == initial
    for invalid in [("0x" + "ff" * 32, 105), (anchor_hash, 99)]:
        try:
            resume(approval=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid anchor was accepted")
        assert json.loads(path.read_text()) == initial
    assert resume() == (123, cursor_hash)
    assert json.loads(path.read_text()) == {**initial, "scope": scope}
    assert resume() == (123, cursor_hash)

print("PASS read-only preflight, rejected anchors, verified adoption, and restart")
