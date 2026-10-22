#!/usr/bin/env python3
"""Audit Jarvis Box capability coverage, skill depth, and package safety."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


CATEGORIES = {
    "build",
    "runtime",
    "lifecycle",
    "config",
    "concurrency",
    "security",
    "diagnostics",
    "compatibility",
    "agent-tools",
    "repo-specific",
}
CATEGORY_STATUS = {"covered", "not-applicable"}
SURFACE_STATUS = {"present", "not-present", "not-authorized"}
DISPOSITIONS = {
    "router",
    "capability-skill",
    "focused-loop",
    "cross-cutting-skill",
    "reference",
    "script-gate",
    "agent-tool",
    "no-skill",
    "candidate",
}
DELIVERED_SKILLS = {
    "router",
    "capability-skill",
    "focused-loop",
    "cross-cutting-skill",
}
DELIVERED_TOOLS = {"agent-tool"}
LEVELS = {"L0", "L1", "L2", "L3"}
EVAL_STATUS = {"executed-pass", "executed-fail", "prepared-not-executed"}
CONTROL_PREFIX = ("executed-pass:", "executed-fail:", "observed-not-executed:")
DIMENSIONS = {
    "implementation_anchors",
    "mechanical_controls",
    "risk_promotion",
    "runtime_hidden_forward_eval",
    "cross_repository_closure",
    "drift_self_improve",
}
CAPABILITY_TEXT = {
    "task_family",
    "state_or_resource_model",
    "merge_split_rationale",
    "current_state",
}
CAPABILITY_LISTS = {
    "trigger_examples",
    "authority",
    "entrypoints",
    "proof",
    "evidence",
}
PRODUCT_SKILLS = {
    "jarvis-box",
    "jarvis-box-init",
    "jarvis-box-doctor",
    "jarvis-box-monitor",
}
TOOL_DIRS = {"bin", "cmd", "scripts", "tools"}
TOOL_FILES = {
    "GNUmakefile",
    "Justfile",
    "Makefile",
    "Taskfile.yaml",
    "Taskfile.yml",
    "justfile",
    "makefile",
    "package.json",
    "pyproject.toml",
}


def read_json(path: Path, problems: list[str], label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        problems.append(f"{label} unreadable: {exc}")
        return {}
    if not isinstance(value, dict):
        problems.append(f"{label} must be a JSON object")
        return {}
    return value


def relative_existing(
    base: Path,
    raw: str,
    repo: Path,
    problems: list[str],
    label: str,
) -> Path | None:
    text = str(raw).split("#", 1)[0]
    candidate = Path(text)
    if candidate.is_absolute():
        problems.append(f"{label} must be repository-relative: {raw}")
        return None
    resolved = (base / candidate).resolve()
    try:
        resolved.relative_to(repo.resolve())
    except ValueError:
        problems.append(f"{label} escapes repository root: {raw}")
        return None
    if not resolved.exists():
        problems.append(f"{label} path missing: {raw}")
        return None
    return resolved


def risk_level(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("level", "")).strip().lower()
    return str(value).split(":", 1)[0].strip().lower()


def validate_frontmatter(path: Path, expected_name: str, problems: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        problems.append(f"skill {expected_name} lacks YAML frontmatter")
        return
    end = text.find("\n---\n", 4)
    if end < 0:
        problems.append(f"skill {expected_name} has unclosed YAML frontmatter")
        return
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    if fields.get("name") != expected_name:
        problems.append(f"skill {expected_name} frontmatter name does not match folder")
    description = fields.get("description", "")
    if not description:
        problems.append(f"skill {expected_name} lacks description")
    if "REPLACE_WITH_" in text or "[TODO" in text:
        problems.append(f"skill {expected_name} contains unfinished placeholders")


def validate_openai_yaml(path: Path, name: str, problems: list[str]) -> None:
    if not path.is_file():
        problems.append(f"skill {name} lacks agents/openai.yaml")
        return
    text = path.read_text(encoding="utf-8")
    if "interface:" not in text or "display_name:" not in text or "short_description:" not in text:
        problems.append(f"skill {name} openai.yaml lacks required interface metadata")
    if f"${name}" not in text:
        problems.append(f"skill {name} openai.yaml default prompt must mention ${name}")


def validate_product_installer(repo: Path, problems: list[str]) -> None:
    installer = repo / "install-skills.py"
    try:
        tree = ast.parse(installer.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        problems.append(f"install-skills.py unreadable: {exc}")
        return
    values = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "SKILLS" for target in node.targets
        ):
            try:
                values = set(ast.literal_eval(node.value))
            except (ValueError, TypeError):
                pass
            break
    if values != PRODUCT_SKILLS:
        problems.append(
            "install-skills.py product package list must be exactly: "
            + ", ".join(sorted(PRODUCT_SKILLS))
        )


def validate_manifest(repo: Path, problems: list[str]) -> None:
    manifest = repo / ".jarvis-box-managed-files"
    try:
        entries = [
            line.strip()
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except OSError as exc:
        problems.append(f"managed-file manifest unreadable: {exc}")
        return
    if len(entries) != len(set(entries)):
        problems.append("managed-file manifest contains duplicate paths")
    required = {
        path.relative_to(repo).as_posix()
        for root in (repo / "docs", repo / "skills")
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }
    required.add("install-skills.py")
    missing = sorted(required - set(entries))
    if missing:
        problems.append("managed-file manifest omits current overlay files: " + ", ".join(missing))


def validate_skill_links(repo: Path, problems: list[str]) -> None:
    for markdown in (repo / "skills").rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        for raw in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
            target = raw.split("#", 1)[0].strip()
            if not target or "://" in target or target.startswith(("#", "mailto:")):
                continue
            resolved = (markdown.parent / target).resolve()
            try:
                resolved.relative_to(repo.resolve())
            except ValueError:
                problems.append(f"{markdown}: link escapes repository: {raw}")
                continue
            if not resolved.exists():
                problems.append(f"{markdown}: link target missing: {raw}")


def audit(repo: Path, router_name: str) -> list[str]:
    problems: list[str] = []
    repo = repo.resolve()
    router = repo / "skills" / router_name
    contract = read_json(
        router / "references" / "skill-depth.json",
        problems,
        "skill depth contract",
    )
    if not contract:
        return problems

    if set(contract.get("dimensions", {})) != DIMENSIONS:
        problems.append("skill-depth.json must declare exactly the six dimensions")
    coverage_path = relative_existing(
        router,
        contract.get("coverage_file", ""),
        repo,
        problems,
        "coverage file",
    )
    evals_path = relative_existing(
        router,
        contract.get("evals_file", ""),
        repo,
        problems,
        "evals file",
    )
    coverage = read_json(coverage_path, problems, "capability coverage") if coverage_path else {}
    eval_payload = read_json(evals_path, problems, "eval suite") if evals_path else {}

    if coverage.get("schema_version") != 2:
        problems.append("capability coverage must use schema_version 2")
    if not str(coverage.get("repository", "")).strip():
        problems.append("capability coverage lacks repository identity")
    fixed = str(coverage.get("fixed_revision", ""))
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", fixed):
        problems.append("capability coverage fixed_revision must be a full commit")
    if "REPLACE_WITH_" in json.dumps(coverage, ensure_ascii=False):
        problems.append("capability coverage contains template placeholders")

    evals: dict[str, dict] = {}
    rows = eval_payload.get("evals", [])
    if not isinstance(rows, list):
        problems.append("eval suite evals must be a list")
        rows = []
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("id", "")).strip():
            problems.append("every eval must have an id")
            continue
        eval_id = str(row["id"])
        if eval_id in evals:
            problems.append(f"duplicate eval id: {eval_id}")
        evals[eval_id] = row
        if row.get("status") not in EVAL_STATUS:
            problems.append(f"eval {eval_id} has invalid status")

    category_rows: dict[str, dict] = {}
    for row in coverage.get("categories", []):
        name = str(row.get("name", ""))
        status = str(row.get("status", ""))
        if name in category_rows:
            problems.append(f"duplicate category: {name}")
        category_rows[name] = row
        if name not in CATEGORIES:
            problems.append(f"unknown category: {name}")
        if status not in CATEGORY_STATUS:
            problems.append(f"category {name} has invalid status")
        if not any(str(item).strip() for item in row.get("evidence", [])):
            problems.append(f"category {name} lacks evidence")
        for field in ("surface_ids", "capability_ids"):
            values = row.get(field)
            if not isinstance(values, list):
                problems.append(f"category {name} {field} must be a list")
            elif status == "covered" and not values:
                problems.append(f"covered category {name} has no {field}")
            elif status == "not-applicable" and values:
                problems.append(f"not-applicable category {name} must not list {field}")
    missing = CATEGORIES - set(category_rows)
    if missing:
        problems.append("missing categories: " + ", ".join(sorted(missing)))

    skills: dict[str, dict] = {}
    for record in contract.get("skills", []):
        name = str(record.get("name", "")).strip()
        if not name:
            problems.append("skill inventory record lacks name")
            continue
        if name in skills:
            problems.append(f"duplicate skill inventory record: {name}")
        skills[name] = record
        if record.get("level") not in LEVELS:
            problems.append(f"skill {name} has invalid level")
        for authority in record.get("authority", []):
            relative_existing(repo, authority, repo, problems, f"skill {name} authority")
        controls = record.get("mechanical_controls", [])
        if not isinstance(controls, list) or not controls:
            problems.append(f"skill {name} has no mechanical controls")
        else:
            for control in controls:
                if not str(control).startswith(CONTROL_PREFIX):
                    problems.append(f"skill {name} control lacks execution status")
        forward_ids = record.get("forward_eval_ids", [])
        if not isinstance(forward_ids, list):
            problems.append(f"skill {name} forward_eval_ids must be a list")
            forward_ids = []
        for eval_id in forward_ids:
            if eval_id not in evals:
                problems.append(f"skill {name} references unknown eval {eval_id}")
        if risk_level(record.get("risk")) in {"high", "critical"}:
            if record.get("level") not in {"L2", "L3"}:
                problems.append(f"high-risk skill {name} must be L2/L3")
            if not any(str(item).startswith("executed-pass:") for item in controls):
                problems.append(f"high-risk skill {name} lacks executed-pass control")
            if record.get("level") == "L3" and not any(
                evals.get(eval_id, {}).get("status") == "executed-pass"
                for eval_id in forward_ids
            ):
                problems.append(f"L3 skill {name} lacks an executed-pass hidden eval")

    actual_packages = {
        path.parent.name for path in (repo / "skills").glob("*/SKILL.md") if path.is_file()
    }
    if set(skills) != actual_packages:
        problems.append(
            "skill inventory mismatch: expected="
            + repr(sorted(actual_packages))
            + " recorded="
            + repr(sorted(skills))
        )
    if router_name not in skills:
        problems.append(f"router missing from inventory: {router_name}")
    validate_product_installer(repo, problems)
    validate_manifest(repo, problems)
    validate_skill_links(repo, problems)
    if actual_packages - PRODUCT_SKILLS != {"jarvis-box-release-maintainer"}:
        problems.append("unexpected non-product skill package")

    capabilities: dict[str, dict] = {}
    delivered_primary_homes: set[str] = set()
    for row in coverage.get("capabilities", []):
        cap_id = str(row.get("id", "")).strip()
        if not cap_id or cap_id in capabilities:
            problems.append(f"invalid or duplicate capability id: {cap_id or '<missing>'}")
            continue
        capabilities[cap_id] = row
        category = str(row.get("category", ""))
        disposition = str(row.get("disposition", ""))
        primary_home = str(row.get("primary_home", ""))
        if category not in CATEGORIES:
            problems.append(f"capability {cap_id} has invalid category")
        if disposition not in DISPOSITIONS:
            problems.append(f"capability {cap_id} has invalid disposition")
        for field in CAPABILITY_TEXT:
            if not str(row.get(field, "")).strip():
                problems.append(f"capability {cap_id} lacks {field}")
        for field in CAPABILITY_LISTS:
            if not isinstance(row.get(field), list) or not any(
                str(item).strip() for item in row.get(field, [])
            ):
                problems.append(f"capability {cap_id} lacks {field}")
        for authority in row.get("authority", []):
            relative_existing(repo, authority, repo, problems, f"capability {cap_id} authority")
        route_ids = row.get("route_eval_ids", [])
        if not isinstance(route_ids, list):
            problems.append(f"capability {cap_id} route_eval_ids must be a list")
            route_ids = []
        for eval_id in route_ids:
            if eval_id not in evals:
                problems.append(f"capability {cap_id} references unknown eval {eval_id}")
        if disposition in DELIVERED_SKILLS:
            if primary_home not in skills:
                problems.append(f"capability {cap_id} has unknown primary_home")
            else:
                delivered_primary_homes.add(primary_home)
            if not any(evals.get(eval_id, {}).get("status") == "executed-pass" for eval_id in route_ids):
                problems.append(f"delivered capability {cap_id} lacks executed-pass route eval")
        elif disposition in DELIVERED_TOOLS:
            tool_path = relative_existing(
                repo,
                primary_home,
                repo,
                problems,
                f"capability {cap_id} primary_home",
            )
            if tool_path:
                parts = tool_path.resolve().relative_to(repo).parts
                if not (len(parts) == 1 and parts[0] in TOOL_FILES) and not (
                    parts and parts[0] in TOOL_DIRS
                ):
                    problems.append(f"capability {cap_id} is not an agent-tool home")
            if not any(evals.get(eval_id, {}).get("status") == "executed-pass" for eval_id in route_ids):
                problems.append(f"agent-tool {cap_id} lacks executed-pass route eval")
        elif disposition == "reference":
            if not primary_home:
                problems.append(f"reference capability {cap_id} lacks primary_home")
            else:
                relative_existing(repo, primary_home, repo, problems, f"capability {cap_id} primary_home")
        elif not str(row.get("reason", "")).strip():
            problems.append(f"capability {cap_id} disposition requires reason")

    unowned_packages = actual_packages - {router_name} - delivered_primary_homes
    if unowned_packages:
        problems.append("delivered packages lack capability primary homes: " + ", ".join(sorted(unowned_packages)))

    surfaces: dict[str, dict] = {}
    for row in coverage.get("surface_inventory", []):
        surface_id = str(row.get("id", "")).strip()
        if not surface_id or surface_id in surfaces:
            problems.append(f"invalid or duplicate surface id: {surface_id or '<missing>'}")
            continue
        surfaces[surface_id] = row
        category = str(row.get("category", ""))
        status = str(row.get("status", ""))
        if category not in CATEGORIES:
            problems.append(f"surface {surface_id} has invalid category")
        if status not in SURFACE_STATUS:
            problems.append(f"surface {surface_id} has invalid status")
        if not str(row.get("name", "")).strip():
            problems.append(f"surface {surface_id} lacks name")
        for field in ("entrypoints", "evidence"):
            if not isinstance(row.get(field), list) or not any(
                str(item).strip() for item in row.get(field, [])
            ):
                problems.append(f"surface {surface_id} lacks {field}")
        cap_ids = row.get("capability_ids")
        if not isinstance(cap_ids, list):
            problems.append(f"surface {surface_id} capability_ids must be a list")
            cap_ids = []
        if status == "present" and not cap_ids:
            problems.append(f"present surface {surface_id} lacks capability_ids")
        for cap_id in cap_ids:
            capability = capabilities.get(str(cap_id))
            if not capability:
                problems.append(f"surface {surface_id} references unknown capability {cap_id}")
            elif capability.get("category") != category:
                problems.append(f"surface {surface_id} category differs from capability {cap_id}")

    referenced_surfaces: set[str] = set()
    referenced_capabilities: set[str] = set()
    for category, row in category_rows.items():
        for surface_id in row.get("surface_ids", []):
            referenced_surfaces.add(str(surface_id))
            if surface_id not in surfaces:
                problems.append(f"category {category} references unknown surface {surface_id}")
            elif surfaces[str(surface_id)].get("category") != category:
                problems.append(f"category {category} owns mismatched surface {surface_id}")
        for cap_id in row.get("capability_ids", []):
            referenced_capabilities.add(str(cap_id))
            if cap_id not in capabilities:
                problems.append(f"category {category} references unknown capability {cap_id}")
            elif capabilities[str(cap_id)].get("category") != category:
                problems.append(f"category {category} owns mismatched capability {cap_id}")
    if set(surfaces) != referenced_surfaces:
        problems.append("surface inventory does not match category ownership")
    if set(capabilities) != referenced_capabilities:
        problems.append("capability inventory does not match category ownership")
    surface_capabilities = {
        str(cap_id) for row in surfaces.values() for cap_id in row.get("capability_ids", [])
    }
    if set(capabilities) - surface_capabilities:
        problems.append("capabilities lack surface ownership")

    for package in sorted(actual_packages):
        skill_path = repo / "skills" / package / "SKILL.md"
        validate_frontmatter(skill_path, package, problems)
        validate_openai_yaml(repo / "skills" / package / "agents" / "openai.yaml", package, problems)
        text = skill_path.read_text(encoding="utf-8")
        for marker in ("skill-depth", "evals/evals.json", "audit_skill_depth.py"):
            if marker not in text:
                problems.append(f"skill {package} does not link {marker}")
    router_text = (router / "SKILL.md").read_text(encoding="utf-8")
    for package in actual_packages - {router_name}:
        if package not in router_text:
            problems.append(f"router does not name package {package}")

    depth_doc = router / "references" / "skill-depth.md"
    if not depth_doc.is_file():
        problems.append("router depth document missing")
    else:
        for link in re.findall(r"\[[^]]+\]\(([^)]+)\)", depth_doc.read_text(encoding="utf-8")):
            if "://" not in link and not link.startswith("#"):
                relative_existing(depth_doc.parent, link, repo, problems, "depth document link")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--router", required=True)
    args = parser.parse_args()
    problems = audit(args.repo, args.router)
    print(json.dumps({"status": "failed" if problems else "ok", "problems": problems}, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
