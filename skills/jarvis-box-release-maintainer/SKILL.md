---
name: jarvis-box-release-maintainer
description: Maintain the public hengshi/jarvis-box documentation, release-note, and customer-skill overlay. Use when editing this repository, syncing a release overlay, reviewing a docs PR, or deciding whether a requested Jarvis Box change belongs in the private product source.
---

# Jarvis Box public overlay maintenance

Keep this repository a verified customer-facing overlay. It owns release notes, customer documentation, the four-entry product skill package, and the ownership manifest; it does not own private implementation.

## Establish the mutation boundary

1. Read `CONTRIBUTING.md`, `REPOSITORY-MODEL.md`, `.jarvis-box-managed-files`, and [release compatibility](../jarvis-box/references/release-contract.md).
2. Identify the source release/version and whether the task is documentation, customer skills, release notes, or implementation.
3. Continue here only for the public overlay surfaces. For source, test, binary, image-build, CI, or runtime behavior changes, preserve the request and route it to the canonical private source workflow. Do not create a public implementation fork or claim that a documentation edit changed runtime behavior.
4. Record the fixed public commit and use a dedicated branch. Preserve unrelated working-tree changes and the repository history.

## Apply an overlay change

- Update the customer-facing authority first: release notes belong in `CHANGELOG.md`; customer procedures belong in the matching `CUSTOMER-OPERATIONS.md` and `docs/` owner; product skill changes belong under `skills/`.
- Keep one primary home. Do not duplicate configuration tables across `README.md`, integration docs, and skill references.
- Add or retire every publisher-owned path in `.jarvis-box-managed-files`. A file absent from that manifest can survive a release sync even after deletion from the canonical overlay.
- Keep the customer skill package at exactly `jarvis-box`, `jarvis-box-init`, `jarvis-box-doctor`, and `jarvis-box-monitor`; `install-skills.py` must continue to exclude repository-maintenance skills.
- Do not put private implementation details, customer names, credentials, private URLs, or raw sessions into public docs or evals.

## Prove the result

Run all checks from the repository root:

```bash
python3 -m py_compile install-skills.py
python3 skills/jarvis-box/scripts/audit_skill_depth.py --repo . --router jarvis-box
git diff --check
```

For product-skill changes, also install into an owned temporary Agent-root fixture and compare:

```bash
fixture="$(mktemp -d)"
mkdir -p "$fixture/skills"
python3 install-skills.py --skills-root "$fixture/skills"
python3 install-skills.py --skills-root "$fixture/skills" --check
rm -rf "$fixture"
```

Use `rm -rf` only on the exact temporary fixture after verifying it is non-empty and under the platform temporary directory. Inspect the diff for stale versions, failed links, and accidental private-source material. Record checks that were not executed.

## Delivery

Commit the overlay and evidence-backed skill changes on the assigned branch. Create a PR describing the customer-visible surface, version applicability, checks, and any unverified release fact. Do not merge a protected branch or publish a Release.

Depth and verification pointers: [skill-depth](../jarvis-box/references/skill-depth.md), [evals](../jarvis-box/evals/evals.json), and `skills/jarvis-box/scripts/audit_skill_depth.py`.
