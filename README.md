# Engine Export Kit

**A handoff protocol for game studios.** Export your card game's rules, cards, effect
system and match generation into a portable bundle, so an outside team can rebuild it as a
headless, deterministic, reproducible simulator — and *prove* the rebuild is faithful.

You do not send source code. You send an export.

**Status: v0.1.** The specification is complete and the validator is tested. It has not yet
been run end to end against a commercial engine. Expect rough edges on first contact, and
please open an issue when you hit one — that feedback is the point of v0.1 being public.

MIT licensed. Run it, fork it, adapt it.

---

## Start here, not with the full spec

Two artifacts, two jobs.

### 1. [`ASK.md`](ASK.md) — the probe. One afternoon.

One self-contained file. It answers whether a faithful export is possible at all, and proves
it with **five golden replays that reproduce on a clean process**.

Those five replays are the real test. If they reproduce, a full export is straightforward.
If they cannot be produced, nothing in a larger bundle would be trustworthy — and you
learned that in an afternoon instead of a week.

Before them it asks three questions, in order, because the first gates the other two:

1. Does **all** randomness come from one seedable generator?
2. Can the complete game state be serialized and restored?
3. Can the engine run without a renderer?

### 2. [`engine-export/`](engine-export/) — the full specification.

Fifteen files. Send for this once the probe passes.

---

## Why this is worth your time regardless of who asked

Every artifact either half requests is foundational tooling for your own project:

| What the kit asks for | What it gives you |
|---|---|
| One seedable RNG source | Reproducible bug reports. "Seed 41823, turn 6" instead of "it happened once" |
| Serializable game state | Save/load, resume, spectate, crash recovery |
| Legal-action enumeration | The foundation of any AI opponent, tutorial hint, or "you missed lethal" nudge |
| Golden replays | A regression suite. Change a card, replay 500 games, see exactly what broke |
| Machine-readable card DB | Balance dashboards, card-text validation, localization checks |
| Headless mode | CI running thousands of balance simulations per commit |

A studio that completes this has automated balance testing. The export is the side effect.

---

## How to run it

Drop the folder into your game's repository and use whichever entry point matches your
tooling. Nothing to install — the validator is Python standard library only.

| Your tool | Entry point |
|---|---|
| Claude Code / Claude | `engine-export/SKILL.md` (or drop the folder in `.claude/skills/`) |
| Cursor, Codex, Copilot, Windsurf | `engine-export/AGENTS.md` |
| ChatGPT, Gemini, any chat LLM | paste `engine-export/PROMPT.md` |
| By hand | `engine-export/README.md`, then `CHECKLIST.md` |

`ASK.md` works the same four ways, and also reads fine pasted into a message.

Check your own bundle before sending it:

```bash
python3 engine-export/validate_bundle.py <bundle_dir>
```

It checks structure, cross-references, MANIFEST counts and checksums, replay coverage, the
determinism flags, and scans for anything credential-shaped. Errors block; warnings advise.
The receiving team runs the same script, so there is no disagreement about what counts as a
valid handoff.

---

## The three tiers

| Tier | Effort | You share | Fidelity risk |
|---|---|---|---|
| **0** Data export | ~1 day | Rules, cards, RNG contract, 100+ replays. No code, no API | Reimplementation drift, bounded by the replays |
| **1** + contracts *(recommended)* | ~2–5 days | Plus state schema, action enumeration, effect DSL | Low, concentrated in bespoke cards |
| **2** Headless engine | ~1–2 weeks | A container running your engine behind `reset()`/`step()` | **None** — nothing is reimplemented |

Tier 2 *plus* the Tier 1 data export is ideal: the container guarantees fidelity today, the
data export means the work survives the container going unmaintained.

---

## What never goes in a bundle

Credentials, server endpoints, signing keys, player data, telemetry, anti-cheat logic,
matchmaking internals, monetization and drop rates, and source code. Unreleased content can
be held back, or **anonymized** — an agent needs to know what a card does, not that it is
called "Dragonlord Ignis". The recipe is in
[`reference/05-privacy-and-tiers.md`](engine-export/reference/05-privacy-and-tiers.md).

A bundle fully describes your game's meta. Treat it like internal design documentation,
under whatever agreement covers that.

---

## What to ask for in return

This is an exchange, not a favor. Reasonable asks of whoever receives your bundle:

- **Balance findings.** An agent playing 100,000 games finds degenerate lines no playtester will.
- **The bugs they find.** Reimplementing your engine from a spec is the most thorough code review it will ever get.
- **Their replay corpus**, to use as your own regression suite.
- **Determinism fixes**, if they find any in your engine.

---

## Prior art

The pieces are proven individually; the protocol is what was missing.

| | |
|---|---|
| **Forge** (Magic) | Card behavior in per-card text scripts with parameters for properties, effects and abilities, editable without recompiling. The model for `cards.json` + `effects.md` |
| **mtgjson / Cockatrice** | Machine-readable card data as a published artifact, keyword abilities auto-parsed |
| **Ludii** | Games described declaratively as composable "ludemes" — 547 of them across 1,000+ games including card, dice and hidden-information games |
| **Gymnasium / PettingZoo** | The `reset()`/`step()` interface a Tier 2 container should expose. Don't invent an API |
| **SabberStone, Fireplace** | Community-built simulators of a commercial card game — reverse-engineered, perpetually behind. What this kit exists to make unnecessary |

What does not appear to exist: a standard protocol for *"developer, export your engine so an
outside team can rebuild it faithfully, with evidence."* That is what this is.

---

## Scope

v0.1 is **card-game shaped**: `cards.json`, a card-effect DSL, turn-based match structure.
The determinism, state, replay and validation halves are general and transfer to other
genres with little change. Ports welcome.

## Contributing

Issues and PRs welcome, particularly: a tier-2 container reference implementation, ports to
non-card genres, and reports from running this against a real engine — including the parts
that did not work.
