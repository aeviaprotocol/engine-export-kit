# Engine Export Kit

**A handoff protocol for game studios.** Export your card game's rules, cards, effect
system and match generation into a portable bundle, so an outside team can rebuild it as a
headless, deterministic, reproducible simulator — and *prove* the rebuild is faithful.

You do not send source code. You send an export.

**Status: v0.4 — tested end to end against three real games.**

| Game | What it tested | Result |
|---|---|---|
| [RLCard](https://github.com/datamllab/rlcard) UNO | the full loop: export → validate → rebuild from scratch | **20/20 replays reproduced exactly** |
| [Forge](https://github.com/Card-Forge/forge) | the effect model on 34,074 cards in a text DSL | 24 operations cover 80% — a vocabulary exists |
| [XMage](https://github.com/magefree/mage) | the effect model on 32,498 cards as Java classes | 2,083 operations for 80%, 92% tail — no vocabulary exists |

Those last two are the same genre at the same scale and they gave **opposite answers**, which
is why step 1 of the export is now a five-minute measurement of whether a reusable effect
vocabulary exists at all. Assuming the wrong one wastes weeks.

The testing found six real bugs in this kit, all fixed. The most useful: mutation testing
planted a bug in a code path no replay exercised, and it passed every replay — while the
bundle's coverage tags claimed that path was covered. **Coverage tags must be derived from the
run, not asserted.**

**You run this inside your own repository and the code never leaves it.** Still not run
against a closed commercial engine — please open an issue when you hit a rough edge.

**v0.2 removed the biggest obstacle.** v0.1 required a seedable, single-source RNG. It no
longer does: replays carry a log of the random outcomes that actually occurred, and a
rebuilt engine consumes those instead of generating its own. **Keep calling `Math.random()`
wherever you already do.** You only have to log what it returned.

MIT licensed. Run it, fork it, adapt it.

---

## The shape of the engagement

Two phases, documented in [`PROTOCOL.md`](PROTOCOL.md).

| | Phase 1 — qualify | Phase 2 — play |
|---|---|---|
| You do | run `ASK.md` in your repo | integrate a small SDK |
| It produces | data: effect vocabulary, rules, replays | agents driving your real engine |
| Your cost | hours, no commitment | days, a dependency in your build |

**Phase 1 commits you to nothing**, and its output is what phase 2 is designed against, so
none of it is wasted either way. The gate between them is `ASK.md` step 1 — the
five-minute measurement of whether your card logic has a reusable vocabulary or is mostly
one-off. That answer decides whether an external rebuild is realistic at all.

## Start here, not with the full spec

Two artifacts, two jobs.

### 1. [`ASK.md`](ASK.md) — start here. Runs inside your repo.

One self-contained file. Point your coding agent at it and it works through seven steps in
your own codebase, emitting a `bundle/` directory you review before anything is sent.

**The source never leaves the repository.** The agent reads it and emits extracted data.
Most of the work is extraction rather than authorship — grep-scale, even on tens of
thousands of cards — and prose is asked for only where reading the code is the only way to
know: resolution order when several triggers fire at once, win conditions, timing edge cases.

The orienting questions:

1. Does a reusable effect vocabulary exist, or is most card logic one-off? (step 1 — measure it)
2. Can you log what each random call returns? (not reproduce it — just log it)
3. Can the complete game state be serialized? (useful, not required)
4. Can the engine run without a renderer?

### 2. [`engine-export/`](engine-export/) — the full specification.

Fifteen files. Send for this once the probe passes.

---

## Why this is worth your time regardless of who asked

Every artifact either half requests is foundational tooling for your own project:

| What the kit asks for | What it gives you |
|---|---|
| Logging your random outcomes | Reproducible bug reports: replay the exact game instead of "it happened once" |
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
| **0** Data + replays | hours | Content data as-is, replay logs | Reimplementation drift, bounded by the replays |
| **1** + extracted spec *(recommended)* | hours | Plus the effect vocabulary, resolution order and state schema, extracted in your repo | Low |
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
