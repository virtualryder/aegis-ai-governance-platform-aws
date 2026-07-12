import os, shutil, pathlib
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
print("staged", n, "modules from", src)
