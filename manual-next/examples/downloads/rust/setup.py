from pathlib import Path
import json
import os

root_value = os.environ.get("SOURCE_ROOT")
if not root_value:
    raise SystemExit("Set SOURCE_ROOT to the absolute SDK source checkout path")
root = Path(root_value).expanduser().resolve()
a, b = root / "crates/zvision", root / "crates/zvision-ops"
if not (a / "Cargo.toml").is_file() or not (b / "Cargo.toml").is_file():
    raise SystemExit("SOURCE_ROOT must contain crates/zvision and crates/zvision-ops")
def toml_path(path):
    return json.dumps(path.as_posix(), ensure_ascii=False)
manifest = """[package]
name = "zvision-manual-facade-examples"
version = "0.1.0"
edition = "2024"
publish = false

[workspace]

[dependencies]
zvision = { path = %s }
zvision-ops = { path = %s }

[[bin]]
name = "zvision-manual-facade-examples"
path = "main.rs"
""" % (toml_path(a), toml_path(b))
Path(__file__).with_name("Cargo.toml").write_text(manifest, encoding="utf-8")
print("Cargo.toml configured for SOURCE_ROOT")
