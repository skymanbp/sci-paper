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
TESTS = REPO / "tests"
DOCS = REPO / "docs"
SCHEMA = "sci-paper.feedback.v1"

# docs/ is categorized: the normative contract sits at the root beside the
# index, current engineering references under architecture/, and frozen
# non-authoritative notes under design-notes/.
STANDARD_DOC = "docs/SCIPAPER_STANDARD.md"
DOCS_INDEX = "docs/README.md"
SUBSYSTEM_DOC = "docs/architecture/DEAI_SUBSYSTEM.md"
# The evidence record is a hub plus parts under docs/architecture/evaluation/.
# EVALUATION_DOC is the hub: it carries the contract, the axis-status table, the
# section map, and the release boundary, and is what other documents cite.
# EVALUATION_PARTS_DIR holds the section bodies. Any check that validates a
# recorded measurement must scan the WHOLE record, not just the hub -- a stale
# figure hiding in a part file is exactly the drift these checks exist to catch.
EVALUATION_DOC = "docs/architecture/EVALUATION.md"
EVALUATION_PARTS_DIR = "docs/architecture/evaluation"
DESIGN_NOTES = (
    "docs/design-notes/DEAI_ARCHITECTURE_ROADMAP.md",
    "docs/design-notes/DEAI_FRONTIER.md",
)
# Paths a doc must NOT reappear at. Each entry was a real location before the
# v0.27.0 reorganisation, so a stale copy would read as authoritative.
FORBIDDEN_DOC_COPIES = (
    "EVALUATION.md",
    "docs/EVALUATION.md",
    "docs/DEAI_SUBSYSTEM.md",
    "docs/DEAI_ARCHITECTURE_ROADMAP.md",
    "docs/DEAI_FRONTIER.md",
    "docs/HANDOFF.md",
)

