# Engine Export Kit

**For game developers.** A procedure for exporting your card game's rules, card data and
match generation into a portable bundle, so an external team can run AI agents against a
faithful, isolated, reproducible copy of your game.

**Last verified: 2026-10-05** · Version 0.1

---

## What this is

You have a card game. Someone wants to train and test AI agents on it. Neither of you
wants them poking at your live build or reverse-engineering your client.

This kit produces a **bundle**: a directory of data files that describes your game
completely enough to rebuild it as a headless simulator, plus **golden replays** that
*prove* the rebuild is faithful.

**You do not send source code.** You send an export.

## What you get out of it

Every artifact this kit asks for is something you want anyway. If your engine can't
produce one, that's a gap in your own tooling, not a favor you're doing someone else:

| Artifact | What it also gives you |
|---|---|
| Single seedable RNG source | Reproducible bug reports. "Seed 41823, turn 6" instead of "it happened once" |
| Serializable game state | Save/load, crash recovery, spectate, resume |
| Legal-action enumerator | The foundation of any AI opponent, tutorial hint system, or "you missed lethal" nudge |
| Golden replays | A regression suite. Change a card, replay 500 games, see exactly what broke |
| Machine-readable card DB | Balance dashboards, automated card-text validation, localization checks |
| Headless mode | CI. Thousands of balance simulations per commit |

Teams that build this get automated balance testing. The AI export is a side effect.

---

## How to run it

Point your coding agent at this directory inside your game's repository.

| Your tool | What to do |
|---|---|
| **Claude Code / Claude** | `SKILL.md` is a skill. Drop this directory in `.claude/skills/` or just say "follow `kits/engine-export/SKILL.md`" |
| **Cursor, Codex, Copilot, Windsurf** | `AGENTS.md` points the agent at the procedure. Most agent tools read it automatically |
| **ChatGPT, Gemini, any chat LLM** | Paste `PROMPT.md`. It's self-contained |
| **By hand** | `CHECKLIST.md`, then `reference/01-export-spec.md` |

Expect **2–5 days** of engineering for Tier 1 on a codebase whose author knows it well.
Tier 0 can be done in a day if your card data is already structured.

---

## The three tiers

Pick based on what you're willing to share and how much fidelity matters. Higher is better
for everyone, but Tier 0 is genuinely usable.

### Tier 0 — Data export *(floor: ~1 day)*
Rules document, card database, RNG contract, 100+ golden replays. No code, no API.
The receiving team reimplements your engine from the spec and validates against the replays.
**Risk:** reimplementation drift on edge cases. The replays bound it but don't eliminate it.

### Tier 1 — Data export + contracts *(recommended: ~2–5 days)*
Tier 0, plus a serializable state schema, the legal-action enumeration spec, and your
effect system expressed as a DSL. Reimplementation becomes mechanical rather than
interpretive.
**This is the sweet spot.** Most of the remaining ambiguity disappears.

### Tier 2 — Headless engine *(best: ~1–2 weeks)*
You ship a container running *your own* engine headless, behind a small step/reset API.
Nothing is reimplemented, so fidelity is exact by construction.
**Requires:** you're willing to share a binary, and your engine can run without a renderer.
Still include the golden replays — they become the container's smoke test.

**Tier 2 plus the Tier 1 data export is the ideal.** The container guarantees fidelity; the
data export means the work survives if the container stops being maintained.

---

## What the bundle looks like

```
<game>-export-v<version>/
├── MANIFEST.json          what's here, engine version, tier, checksums
├── rules/
│   ├── RULES.md           turn structure, phases, timing, win conditions
│   ├── state-schema.json  (Tier 1+) complete serializable state
│   └── actions.md         (Tier 1+) legal-action enumeration
├── cards/
│   ├── cards.json         the full card database
│   └── effects.md         (Tier 1+) the effect DSL: primitives, targeting, triggers
├── rng/
│   └── RNG.md             every random draw, in order, and how to seed it
├── replays/
│   ├── replay-0001.json   ... 100+ complete games
│   └── REPLAYS.md         format, how they were generated, how to verify
└── NOTES.md              known bugs, intentional quirks, what's out of scope
```

Schemas and templates are in `templates/`. The full specification of each file is in
`reference/01-export-spec.md`.

---

## Before you start: what NOT to send

Read `reference/05-privacy-and-tiers.md`. Short version:

- **Never** send credentials, server endpoints, signing keys, player data, or telemetry.
- **Never** send anti-cheat logic, matchmaking internals, or monetization/drop-rate code unless you specifically mean to.
- Unreleased content can be **held back or renamed** — the agent doesn't need to know a card is called "Dragonlord". It needs to know what the card *does*. See the anonymization recipe.
- The bundle is **balance-sensitive**: it fully describes your meta. Treat it like design docs, under whatever agreement you'd use for those.

---

## Checking your own bundle

```
python3 validate_bundle.py <bundle_dir>
```

Standard library only — nothing to install. It checks structure, cross-references (every
card id a replay uses actually exists), MANIFEST counts and checksums, coverage, the
determinism flags, and scans for anything credential-shaped. Errors are blocking; warnings
are advice.

Run it before sending. The receiving team runs the same script on arrival, so there is no
surprise about what counts as a valid bundle.

## Acceptance

You are done when `CHECKLIST.md` passes, `validate_bundle.py` exits 0, and specifically
when this holds:

> Your own engine, fed the seed and the action list from each golden replay, reproduces
> that replay's final state **exactly**, byte for byte, on a clean process.

If that fails, the bundle is not ready — and you've found a real determinism bug in your
engine, which is worth knowing regardless.

---

## Prior art, so you know this isn't invented from nothing

| | |
|---|---|
| **Forge** (Magic) | Card behavior in per-card text scripts with parameters for properties, effects and abilities, editable without recompiling. The model for `cards.json` + `effects.md`. |
| **mtgjson / Cockatrice** | Machine-readable card data as a published artifact, with keyword abilities auto-parsed. |
| **Ludii** | Games described declaratively as composable "ludemes" — 547 of them covering 1,000+ games including card, dice and hidden-information games. Prior art for declarative rules. |
| **Gymnasium / PettingZoo** | The `reset()`/`step()` interface the Tier 2 container should expose. Don't invent an API. |
| **SabberStone, Fireplace** | Community Hearthstone simulators — what this kit exists to make unnecessary. |

What doesn't exist, as far as we can tell: a standard protocol for *"developer, export your
engine so an outside team can rebuild it faithfully."* That's what this is.
