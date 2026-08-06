#!/usr/bin/env python3
"""Validate the sci-paper plugin contract without optional dependencies.

Run with no arguments. The validator checks repository shape, release metadata,
active skill policy, documentation authority, the shared feedback schema, core
runtime imports/CLI entry points, linter exit semantics, tests, and CI wiring.
"""

from __future__ import annotations

import ast
import contextlib
import importlib
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
SKILLS = REPO / "skills"
SCHEMA = "sci-paper.feedback.v1"

NORMATIVE_SKILLS = {
    "paper",
    "de-ai",
    "condense",
    "paper-review",
    "figure-review",
    "final-review",
    "proposal-polish",
}
CORE_IMPORTS = {
    "ai_ism_lint",
    "deai_docstructure",
    "deai_features",
    "deai_feedback",
    "deai_metrics",
    "deai_oracle",
    "deai_structure",
    "deai_voice",
    "rewrite_reward",
}
CORE_CLIS = CORE_IMPORTS - {"deai_feedback"}
REQUIRED_TESTS = {
    "test_ai_ism_lint_cli.py",
    "test_deai_docstructure.py",
    "test_deai_feedback.py",
    "test_rewrite_reward.py",
    "test_train_voice_model.py",
}
REQUIRED_FINDING_FIELDS = {
    "finding_id",
    "kind",
    "layer",
    "rule",
    "scope",
    "location",
    "message",
    "observed",
    "reference",
    "normalized_distance",
    "confidence",
    "measurement_status",
    "priority",
    "recommended_action",
    "detector",
    "source_trace",
    "disposition",
    "before_after",
}
STALE_REVIEW_MARKERS = {
    "A–O": "review dimensions must use A–R",
    "A-O": "review dimensions must use A–R",
    "A–Q": "review dimensions must use A–R",
    "A-Q": "review dimensions must use A–R",
    "zero-issue convergence": "review completion must use typed disposition semantics",
    "0 issue across all": "review completion must not require zero advisories",
}


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValidationError(f"cannot read {path.relative_to(REPO)}: {error}") from error


def load_json(path: Path) -> dict:
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as error:
        raise ValidationError(f"{path.relative_to(REPO)} is not valid JSON: {error}") from error
    require(isinstance(value, dict), f"{path.relative_to(REPO)} must contain a JSON object")
    return value


def check_manifests() -> str:
    plugin = load_json(REPO / ".claude-plugin" / "plugin.json")
    market = load_json(REPO / ".claude-plugin" / "marketplace.json")
    for key in ("name", "version", "description"):
        require(plugin.get(key), f"plugin.json missing required key {key!r}")

    plugin_v = str(plugin["version"])
    require(market.get("metadata", {}).get("version") == plugin_v,
            "marketplace metadata.version does not match plugin.json")
    inner = next(
        (item for item in market.get("plugins", [])
         if item.get("name") == plugin["name"]),
        None,
    )
    require(inner is not None,
            f"marketplace plugins[] has no entry named {plugin['name']!r}")
    require(inner.get("version") == plugin_v,
            "marketplace plugin entry version does not match plugin.json")
    require(inner.get("description") == plugin.get("description"),
            "marketplace and plugin descriptions must match")

    readme = read_text(REPO / "README.md")
    changelog = read_text(REPO / "CHANGELOG.md")
    require(f"Current: **v{plugin_v}**" in readme,
            f"README current version is not v{plugin_v}")
    require(re.search(rf"^## v{re.escape(plugin_v)}\s+[—-]", changelog, re.MULTILINE) is not None,
            f"CHANGELOG has no top-level entry for v{plugin_v}")
    # Versioned doc headers ("current as of vX") must track the release;
    # they sat outside every check until the v0.24.0 release shipped with
    # two stale ones.
    for doc_name in ("docs/DEAI_SUBSYSTEM.md", "docs/EVALUATION.md"):
        first_line = read_text(REPO / doc_name).splitlines()[0]
        require(f"v{plugin_v}" in first_line,
                f"{doc_name} header line does not carry v{plugin_v}")
    return f"manifests, doc headers, and release version agree ({plugin_v})"


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str] | None:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    frontmatter: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    return frontmatter


def skill_documents() -> dict[str, str]:
    require(SKILLS.is_dir(), "skills/ directory missing")
    result: dict[str, str] = {}
    for directory in sorted(path for path in SKILLS.iterdir() if path.is_dir()):
        skill_path = directory / "SKILL.md"
        require(skill_path.is_file(), f"{skill_path.relative_to(REPO)} missing")
        text = read_text(skill_path)
        frontmatter = parse_frontmatter(text)
        require(frontmatter is not None,
                f"{skill_path.relative_to(REPO)} has no YAML frontmatter")
        for key in ("name", "description"):
            require(frontmatter.get(key),
                    f"{skill_path.relative_to(REPO)} frontmatter missing {key!r}")
        require(frontmatter["name"] == directory.name,
                f"{skill_path.relative_to(REPO)} name does not match directory")
        result[directory.name] = text
    require(result, "skills/ has no skill directories")
    return result


