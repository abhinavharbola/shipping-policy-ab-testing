import ast
import io
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_DIRS = ["src", "tests", "dashboard", "scripts"]
TEXT_SUFFIXES = {".py", ".md", ".toml", ".txt", ".json"}
SKIP_PARTS = {"__pycache__", ".git", "raw", "simulated", "calibration"}
EM_DASH = chr(0x2014)


def python_files():
    for d in PY_DIRS:
        yield from sorted((ROOT / d).rglob("*.py"))


def text_files():
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES and not SKIP_PARTS & set(path.parts):
            yield path


def test_no_comments_in_python_files():
    offenders = []
    for path in python_files():
        source = path.read_text(encoding="utf-8")
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                offenders.append(f"{path.relative_to(ROOT)}:{tok.start[0]}")
    assert offenders == []


def test_no_em_dashes_anywhere():
    offenders = [
        str(p.relative_to(ROOT)) for p in text_files()
        if EM_DASH in p.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_no_unused_imports_or_locals():
    problems = []
    for path in python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imported[(a.asname or a.name).split(".")[0]] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    imported[a.asname or a.name] = node.lineno
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for name, line in imported.items():
            if name not in used:
                problems.append(f"{path.relative_to(ROOT)}:{line} unused import {name}")
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            stores, loads = {}, set()
            for n in ast.walk(fn):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            stores.setdefault(t.id, n.lineno)
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                    loads.add(n.id)
            for name, line in stores.items():
                if name not in loads:
                    problems.append(f"{path.relative_to(ROOT)}:{line} unused local {name}")
    assert problems == []


def test_no_unclosed_json_load_of_open():
    offenders = [
        str(p.relative_to(ROOT)) for p in python_files()
        if p.name != "test_repo_hygiene.py" and "json.load(open(" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_dashboard_uses_no_deprecated_container_width_argument():
    source = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")
    assert "use_container_width" not in source