NORMATIVE_SKILLS = {
    "paper",
    "physics",
    "mainline",
    "logic",
    "de-ai",
    "condense",
    "paper-review",
    "figure-review",
    "final-review",
    "calibrate",
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
    # The only check that can see whether a published number still has a
    # source: the artifacts it reads are gitignored, so deleting this file
    # would silently restore the drift it was written to stop.
    "test_published_figures.py",
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
    for doc_name in (SUBSYSTEM_DOC, EVALUATION_DOC):
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

    standard = read_text(REPO / STANDARD_DOC)
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


RE_HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*$", re.MULTILINE)
RE_PAGE_ANCHOR = re.compile(r"\]\(#([^)]+)\)")


def _anchor_slug(heading: str) -> str:
    """GitHub's heading-to-anchor rule, enough of it for these documents.

    Inline markup is stripped, the text lowercased, spaces become hyphens, and
    everything that is neither a letter, a digit, nor a hyphen is dropped. CJK
    characters are letters and survive, which is why the Chinese README's
    anchors are checkable at all.
    """
    heading = re.sub(r"`([^`]*)`", r"\1", heading)
    heading = re.sub(r"\*{1,2}([^*]*)\*{1,2}", r"\1", heading)
    heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    return "".join(
        "-" if char in " \t" else char
        for char in heading.lower()
        if char in " \t-" or char.isalnum()
    )


def _broken_page_anchors(path: Path) -> list[str]:
    text = read_text(path)
    anchors = {_anchor_slug(m.group(1)) for m in RE_HEADING.finditer(text)}
    broken = []
    for match in RE_PAGE_ANCHOR.finditer(text):
        if match.group(1) not in anchors:
            line = text[: match.start()].count("\n") + 1
            broken.append(f"{path.relative_to(REPO).as_posix()}:{line} "
                          f"#{match.group(1)}")
    return broken


RE_SECTION_REF = re.compile(r"\[\s*§\s*(\d+)(?:\.\w+)?\s*\]\(([^)\s#]+\.md)")


def _broken_section_references(path: Path) -> list[str]:
    """Cross-file `[§N](other.md)` links whose target has no section N.

    The file link resolves and the anchor check passes -- there is no
    `#fragment` -- so both existing checks are silent when a numbered section
    moves to a different page. Splitting §17 out of narrative-salience-register
    stranded both READMEs' §17 links exactly that way.
    """
    text = read_text(path)
    broken = []
    for match in RE_SECTION_REF.finditer(text):
        number, target = match.group(1), match.group(2)
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            continue            # the file-link check owns a missing target
        body = read_text(resolved)
        if (re.search(rf"(?m)^#{{1,6}}\s+{number}[.\s]", body)
                or re.search(rf"(?m)^\|\s*\*\*{number}\*\*\s*\|", body)):
            continue
        line = text[: match.start()].count("\n") + 1
        broken.append(f"{path.relative_to(REPO).as_posix()}:{line} "
                      f"§{number} -> {target}")
    return broken


RETIRED_SKILLS = ("modern-physics-review", "现代物理 review")
RE_SKILL_REF = re.compile(
    r"/sci-paper:([a-z][a-z0-9-]*)|skills/([a-z][a-z0-9-]*)/SKILL\.md")


def _unshipped_skill_references(path: Path, shipped: set[str]) -> list[str]:
    """Prose naming a skill this repository does not ship.

    `check_skills` verifies every shipped skill is registered. Nothing verified
    the other direction, so retiring `modern-physics-review` in v0.34.0 left
    both READMEs' fifth demo and DEAI_SUBSYSTEM §8 describing a review pass that
    no longer exists. Retired names are listed rather than inferred: prose calls
    it "the modern-physics reviewer", which no form-based rule can catch.
    """
    text = read_text(path)
    found = []
    for match in RE_SKILL_REF.finditer(text):
        name = match.group(1) or match.group(2)
        if name not in shipped:
            line = text[: match.start()].count("\n") + 1
            found.append(f"{path.relative_to(REPO).as_posix()}:{line} {name}")
    for retired in RETIRED_SKILLS:
        index = text.find(retired)
        if index >= 0:
            line = text[:index].count("\n") + 1
            found.append(f"{path.relative_to(REPO).as_posix()}:{line} "
                         f"retired name {retired!r}")
    return found


RE_NUMBERED_HEADING = re.compile(r"(?m)^#{2,3}\s+(\d+)(?:\.(\d+))?\.?\s")


def _sections_out_of_order(path: Path) -> list[str]:
    """A numbered heading that sits before a lower-numbered one.

    Section numbers are global across the evaluation record, so their order is
    part of the contract and nothing checked it. §21 was anchored on the
    paragraph that closes §17.4 -- not the end of that file -- so the document
    read 17.1-17.4, 21, 17.5, 17.6 with every other check green.
    """
    text = read_text(path)
    seen = []
    for match in RE_NUMBERED_HEADING.finditer(text):
        minor = int(match.group(2)) if match.group(2) else 0
        seen.append((int(match.group(1)) + minor / 100,
                     text[: match.start()].count("\n") + 1,
                     match.group(0).strip()))
    return [f"{path.relative_to(REPO).as_posix()}:{line} '{title}' follows "
            f"'{prior}'"
            for (value, line, title), (previous, _, prior) in zip(seen[1:], seen)
            if value < previous]


def check_documentation_boundaries() -> str:
    # v0.21.0 made docs/EVALUATION.md the single canonical evaluation record;
    # v0.27.0 categorized docs/ and moved it under architecture/. A copy left
    # at any former location is the stub-plus-canonical accumulation pattern
    # both moves eliminated.
    evaluation = read_text(REPO / EVALUATION_DOC)
    require("(../SCIPAPER_STANDARD.md)" in evaluation,
            f"{EVALUATION_DOC} must link the normative standard by path "
            "(../SCIPAPER_STANDARD.md) — a bare name mention is not enough")
    require(SCHEMA in evaluation,
            f"{EVALUATION_DOC} must identify the {SCHEMA} contract")

    for stale in FORBIDDEN_DOC_COPIES:
        require(not (REPO / stale).exists(),
                f"{stale} exists; the canonical documents are {STANDARD_DOC}, "
                f"{SUBSYSTEM_DOC}, {EVALUATION_DOC} and docs/design-notes/ — "
                "remove the stale copy")

    # Every shipped document must be reachable from the index, so a new doc
    # cannot land in the tree as an orphan nothing links to.
    index = read_text(REPO / DOCS_INDEX)
    shipped = sorted(
        path.relative_to(DOCS).as_posix()
        for path in DOCS.rglob("*.md")
        if path.name != "README.md"
    )
    missing = [name for name in shipped if f"]({name})" not in index]
    require(not missing,
            f"{DOCS_INDEX} does not link: {', '.join(missing)}")
    for note in DESIGN_NOTES:
        header = "\n".join(read_text(REPO / note).splitlines()[:4])
        require("design note" in header.lower(),
                f"{note} lives under design-notes/ but its header does not "
                "declare it a design note; a frozen note must not read as "
                "current status")
    # File links were checked; in-page #fragments were not, so the README
    # restructure left five cross-references pointing at headings that had been
    # renamed or renumbered — including "demo 3" linking to demo 4.
    pages = [REPO / "README.md", REPO / "README.zh-CN.md",
             *sorted(DOCS.rglob("*.md"))]
    broken = [item for page in pages for item in _broken_page_anchors(page)]
    require(not broken,
            "in-page anchors point at headings that do not exist: "
            + "; ".join(broken))
    stranded = [item for page in pages
                for item in _broken_section_references(page)]
    require(not stranded,
            "numbered cross-references point at pages that do not carry that "
            "section: " + "; ".join(stranded))
    skills = {path.parent.name for path in (REPO / "skills").glob("*/SKILL.md")}
    ghosts = [item for page in pages
              for item in _unshipped_skill_references(page, skills)]
    require(not ghosts,
            "documentation names a skill this repository does not ship: "
            + "; ".join(ghosts))
    disordered = [item for page in pages for item in _sections_out_of_order(page)]
    require(not disordered,
            "numbered headings run backwards: " + "; ".join(disordered))
    refs = sum(len(RE_SECTION_REF.findall(read_text(page))) for page in pages)
    return (f"documentation boundaries are unambiguous "
            f"({len(shipped)} documents, all indexed; "
            f"{len(pages)} pages anchor-checked; "
            f"{refs} numbered cross-references resolved; "
            f"{len(skills)} skills named only where shipped; heading order clean)")


def _discovered_test_count() -> tuple[int, int]:
    """(test count, test-file count) from real unittest discovery."""
    import unittest
    suite = unittest.defaultTestLoader.discover(str(TESTS), top_level_dir=str(TESTS))

    def count(item) -> int:
        if isinstance(item, unittest.TestSuite):
            return sum(count(child) for child in item)
        require(item.__class__.__name__ != "_FailedTest",
                f"a test module failed to import: {item}")
        return 1

    return count(suite), len(list(TESTS.glob("test_*.py")))


TEST_COUNT_RE = re.compile(r"(\d[\d,]*) unit/CLI tests? \((\d+) test files?")
SUITE_COUNT_RE = re.compile(r"\((\d[\d,]*) tests?, (\d+) files?\)")
# The latency table spells the same measurement a third way, in both languages.
# It sat at 360/19 against a 381-test suite because this check only ever read
# the evidence record -- a recorded count outside docs/ was nobody's job.
LATENCY_COUNT_RE = re.compile(
    r"\*\*(\d[\d,]*) (?:passing|通过)\*\*[,，] ?(\d+) (?:files?|个文件)")


def check_recorded_test_counts() -> str:
    """Every recorded suite size must match the suite that actually exists.

    docs/architecture/EVALUATION.md quoted two different sizes for the same
    release (147/13 in section 3, 172/14 in section 12) because nothing
    compared either figure with the repository. A count is a measurement, so
    it is validated like one.
    """
    tests, files = _discovered_test_count()
    # Scan the WHOLE evidence record. Before the record was split, checking the
    # single EVALUATION.md was the same thing; afterwards it was not, and a
    # stale count in a part file would have gone unchecked -- the precise
    # failure mode this function exists to prevent.
    documents = [REPO / EVALUATION_DOC]
    documents.extend(sorted((REPO / EVALUATION_PARTS_DIR).glob("*.md")))
    # Both READMEs publish the suite size in their latency table. That is a
    # recorded measurement wherever it is written, so it is checked wherever it
    # is written -- scanning only docs/ is what let 360/19 survive to 381/19.
    documents.extend(REPO / name for name in ("README.md", "README.zh-CN.md"))
    claims: list[tuple[tuple[int, int], str]] = []
    for path in documents:
        if not path.is_file():
            continue
        name = path.relative_to(REPO).as_posix()
        text = read_text(path)
        for pattern in (TEST_COUNT_RE, SUITE_COUNT_RE, LATENCY_COUNT_RE):
            for claimed_tests, claimed_files in pattern.findall(text):
                claims.append(((int(claimed_tests.replace(",", "")),
                                int(claimed_files)), name))
    require(claims,
            f"the evaluation record ({EVALUATION_DOC} and "
            f"{EVALUATION_PARTS_DIR}/) records no suite size to verify")
    wrong = sorted({(claim, name) for claim, name in claims
                    if claim != (tests, files)})
    require(not wrong,
            "recorded suite size(s) "
            + ", ".join(f"{claim} in {name}" for claim, name in wrong)
            + f" but discovery finds ({tests}, {files})")
    return (f"recorded suite size matches discovery ({tests} tests, {files} files; "
            f"{len(claims)} claim(s) across {len(documents)} document(s))")


def product_tool_files() -> set[str]:
    scripts = {path.name for path in TOOLS.glob("*.py") if path.name != "validate_plugin.py"}
    data_assets = {path.name for path in TOOLS.glob("*.txt")}
    return scripts | data_assets


def parse_declared_count(text: str, heading: str) -> int:
    # Any heading level: the contract is the declared count, not how deep the
    # README nests its registry sections.
    match = re.search(rf"^#{{2,4}} {re.escape(heading)} \((\d+)\)\s*$", text, re.MULTILINE)
    require(match is not None, f"README missing '{heading} (N)' heading")
    return int(match.group(1))


HEADLINE_EN_RE = re.compile(r"\*\*(\d+) skills · (\d+) tools · (\d+) tests")
HEADLINE_ZH_RE = re.compile(r"\*\*(\d+) 个 skill · (\d+) 个工具 · (\d+) 个测试")

# Every way the two READMEs spell a repository-shape number, paired with the
# quantity it claims. One regex per spelling was tried and failed four times --
# the headline, the ASCII tree and the release paragraph each drifted on their
# own, and the translation drifted furthest because nothing read it at all. The
# rule is now the table: a shape number is checked wherever it is written.
SHAPE_CLAIMS = (
    (re.compile(r"(\d+) skills\b"), ("skills",)),
    (re.compile(r"(\d+) product tools\b"), ("tools",)),
    (re.compile(r"(\d+) files, (\d+) tests\b"), ("files", "tests")),
    (re.compile(r"(\d+) contract checks\b"), ("checks",)),
    (re.compile(r"the (\d+)-test suite"), ("tests",)),
    (re.compile(r"(\d+) 个 skill\b"), ("skills",)),
    (re.compile(r"(\d+) 个产品工具"), ("tools",)),
    (re.compile(r"(\d+) 个测试文件、(\d+) 个测试"), ("files", "tests")),
    (re.compile(r"(\d+) 项契约检查"), ("checks",)),
    (re.compile(r"跑 (\d+) 个测试"), ("tests",)),
)


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

    # Both READMEs open with the same three counts. Only README.md's section
    # headings were ever checked, so the translated headline drifted to 9 skills
    # against a 12-skill repository and nothing said so.
    tests, files = _discovered_test_count()
    truth = (len(documents), len(products), tests)
    for name, pattern in (
        ("README.md", HEADLINE_EN_RE),
        ("README.zh-CN.md", HEADLINE_ZH_RE),
    ):
        found = pattern.search(read_text(REPO / name))
        require(found is not None, f"{name} has no headline skills/tools/tests line")
        claimed = tuple(int(value) for value in found.groups())
        require(claimed == truth,
                f"{name} headline states {claimed} (skills, tools, tests) "
                f"but repository has {truth}")

    facts = {"skills": len(documents), "tools": len(products),
             "tests": tests, "files": files, "checks": len(CHECKS)}
    wrong, seen = [], 0
    for name in ("README.md", "README.zh-CN.md"):
        text = read_text(REPO / name)
        for pattern, keys in SHAPE_CLAIMS:
            for groups in pattern.findall(text):
                values = (groups,) if isinstance(groups, str) else groups
                seen += 1
                for value, key in zip(values, keys):
                    if int(value) != facts[key]:
                        wrong.append(f"{name} says {value} {key} (repository has {facts[key]})")
    require(not wrong, "; ".join(sorted(set(wrong))))
    return (f"README and manifest registries agree ({len(documents)} skills, "
            f"{len(products)} tools; {seen} shape claim(s) verified in both READMEs)")


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


# Module level so the count is readable: the READMEs publish "9 contract checks"
# and check_registry_counts verifies that claim against this tuple.
CHECKS = (
    check_manifests,
    check_skills,
    check_documentation_boundaries,
    check_recorded_test_counts,
    check_registry_counts,
    check_tools_syntax,
    check_runtime_contract,
    check_linter_exit_semantics,
    check_tests_and_ci,
)


def main() -> int:
    # Failure messages quote document text containing en/em dashes; a redirected
    # stdout under a non-UTF-8 locale would turn a readable contract violation
    # into a UnicodeEncodeError traceback.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        for check in CHECKS:
            print(f"  [ok] {check()}")
    except ValidationError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("validate_plugin: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