def check_skills() -> str:
    documents = skill_documents()
    missing = sorted(NORMATIVE_SKILLS - documents.keys())
    require(not missing, f"required normative skills missing: {', '.join(missing)}")
    for name in sorted(NORMATIVE_SKILLS):
        require("docs/SCIPAPER_STANDARD.md" in documents[name],
                f"skills/{name}/SKILL.md does not reference SCIPAPER_STANDARD.md")

    for name, text in documents.items():
        for marker, explanation in STALE_REVIEW_MARKERS.items():
            require(marker not in text,
                    f"skills/{name}/SKILL.md contains stale marker {marker!r}: {explanation}")

    standard = read_text(REPO / "docs" / "SCIPAPER_STANDARD.md")
    for token in (
        SCHEMA,
        "integrity_blocker",
        "l0_target",
        "advisory",
        "measured",
        "degraded",
        "unmeasured",
        "not_applicable",
        "rejected_as_false_positive",
    ):
        require(token in standard, f"SCIPAPER_STANDARD.md missing contract token {token!r}")
    return f"skills and normative standard agree ({len(documents)} skills)"


def check_documentation_boundaries() -> str:
    # v0.21.0: docs/EVALUATION.md is the single canonical evaluation record
    # (all five documentation files live under docs/). A root-level copy is
    # the stub-plus-canonical accumulation pattern the move eliminated.
    evaluation = read_text(REPO / "docs" / "EVALUATION.md")
    require("(SCIPAPER_STANDARD.md)" in evaluation,
            "docs/EVALUATION.md must link the normative standard as a sibling "
            "(SCIPAPER_STANDARD.md) — a bare name mention is not enough")
    require(SCHEMA in evaluation,
            f"docs/EVALUATION.md must identify the {SCHEMA} contract")

    require(not (REPO / "EVALUATION.md").exists(),
            "root EVALUATION.md found; docs/EVALUATION.md is the single "
            "canonical record — remove the root copy")

    require(not (REPO / "docs" / "HANDOFF.md").exists(),
            "docs/HANDOFF.md is a transient session artifact and must not ship")
    return "normative/evaluation documentation boundaries are unambiguous"


def product_tool_files() -> set[str]:
    scripts = {path.name for path in TOOLS.glob("*.py") if path.name != "validate_plugin.py"}
    data_assets = {path.name for path in TOOLS.glob("*.txt")}
    return scripts | data_assets


def parse_declared_count(text: str, heading: str) -> int:
    match = re.search(rf"^### {re.escape(heading)} \((\d+)\)\s*$", text, re.MULTILINE)
    require(match is not None, f"README missing '{heading} (N)' heading")
    return int(match.group(1))


def check_registry_counts() -> str:
    documents = skill_documents()
    products = product_tool_files()
    readme = read_text(REPO / "README.md")
    declared_skills = parse_declared_count(readme, "Skills")
    declared_tools = parse_declared_count(readme, "Tools")
    require(declared_skills == len(documents),
            f"README declares {declared_skills} skills but repository has {len(documents)}")
    require(declared_tools == len(products),
            f"README declares {declared_tools} tools but repository ships {len(products)}")

    listed_tools = set(re.findall(r"\| `tools/([^`]+)` \|", readme))
    require(listed_tools == products,
            "README tool registry mismatch: "
            f"missing={sorted(products - listed_tools)}, extra={sorted(listed_tools - products)}")

    plugin = load_json(REPO / ".claude-plugin" / "plugin.json")
    expected = rf"Ships {len(documents)} skills\b.*\b{len(products)} tools"
    require(re.search(expected, plugin["description"]) is not None,
            "plugin description skill/tool counts do not match repository")
    return f"README and manifest registries agree ({len(documents)} skills, {len(products)} tools)"


def check_tools_syntax() -> str:
    files = sorted(TOOLS.glob("*.py"))
    require(files, "tools/ has no Python files")
    for path in files:
        try:
            ast.parse(read_text(path), filename=str(path))
        except SyntaxError as error:
            raise ValidationError(f"{path.relative_to(REPO)}: SyntaxError: {error}") from error
    return f"tool syntax valid ({len(files)} Python files)"


