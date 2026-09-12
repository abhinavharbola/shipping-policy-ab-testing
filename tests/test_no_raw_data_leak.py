"""
Enforces the dataset-role rule from docs/PREREGISTRATION.md / README in code:
no function in analyze.py or reporting.py may ever receive raw Olist
data as input, and analyze() specifically must never read
true_effects.json (only check_ground_truth_recovery may, and only after
analyze() has already returned).
"""

import ast
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "experiment"


def _source(filename):
    return (PACKAGE_DIR / filename).read_text()


def test_analyze_function_body_does_not_reference_true_effects_path():
    tree = ast.parse(_source("analyze.py"))
    analyze_func = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "analyze"
    )
    names_used = {n.id for n in ast.walk(analyze_func) if isinstance(n, ast.Name)}
    assert "TRUE_EFFECTS_PATH" not in names_used


def test_private_analysis_helpers_do_not_reference_true_effects_path():
    tree = ast.parse(_source("analyze.py"))
    for fname in ("_analyze_primary", "_analyze_guardrail"):
        func = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == fname
        )
        names_used = {n.id for n in ast.walk(func) if isinstance(n, ast.Name)}
        assert "TRUE_EFFECTS_PATH" not in names_used


def _docstring_nodes(tree):
    """Module, class, and function docstrings, so string-literal checks
    below can skip prose (e.g. this file's own comments about raw data)
    and only flag string literals actually used as code, such as a path."""
    docstrings = set()
    candidates = [tree] + [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    for node in candidates:
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstrings.add(id(node.body[0].value))
    return docstrings


def _string_constants_outside_docstrings(tree):
    docstring_ids = _docstring_nodes(tree)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstring_ids
    ]


def _no_raw_data_string_literals(filename):
    tree = ast.parse(_source(filename))
    for value in _string_constants_outside_docstrings(tree):
        lowered = value.lower()
        assert "data/raw" not in lowered, f"{filename} references data/raw in: {value!r}"
        assert "olist_" not in lowered, f"{filename} references an Olist raw file in: {value!r}"


def test_analyze_module_never_imports_raw_olist_paths():
    _no_raw_data_string_literals("analyze.py")


def test_reporting_only_reads_analysis_results():
    _no_raw_data_string_literals("reporting.py")
    tree = ast.parse(_source("reporting.py"))
    for value in _string_constants_outside_docstrings(tree):
        assert "true_effects" not in value.lower(), (
            f"reporting.py references true_effects.json in: {value!r}"
        )
    top_level_names = {
        n.id for node in tree.body if isinstance(node, ast.Assign)
        for n in node.targets if isinstance(n, ast.Name)
    }
    assert "RESULTS_PATH" in top_level_names  # only reads the already-computed results file


def test_check_ground_truth_recovery_is_the_sole_reader_of_true_effects():
    src = _source("analyze.py")
    # true_effects.json / TRUE_EFFECTS_PATH should appear only inside
    # check_ground_truth_recovery and the module-level constant definition
    tree = ast.parse(src)
    functions_referencing_true_effects = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            names_used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            if "TRUE_EFFECTS_PATH" in names_used:
                functions_referencing_true_effects.append(node.name)
    assert functions_referencing_true_effects == ["check_ground_truth_recovery"]



