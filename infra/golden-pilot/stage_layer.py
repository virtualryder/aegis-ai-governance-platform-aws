#!/usr/bin/env python3
"""Windows/cross-platform equivalent of prepare_layer.sh — stage platform_core into layer/python.

`sam build` needs no make/Docker; this just copies the reviewed engine (stdlib-only) from the single
source of truth (../../platform_core) into layer/python/platform_core. On Linux/macOS/CI use
prepare_layer.sh; on Windows (where bash may be WSL with different path semantics) run:  py -3.12 stage_layer.py
"""
import os
import pathlib
import shutil

here = pathlib.Path(__file__).resolve().parent
src = (here / ".." / ".." / "platform_core").resolve()
dst = here / "layer" / "python" / "platform_core"
if (here / "layer" / "python").exists():
    shutil.rmtree(here / "layer" / "python")
n = 0
for root, dirs, files in os.walk(src):
    dirs[:] = [d for d in dirs if d not in ("tests", "__pycache__")]
    for f in files:
        if not f.endswith(".py"):
            continue
        rel = pathlib.Path(root).relative_to(src) / f
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pathlib.Path(root) / f, out)
        n += 1
print(f"staged {n} modules from {src}")
