"""Install only Jarvis Box customer skills into explicit existing Agent roots."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import sys
import tempfile


SKILLS = ("jarvis-box", "jarvis-box-init", "jarvis-box-doctor", "jarvis-box-monitor")
SOURCE = Path(__file__).resolve().parent / "skills"


def tree(path: Path) -> dict[str, str]:
    """Validate a regular tree and compare contents without persisting a ledger."""
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"skill must be a real directory: {path}")
    result = {}
    for entry in sorted(path.rglob("*")):
        mode = entry.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f"skill contains a symlink or special file: {entry}")
        result[str(entry.relative_to(path))] = hashlib.sha256(entry.read_bytes()).hexdigest()
    if "SKILL.md" not in result:
        raise ValueError(f"skill lacks SKILL.md: {path}")
    return result


def discovery_root(candidate: Path) -> Path:
    if not candidate.is_absolute():
        raise ValueError(f"skills root must be absolute: {candidate}")
    if candidate.is_symlink():
        raise ValueError(f"skills root must not be a symlink: {candidate}")
    if not candidate.is_dir() or candidate.stat().st_uid != os.getuid():
        raise ValueError(f"skills root must exist and belong to the current user: {candidate}")
    candidate = candidate.resolve()
    if candidate == Path(candidate.anchor) or candidate == Path.home().resolve():
        raise ValueError(f"select an Agent discovery directory, not a filesystem/HOME root: {candidate}")
    if candidate == SOURCE or candidate in SOURCE.parents or SOURCE in candidate.parents:
        raise ValueError("source and destination must be separate directories")
    return candidate


def validate_destination(root: Path) -> None:
    for name in SKILLS:
        destination = root / name
        if destination.is_symlink():
            raise ValueError(f"refusing a symlink destination: {destination}")
        if destination.exists():
            tree(destination)
            if destination.stat().st_uid != os.getuid():
                raise ValueError(f"skill belongs to a different user: {destination}")


def install(root: Path) -> None:
    # Lock the existing directory itself: no shared runtime state or lock file.
    descriptor = os.open(root, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        validate_destination(root)
        with tempfile.TemporaryDirectory(prefix=".jarvis-box-skills-", dir=root) as temporary:
            stage = Path(temporary)
            for name in SKILLS:
                shutil.copytree(SOURCE / name, stage / name)
            for name in SKILLS:
                destination = root / name
                previous = stage / (name + ".previous")
                if destination.exists():
                    destination.rename(previous)
                try:
                    (stage / name).rename(destination)
                except OSError:
                    if previous.exists():
                        previous.rename(destination)
                    raise
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", action="append", required=True,
                        help="verified existing Agent discovery root; repeat for each Agent")
    parser.add_argument("--check", action="store_true", help="compare installed contents without writing")
    args = parser.parse_args()
    stage = "validate-source-pack"
    path = SOURCE
    may_have_written = False
    next_check = f"ls -ld -- {shlex.quote(str(SOURCE))}"
    try:
        expected = {name: tree(SOURCE / name) for name in SKILLS}
        roots = {}
        stage = "validate-discovery-root"
        for value in args.skills_root:
            path = Path(value)
            next_check = "verify the requested home directory and locate the absolute Agent discovery directory"
            try:
                path = path.expanduser()
            except RuntimeError as error:
                raise ValueError("skills root names an unavailable home directory; use the absolute Agent discovery path") from error
            next_check = f"ls -ld -- {shlex.quote(str(path))}"
            roots[discovery_root(path)] = None
        # Reject an invalid later root before changing any earlier root.
        stage = "validate-destination-skills"
        for root in roots:
            path = root
            next_check = f"ls -la -- {shlex.quote(str(root))}"
            validate_destination(root)
        if args.check:
            stage = "compare-installed-skills"
            mismatches = []
            for root in roots:
                path = root
                next_check = f"ls -la -- {shlex.quote(str(root))}"
                for name in SKILLS:
                    destination = root / name
                    if not destination.is_dir() or tree(destination) != expected[name]:
                        mismatches.append(str(destination))
            print(json.dumps({"status": "different" if mismatches else "ok",
                              "different": mismatches}, ensure_ascii=False))
            return 1 if mismatches else 0
        stage = "install-skills"
        paths = " ".join(shlex.quote(str(root)) for root in roots)
        next_check = f"ls -la -- {paths}"
        for root in roots:
            path = root
            may_have_written = True
            install(root)
        print(json.dumps({"status": "installed", "skills": SKILLS,
                          "skills_roots": [str(root) for root in roots]}, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as error:
        state = "some requested skills may already have changed" if may_have_written else "no skills were changed"
        print(f"Jarvis Box skill installation failed at {stage} (path {str(path)!r}): {error}",
              file=sys.stderr)
        print(f"State: {state}.\nRead-only check: {next_check}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
