#!/usr/bin/env python3
"""Validate an engine-export bundle.

Run it before sending a bundle, and again on receipt. Standard library only --
it has to work in a studio's environment without installing anything.

    python3 validate_bundle.py <bundle_dir>

Exit 0 if no errors. Warnings never fail the run: they are advice, not gates.
See reference/01-export-spec.md for what each file must contain.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

errors: list[str] = []
warnings: list[str] = []
info: list[str] = []

REQUIRED_BY_TIER = {
    0: ["MANIFEST.json", "cards/cards.json", "NOTES.md"],
    1: ["rules/state-schema.json", "rules/actions.md", "cards/effects.md"],
    2: [],
}

NOTES_SECTIONS = [
    "known bugs",
    "intentional quirks",
    "unresolved",
    "bespoke",
    "out of scope",
    "not be able to reproduce",
]

SECRET_PATTERNS = [
    (r"\b(api[_-]?key|secret|passwd|password|bearer)\b\s*[:=]", "credential-shaped assignment"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
    (r"\bhttps?://(?!localhost|127\.0\.0\.1|example\.|schema|json-schema)", "external URL"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "email address"),
    (r"\b(?:[A-Za-z]:\\\\|/Users/|/home/)[A-Za-z0-9._-]+", "absolute path leaking a home directory"),
]


def load_json(path: Path, label: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{label}: file not found ({path})")
    except json.JSONDecodeError as e:
        errors.append(f"{label}: invalid JSON -- {e}")
    return None


def check_manifest(root: Path):
    m = load_json(root / "MANIFEST.json", "MANIFEST.json")
    if m is None:
        return None
    for key in ("game", "export", "contents", "randomness"):
        if key not in m:
            errors.append(f"MANIFEST.json: missing top-level '{key}'")
    tier = m.get("export", {}).get("tier")
    if tier not in (0, 1, 2):
        errors.append(f"MANIFEST.json: export.tier must be 0, 1 or 2 (got {tier!r})")
        tier = 0
    info.append(f"tier {tier}")

    rnd = m.get("randomness", {})
    if not rnd.get("all_random_sites_logged"):
        errors.append(
            "randomness.all_random_sites_logged is false -- replays cannot be ground truth. "
            "Note this does NOT require a seedable or single-source RNG, only logging what "
            "each random call returned (reference/03-determinism.md)"
        )
    for site in rnd.get("sites_missing_distribution", []) or []:
        warnings.append(
            f"random site without a declared distribution: {site} -- outcomes there replay, but the "
            "distribution is unverifiable, so generated games may be out of distribution"
        )
    if rnd.get("notes", "").strip() not in ("", "<any random decision NOT routed through the log>"):
        info.append(f"randomness notes: {rnd['notes']}")

    hashing = m.get("hashing", {})
    canon = str(hashing.get("canonicalization", ""))
    if (not canon or canon.startswith("<")) and any((root / "replays").glob("*.json")) \
            and _any_state_dumps(root):
        warnings.append(
            "hashing.canonicalization is unset while state_dumps are present -- a reimplementation "
            "in another language will mismatch every hash for the wrong reason"
        )
    return m, tier


def _any_state_dumps(root: Path) -> bool:
    for p in (root / "replays").glob("*.json"):
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("state_dumps"):
                return True
        except Exception:
            continue
    return False


def check_required_files(root: Path, tier: int):
    required = list(REQUIRED_BY_TIER[0])
    if tier >= 1:
        required += REQUIRED_BY_TIER[1]
    for rel in required:
        if not (root / rel).exists():
            errors.append(f"missing required file for tier {tier}: {rel}")
    if not (root / "replays").is_dir():
        errors.append("missing required directory: replays/")


def check_checksums(root: Path, manifest: dict):
    listed = manifest.get("files") or []
    checked = skipped = 0
    for entry in listed:
        rel, want = entry.get("path"), entry.get("sha256", "")
        if not rel or not want or want.startswith("<"):
            skipped += 1
            continue
        p = root / rel
        if not p.exists():
            errors.append(f"MANIFEST lists a file that does not exist: {rel}")
            continue
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != want:
            errors.append(f"checksum mismatch for {rel}\n    manifest: {want}\n    actual:   {got}")
        checked += 1
    if skipped:
        warnings.append(f"{skipped} MANIFEST file entries have no real checksum (placeholders left in?)")
    if checked:
        info.append(f"{checked} checksums verified")


def check_cards(root: Path, manifest: dict):
    data = load_json(root / "cards" / "cards.json", "cards/cards.json")
    if data is None:
        return set()
    cards = data.get("cards")
    if not isinstance(cards, list):
        errors.append("cards.json: 'cards' must be an array")
        return set()

    glossary = set(data.get("keyword_glossary") or {})
    ids: set[str] = set()
    bespoke = composed = keyword_only = 0

    for i, c in enumerate(cards):
        where = f"cards[{i}]" + (f" ({c.get('id')})" if isinstance(c, dict) else "")
        if not isinstance(c, dict):
            errors.append(f"{where}: not an object")
            continue
        for field in ("id", "name", "cost", "type", "effect_text_exact"):
            if field not in c:
                errors.append(f"{where}: missing required field '{field}'")
        cid = c.get("id")
        if cid in ids:
            errors.append(f"{where}: duplicate card id '{cid}'")
        if cid:
            ids.add(cid)
        if "effect_dsl" not in c:
            errors.append(f"{where}: missing 'effect_dsl' (use null for keyword-only or bespoke -- never omit it)")
        keywords = c.get("keywords") or []
        for kw in keywords:
            if kw not in glossary:
                errors.append(f"{where}: keyword '{kw}' is not in keyword_glossary")

        # The three buckets of reference/02-effect-dsl.md. effect_dsl: null means EITHER
        # "pure keyword, the engine handles it generically" OR "bespoke, resists the DSL" --
        # keywords are what tell them apart, so only the keyword-less case needs a reason.
        dsl = c.get("effect_dsl", "__absent__")
        if dsl not in (None, "__absent__"):
            composed += 1
        elif keywords:
            keyword_only += 1
        elif dsl is None:
            bespoke += 1
            if not c.get("bespoke_reason"):
                errors.append(
                    f"{where}: effect_dsl is null with no keywords, so this card reads as bespoke, "
                    "but bespoke_reason is missing. Add the reason, or add the keyword it uses."
                )
        if not (c.get("effect_text_exact") or "").strip() and not keywords:
            warnings.append(f"{where}: no effect text and no keywords -- is this card really blank?")

    if not glossary and any(c.get("keywords") for c in cards if isinstance(c, dict)):
        errors.append("cards.json: keywords are used but keyword_glossary is empty")

    total = len(cards)
    info.append(f"{total} cards ({keyword_only} keyword-only, {composed} DSL-composed, {bespoke} bespoke)")
    if total and bespoke / total > 0.05:
        warnings.append(
            f"{bespoke}/{total} cards ({bespoke / total:.0%}) are bespoke -- above ~5% the "
            "effect DSL is too thin (reference/02-effect-dsl.md). Extend it rather than approximating."
        )

    declared = (manifest.get("contents") or {}).get("cards") or {}
    if isinstance(declared.get("total"), int) and declared["total"] != total:
        errors.append(f"MANIFEST contents.cards.total is {declared['total']} but cards.json has {total}")
    if isinstance(declared.get("bespoke"), int) and declared["bespoke"] != bespoke:
        errors.append(f"MANIFEST contents.cards.bespoke is {declared['bespoke']} but cards.json has {bespoke}")
    return ids


def check_replays(root: Path, card_ids: set[str]):
    files = sorted((root / "replays").glob("*.json")) if (root / "replays").is_dir() else []
    if not files:
        errors.append("replays/ contains no .json files -- the bundle is unverifiable")
        return
    tags: dict[str, int] = {}
    verified = hashed_per_action = 0
    dist_missing: set[str] = set()
    sites_unnamed = [0]
    total_draws = [0]

    for p in files:
        data = load_json(p, p.name)
        if data is None:
            continue
        for field in ("replay_id", "engine_version", "setup", "random_log", "actions", "outcome"):
            if field not in data:
                errors.append(f"{p.name}: missing required field '{field}'")

        rlog = data.get("random_log")
        if rlog is None:
            pass
        elif not isinstance(rlog, list):
            errors.append(f"{p.name}: random_log must be an array")
        else:
            for n, e in enumerate(rlog):
                if not isinstance(e, dict):
                    errors.append(f"{p.name}: random_log[{n}] is not an object"); continue
                if e.get("seq") != n:
                    errors.append(f"{p.name}: random_log[{n}].seq is {e.get('seq')!r}, expected {n} "
                                  "(must be contiguous from 0, in draw order)")
                    break
                if "result" not in e:
                    errors.append(f"{p.name}: random_log[{n}] has no 'result'")
                if not e.get("where"):
                    sites_unnamed[0] += 1
                if e.get("kind") == "int" and "range" not in e:
                    dist_missing.add(e.get("where") or f"<unnamed @{n}>")
                if e.get("kind") == "bool" and "p" not in e:
                    dist_missing.add(e.get("where") or f"<unnamed @{n}>")
            total_draws[0] += len(rlog)

        setup = data.get("setup") or {}
        players = setup.get("players") or []
        if len(players) < 2:
            errors.append(f"{p.name}: setup.players needs at least 2 entries")
        for pl in players:
            for cid in (pl.get("deck") or []):
                if card_ids and cid not in card_ids:
                    errors.append(f"{p.name}: deck references unknown card id '{cid}'")

        actions = data.get("actions") or []
        if not actions:
            errors.append(f"{p.name}: no actions -- not a complete game")
        for n, a in enumerate(actions):
            if a.get("seq") != n:
                errors.append(f"{p.name}: actions[{n}].seq is {a.get('seq')!r}, expected {n} (must be contiguous from 0)")
                break
        if actions and all(a.get("state_hash_after") for a in actions):
            hashed_per_action += 1

        v = data.get("verification") or {}
        if v.get("replayed_clean_process"):
            verified += 1

        for t in data.get("coverage_tags") or []:
            tags[t] = tags.get(t, 0) + 1

    n = len(files)
    info.append(f"{n} replays, {total_draws[0]} logged random draws")
    if n < 20:
        warnings.append(f"only {n} replays -- 20 is the minimum useful corpus, 100+ for a full export")
    if dist_missing:
        shown = ", ".join(sorted(dist_missing)[:6])
        warnings.append(
            f"{len(dist_missing)} random site(s) log an outcome but no distribution ({shown}). "
            "A recorded 2 falls inside both [1,3] and [1,4], so without 'range'/'p' a rebuild can "
            "reproduce every replay and still generate out-of-distribution games. Add the distribution."
        )
    if sites_unnamed[0]:
        warnings.append(
            f"{sites_unnamed[0]} random_log entries have no 'where' label -- a divergence can then "
            "only be located by state, not by the decision point where control flow parted"
        )
    if hashed_per_action < n:
        info.append(f"{n - hashed_per_action} replays have no per-action state hashes (optional)")
    # Thresholds scale with corpus size: a 20-replay starter bundle cannot carry 10 of each slice.
    want = 1 if n < 60 else 10
    for tag in ("bespoke_cards", "trigger_collision", "win_condition"):
        if tags.get(tag, 0) < want:
            warnings.append(
                f"coverage tag '{tag}': {tags.get(tag, 0)} replays, {want}+ recommended at this "
                f"corpus size ({n} replays)"
            )
    if tags:
        info.append("coverage tags: " + ", ".join(f"{k}={v}" for k, v in sorted(tags.items())))


def check_notes(root: Path):
    p = root / "NOTES.md"
    if not p.exists():
        return
    text = p.read_text(encoding="utf-8").lower()
    for section in NOTES_SECTIONS:
        if section not in text:
            warnings.append(f"NOTES.md has no section covering '{section}'")


def scan_secrets(root: Path):
    hits = 0
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".md", ".json", ".txt", ".csv", ".yaml", ".yml"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern, label in SECRET_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                line = text.count("\n", 0, m.start()) + 1
                warnings.append(f"possible {label}: {p.relative_to(root)}:{line} -- {m.group(0)[:60]!r}")
                hits += 1
                break
    if hits:
        warnings.append(f"{hits} possible-secret matches -- review each BY HAND before sending (reference/05-privacy-and-tiers.md)")
    else:
        info.append("secret scan: no matches")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"not a directory: {root}")
        return 2

    result = check_manifest(root)
    manifest, tier = result if result else ({}, 0)
    check_required_files(root, tier)
    if manifest:
        check_checksums(root, manifest)
    card_ids = check_cards(root, manifest)
    check_replays(root, card_ids)
    check_notes(root)
    scan_secrets(root)

    print(f"\n=== engine-export bundle validation: {root} ===\n")
    for line in info:
        print(f"  info     {line}")
    for line in warnings:
        print(f"  WARN     {line}")
    for line in errors:
        print(f"  ERROR    {line}")

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    if errors:
        print("FAIL -- the bundle is not ready to send.")
        return 1
    print("PASS -- no blocking errors. Review the warnings; they are advice, not gates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
