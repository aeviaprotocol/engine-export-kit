# 05 — What to hold back, and the tiers

**Last verified: 2026-10-05**

The bundle is balance-sensitive by construction: it fully describes your game's meta. Treat
it like internal design documentation, under whatever agreement covers that.

---

## Never in the bundle

Non-negotiable. Scan before sending.

- Credentials, API keys, tokens, signing keys, certificates
- Server endpoints, internal hostnames, infrastructure topology
- Player data of any kind — accounts, IDs, names, purchase history, telemetry
- Anti-cheat logic or detection heuristics
- Matchmaking and ranking internals
- Monetization: pack odds, drop rates, pricing, pity-timer logic
- Employee names, internal ticket IDs, absolute file paths that leak directory structure
- Source code *(the whole design of this kit is that you export data instead)*

A grep for `api_key|secret|token|password|https?://|@yourstudio` over the finished bundle
catches most of it. Review the matches by hand.

---

## Usually fine to include

- Rules and timing behavior — the players already know this, or could learn it
- Released card data — already public in your client
- Known bugs, in `NOTES.md` — the clone must reproduce them, and hiding them produces a clone that silently disagrees
- Replays of synthetic games played by bots — no human play involved

---

## Needs a decision: unreleased content

Unreleased cards make the export more useful (more coverage, more interesting replays) and
are the most leak-sensitive thing in it.

Three options, in increasing caution:

**1. Include it.** Best fidelity. Only under an agreement you're comfortable with.

**2. Anonymize it.** The useful middle path, and usually the right answer. An agent needs to
know what a card *does*, not what it's called:

```
name          "Dragonlord Ignis"  →  "card_4471"
flavor text   dropped
art reference dropped
set / release "expansion_12"      →  "unreleased_a"
subtypes      "dragon"            →  "subtype_07"   (consistently, across all cards)
cost / stats / effect_dsl / keywords   ← keep EXACTLY as-is
```

Keep the mechanical substance and a consistent mapping, and the export stays fully valid
for AI purposes. Keep the mapping table yourself; don't send it. Subtype and tribal names
must be remapped *consistently* or synergies break.

**3. Exclude it.** Ship only released content. Note the exclusion in `NOTES.md`, and
confirm no replay references an excluded card — a replay with a dangling card id fails
verification and looks like a clone bug.

---

## Tiers in detail

### Tier 0 — Data export
**Effort:** ~1 day if card data is already structured.
**Ship:** `MANIFEST.json`, `rules/RULES.md`, `cards/cards.json`, `rng/RNG.md`, `replays/` (100+), `NOTES.md`.
**You share:** no code, no binary, no API.
**Risk:** reimplementation drift on edge cases. Replays bound it; they don't eliminate it.
**Mitigation:** more replays, weighted toward the cards and interactions you couldn't describe well.

### Tier 1 — Data export + contracts *(recommended)*
**Effort:** ~2–5 days.
**Adds:** `rules/state-schema.json`, `rules/actions.md`, `cards/effects.md`.
**Why it's the sweet spot:** reimplementation goes from interpretive to mechanical. The
state schema and action enumeration are what an agent actually programs against, and the
effect DSL closes most remaining ambiguity.
**Risk:** low, and concentrated in whatever cards stayed bespoke.

### Tier 2 — Headless engine
**Effort:** ~1–2 weeks, mostly decoupling from the renderer.
**Adds:** a container running your engine behind `reset(seed, config)` / `step(action)` /
`legal_actions()` / `serialize()` / `restore()`.
**Why it wins:** nothing is reimplemented, so fidelity is exact by construction. No drift,
ever.
**Requires:** willingness to share a binary, and an engine that runs without a renderer.
**Expose the Gymnasium / PettingZoo interface shape.** Don't invent an API — every tool the
receiving team owns already speaks that one.

**The ideal is Tier 2 *and* the Tier 1 data export.** The container guarantees fidelity
today; the data export means the work survives the container going unmaintained, a version
bump, or the team needing to run a modified variant.

---

## What you should ask for in return

This is a two-way exchange. Reasonable asks of the receiving team:

- **Balance findings.** An agent playing 100,000 games finds degenerate lines your playtesters won't. This is the most valuable thing they can give you back.
- **The bugs they find.** Reimplementing your engine from a spec is an extremely thorough code review. They will find real divergences.
- **Their replay corpus**, so you can use it as a regression suite.
- **Determinism fixes**, if they find any in your engine.

The export is worth more to you than it looks. A team that rebuilds your rules engine from
scratch and replays 500 games against it will tell you things about your game that nobody
else can.
