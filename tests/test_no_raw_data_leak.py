"""
Enforces the dataset-role rule from PREREGISTRATION.md / README in code:
no function in analyze.py or reporting.py may ever receive raw Olist
data as input, and analyze() specifically must never read
true_effects.json (only check_ground_truth_recovery may, and only after
analyze() has already returned).
"""

import ast
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "pipeline"


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


def test_analyze_module_never_imports_raw_olist_paths():
    src = _source("analyze.py")
    assert "data/raw" not in src
    assert "olist_" not in src.lower()


def test_reporting_only_reads_analysis_results():
    src = _source("reporting.py")
    assert "data/raw" not in src
    assert "olist_" not in src.lower()
    assert "true_effects" not in src.lower()
    assert "RESULTS_PATH" in src  # only reads the already-computed results file


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