def check_runtime_contract() -> str:
    sys.path.insert(0, str(TOOLS))
    try:
        modules = {name: importlib.import_module(name) for name in sorted(CORE_IMPORTS)}
    except Exception as error:
        raise ValidationError(f"core runtime import failed: {error}") from error
    finally:
        if sys.path and sys.path[0] == str(TOOLS):
            sys.path.pop(0)

    feedback = modules["deai_feedback"]
    require(feedback.SCHEMA_VERSION == SCHEMA,
            f"deai_feedback schema is {feedback.SCHEMA_VERSION!r}, expected {SCHEMA!r}")
    finding = feedback.make_finding(
        kind="advisory",
        layer="L2",
        rule="validator-smoke",
        scope="sentence",
        message="validator smoke finding",
        action="no action",
        detector="validate_plugin",
    )
    require(REQUIRED_FINDING_FIELDS <= finding.keys(),
            "feedback finding missing fields: "
            f"{sorted(REQUIRED_FINDING_FIELDS - finding.keys())}")
    require(set(feedback.KINDS) == {"integrity_blocker", "l0_target", "advisory"},
            "feedback consequence classes drifted")
    require(set(feedback.STATUSES) ==
            {"measured", "degraded", "unmeasured", "not_applicable"},
            "feedback measurement statuses drifted")
    require(set(feedback.DISPOSITIONS) ==
            {"pending", "acted", "accepted", "rejected_as_false_positive"},
            "feedback dispositions drifted")

    for name in sorted(CORE_CLIS):
        result = subprocess.run(
            [sys.executable, str(TOOLS / f"{name}.py"), "--help"],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        require(result.returncode == 0,
                f"tools/{name}.py --help failed ({result.returncode}): {result.stderr.strip()}")
    return f"core imports, schema, and CLI entry points valid ({len(CORE_IMPORTS)} modules)"


def check_linter_exit_semantics() -> str:
    sys.path.insert(0, str(TOOLS))
    try:
        lint_module = importlib.import_module("ai_ism_lint")
    finally:
        if sys.path and sys.path[0] == str(TOOLS):
            sys.path.pop(0)

    with tempfile.TemporaryDirectory(prefix="sci-paper-validate-") as raw:
        root = Path(raw)
        fixtures = {
            "clean.tex": "We measure the response. The data constrain the model.\n",
            "l0.tex": "We delve into the response.\n",
            "tier-b-cap.tex": "\\section{Introduction}\nFurthermore, the result is stable.\n",
            "tier-b-excess.tex": (
                "\\section{Introduction}\n"
                "Furthermore, the result is stable.\n\n"
                "Furthermore, the estimate is reproducible.\n"
            ),
        }
        paths: dict[str, Path] = {}
        for name, text in fixtures.items():
            path = root / name
            path.write_text(text, encoding="utf-8")
            paths[name] = path

        def run(path: Path) -> int:
            return lint_module.lint(
                path,
                None,
                distribution=False,
                structure=False,
                document_structure=False,
                output_format="json",
                output=root / f"{path.stem}.json",
            )

        require(run(paths["clean.tex"]) == 0, "clean input must return linter status 0")
        require(run(paths["l0.tex"]) == 1, "Tier A input must return linter status 1")
        require(run(paths["tier-b-cap.tex"]) == 0,
                "one Tier B occurrence per section/word must return status 0")
        require(run(paths["tier-b-excess.tex"]) == 1,
                "Tier B excess must return linter status 1")
        # The exit-2 fixture intentionally lints a nonexistent file; swallow
        # the linter's expected "file not found" stderr line so validator
        # output does not open with a spurious error.
        with contextlib.redirect_stderr(io.StringIO()):
            missing_status = run(root / "missing.tex")
        require(missing_status == 2, "missing input must return linter status 2")
    return "linter exit semantics valid (0=no L0, 1=L0, 2=execution failure)"


def check_tests_and_ci() -> str:
    tests_dir = REPO / "tests"
    present = {path.name for path in tests_dir.glob("test_*.py")}
    require(REQUIRED_TESTS <= present,
            f"required tests missing: {sorted(REQUIRED_TESTS - present)}")
    ci = read_text(REPO / ".github" / "workflows" / "ci.yml")
    require("python tools/validate_plugin.py" in ci,
            "CI does not run tools/validate_plugin.py")
    require("python -m unittest discover -s tests -v" in ci,
            "CI does not run the unit/CLI test suite")
    return f"required tests and CI wiring present ({len(present)} test files)"


def main() -> int:
    checks = (
        check_manifests,
        check_skills,
        check_documentation_boundaries,
        check_registry_counts,
        check_tools_syntax,
        check_runtime_contract,
        check_linter_exit_semantics,
        check_tests_and_ci,
    )
    try:
        for check in checks:
            print(f"  [ok] {check()}")
    except ValidationError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("validate_plugin: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
