---
name: game-engine-export
description: Export a card game's rules, card database, effect system and match generation into a portable bundle so external teams can run AI agents against a faithful, isolated, reproducible copy. Use when asked to export a game engine for AI testing, produce a headless simulator spec, make a game reproducible for agent training, generate golden replays, or hand game rules to an AI research team.
---

# Game engine export

You are working inside a game studio's repository. Your job is to produce an **export
bundle** that lets an outside team rebuild this game as a headless, deterministic,
forkable simulator — and to produce the evidence that the rebuild is faithful.

Read `README.md` in this directory for the tiers and the bundle layout. The detailed
specification of every file is in `reference/01-export-spec.md`.

## Hard rules

1. **Never put source code in the bundle.** Export data and specifications. If you cannot describe a behavior without pasting the function, describe it in the effect DSL (`reference/02-effect-dsl.md`) and flag it as needing review.
2. **Never export secrets.** Credentials, endpoints, keys, player data, telemetry, anti-cheat, matchmaking, monetization and drop rates are all out of scope. Run the scan in step 7 before declaring done.
3. **Do not guess at behavior.** If the code is ambiguous, you cannot determine resolution order, or a card's implementation is bespoke and unclear, write it into `NOTES.md` under "unresolved" and tell the user. A wrong spec is far worse than a missing one, because it produces a clone that is subtly wrong and nobody notices.
4. **Change nothing in the game.** This is a read-and-export task. The one exception is step 4, and only with explicit permission.
5. **Golden replays are the deliverable, not a nice-to-have.** A bundle without them is unverifiable and should not be sent.

## Procedure

### 1. Map the engine

Before writing anything, locate and report these six things. Do not proceed until you have
found them or confirmed they don't exist:

| What | Typical shape |
|---|---|
| **Card definitions** | data files (JSON/XML/YAML/CSV), a database, a spreadsheet export, or classes per card |
| **Effect / ability system** | how a card's behavior is expressed — scripts, an interpreter, inheritance, or hardcoded per card |
| **Turn loop** | the state machine: phases, priority, who acts when |
| **Game state object** | what holds the truth, and whether it is already serializable |
| **RNG** | every source of randomness, and whether they route through one seedable generator |
| **Match setup** | deck construction, mulligan, first-player determination, starting resources |

Report your findings as a short table with file paths **before** going further, and state
which tier looks achievable. If the user disagrees with your read of the architecture, they
will correct you now rather than after you've written a wrong spec.

### 2. Determine the achievable tier

Per `README.md`. Ask the user to confirm the target. The determining questions:

- Can the engine run **without a renderer**? → gates Tier 2
- Is the game state **already serializable**, or could it be with modest work? → gates Tier 1
- Is **all randomness** seeded from one source? → gates everything, including Tier 0's replays

If randomness is scattered across ad-hoc calls, say so plainly. It is the single most
common blocker and it must be fixed before any tier is achievable. See
`reference/03-determinism.md` for what the fix looks like.

### 3. Write the rules document

`rules/RULES.md`, using the template in `reference/01-export-spec.md`.

Write it for a competent engineer who has never seen the game. Cover turn structure,
phases, the resource system, timing and resolution order, combat, state-based effects,
and win/loss/draw conditions.

**The section people get wrong is resolution order.** When three triggers fire at once,
what happens? Describe the actual implemented behavior, not the design intent, and say so
if they differ.

### 4. Establish the RNG contract

`rng/RNG.md`. Follow `reference/03-determinism.md`.

Enumerate every random draw in the game, in the order it occurs, and document how the
seed reaches it. If randomness is **not** currently single-sourced and seedable, stop and
tell the user: this is a change to their engine and needs their decision. It is usually a
small, contained change and it is the highest-value thing in this whole kit for the studio
itself.

### 5. Export the card database

`cards/cards.json`, validating against `templates/cards.schema.json`.

Every card, every field, every version. Include cards that are disabled or unreleased only
if the user approves — and offer the anonymization recipe in
`reference/05-privacy-and-tiers.md` as the middle path.

For card effects, express behavior in the DSL from `reference/02-effect-dsl.md`:
- Mechanical keywords that your engine already handles generically → name the keyword
- Composite effects → compose from DSL primitives
- Genuinely bespoke effects that resist the DSL → mark `"effect_dsl": null`, write prose in `effect_text_exact`, and list the card in `NOTES.md` under "bespoke". **Do not approximate.** An approximated card is a silent wrongness bug.

Count and report the bespoke cards. If more than ~5% resist the DSL, the DSL needs
extending — tell the user rather than approximating the long tail.

### 6. Generate golden replays

`replays/`, following `reference/04-golden-replays.md`. **This is the acceptance test for
the whole bundle.**

Generate at least 100 complete games (300+ is better), covering: every archetype or deck
in the export, games that end by each possible win condition, at least 10 games selected
specifically because they exercise bespoke or unusual cards, and the shortest and longest
games you can produce.

Each replay records the seed, the full action list, and state checkpoints. Then **verify**:
feed each replay's seed and actions back into the engine on a clean process and confirm the
final state matches exactly. A replay that doesn't reproduce is a determinism bug — report
it, don't ship it.

### 7. Scan and finalize

- Run `python3 validate_bundle.py <bundle_dir>` (standard library only). Errors are blocking; warnings are advice. Fix the errors and re-run until it exits 0.
- Review every secret-scan match by hand — the scan is deliberately noisy, so it will flag harmless URLs alongside real problems.
- Write `MANIFEST.json` from `templates/MANIFEST.json`, including checksums.
- Write `NOTES.md`: known bugs the clone should reproduce, intentional quirks, unresolved items from step 3, bespoke cards from step 5, and anything explicitly out of scope.
- Work `CHECKLIST.md` top to bottom and report which items pass.

### 8. Report

Tell the user: tier achieved, card count and bespoke count, replay count and verification
result, every unresolved item, and anything you changed or recommend changing in the engine.

Be explicit about what the receiving team will *not* be able to reproduce. That sentence is
more valuable than a longer bundle.

## Known failure modes

- **Scattered randomness.** The usual blocker. Catch it in step 2, not step 6.
- **Hidden state in the renderer.** Animation timing or UI state that affects outcomes. Look for it; it makes headless mode lie.
- **Floating-point order dependence.** If damage or shuffles depend on float arithmetic or iteration order over a hash map, replays will diverge across platforms. Document it.
- **Wall-clock or thread dependence.** Timers, `now()`, async resolution races. All break reproducibility.
- **"The code is the spec."** If a behavior only exists as code nobody can explain, that is the finding. Write it down as unresolved.
- **Approximating the long tail of cards.** The most damaging failure, because it produces a bundle that passes every check and a clone that plays a different game.
