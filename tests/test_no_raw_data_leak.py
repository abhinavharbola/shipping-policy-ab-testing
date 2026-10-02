import ast
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "experiment"


def _source(filename):
    return (PACKAGE_DIR / filename).read_text(encoding="utf-8")


def _functions(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _names_used(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _docstring_ids(tree):
    ids = set()
    for node in [tree] + [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]:
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            ids.add(id(node.body[0].value))
    return ids


def _string_constants(tree):
    skip = _docstring_ids(tree)
    return [
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip
    ]


def _no_raw_data_string_literals(filename):
    tree = ast.parse(_source(filename))
    for value in _string_constants(tree):
        lowered = value.lower()
        assert "data/raw" not in lowered, f"{filename} references data/raw in: {value!r}"
        assert "olist_" not in lowered, f"{filename} references an Olist raw file in: {value!r}"


def test_true_effects_path_is_used_only_by_the_recovery_check():
    tree = ast.parse(_source("analyze.py"))
    referencing = [f.name for f in _functions(tree) if "TRUE_EFFECTS_PATH" in _names_used(f)]
    assert referencing == ["check_ground_truth_recovery"]


def test_analyze_module_never_references_raw_olist_paths():
    _no_raw_data_string_literals("analyze.py")


def test_reporting_only_reads_analysis_results():
    _no_raw_data_string_literals("reporting.py")
    tree = ast.parse(_source("reporting.py"))
    for value in _string_constants(tree):
        assert "true_effects" not in value.lower()
    top_level_names = {
        n.id for node in tree.body if isinstance(node, ast.Assign)
        for n in node.targets if isinstance(n, ast.Name)
    }
    assert "RESULTS_PATH" in top_level_names
    assert "TRUE_EFFECTS_PATH" not in top_level_names


def test_main_runs_the_analysis_before_the_recovery_check():
    tree = ast.parse(_source("analyze.py"))
    main = next(f for f in _functions(tree) if f.name == "main")
    order_by_line = sorted(
        (n.lineno, n.func.id) for n in ast.walk(main)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    )
    names = [name for _, name in order_by_line]
    assert names.index("analyze") < names.index("check_ground_truth_recovery")


def test_randomize_and_analyze_never_read_potential_outcome_columns_together():
    tree = ast.parse(_source("analyze.py"))
    literals = set(_string_constants(tree))
    assert not {"aov_control", "aov_treatment"} & literals
    assert not {"complaint_control", "complaint_treatment"} & literals
