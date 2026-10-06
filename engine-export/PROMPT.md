# Paste-in prompt

For use with any chat LLM that can read the repository (ChatGPT, Gemini, Claude, or a
coding agent without skill support). Paste everything below the line, after attaching or
granting access to the game's source.

---

You are helping a game studio export their card game so an external AI research team can
rebuild it as a headless, deterministic, reproducible simulator. The goal is that the team
can run AI agents against a faithful copy of the game in an isolated environment, as many
times as they want, without touching the live build.

**You are producing a data and specification bundle. Never put source code or secrets in it.**

## Step 1 — Map the engine, and report before continuing

Find and report, with file paths, where each of these lives:

1. **Card definitions** — data files, database, or classes
2. **Effect/ability system** — how card behavior is expressed
3. **Turn loop** — phases, priority, the state machine
4. **Game state** — what holds the truth, and whether it serializes
5. **RNG** — every source of randomness, and whether one seedable generator feeds them all
6. **Match setup** — deck construction, mulligan, first player, starting resources

Stop and show me this table before writing anything else.

## Step 2 — Tell me which tier is achievable

- **Tier 0** — rules doc + card database + RNG contract + 100 golden replays. No code, no API.
- **Tier 1** *(recommended)* — Tier 0 plus a serializable state schema, legal-action enumeration spec, and the effect system as a DSL.
- **Tier 2** — a container running the real engine headless behind a `reset()`/`step()` API, so nothing is reimplemented.

Deciding questions: can the engine run without a renderer (Tier 2)? Is state serializable
(Tier 1)? **Is all randomness seeded from one source (everything)?**

If randomness is scattered across ad-hoc calls, say so now. It blocks every tier and must
be fixed first.

## Step 3 — Build the bundle

```
<game>-export-v<version>/
├── MANIFEST.json       contents, engine version, tier, checksums
├── rules/RULES.md      turn structure, phases, timing and RESOLUTION ORDER, win conditions
├── rules/state-schema.json   (Tier 1+) complete serializable state
├── rules/actions.md    (Tier 1+) how to enumerate legal actions from a state
├── cards/cards.json    every card: id, cost, type, stats, keywords, effect, exact text
├── cards/effects.md    (Tier 1+) effect primitives, targeting, triggers, resolution
├── rng/RNG.md          every random draw in order, and how seeding works
├── replays/            100+ complete games: seed + action list + state checkpoints
└── NOTES.md            known bugs, intentional quirks, unresolved items, bespoke cards
```

Write `RULES.md` for a competent engineer who has never seen the game. **Be most careful
with resolution order** — when several triggers fire at once, what actually happens? Document
the implemented behavior, and say so if it differs from design intent.

For card effects: name the keyword if the engine handles it generically; compose from
primitives if it's composite; and if an effect genuinely resists expression, set it to null,
record the exact card text, and list the card under "bespoke" in `NOTES.md`.
**Never approximate a card** — an approximation produces a clone that passes every test and
plays a different game.

## Step 4 — Golden replays. This is the acceptance test.

Generate at least 100 complete games covering every deck in the export, every win condition,
the shortest and longest games you can produce, and at least 10 chosen to exercise bespoke
cards. Record seed, full action list, and state checkpoints.

Then **verify**: replay each one into the engine on a clean process from its seed and action
list, and confirm the final state matches **exactly**. Report any that diverge — those are
real determinism bugs, and the bundle isn't ready until they're resolved or documented.

## Step 5 — Scan and report

Run `python3 validate_bundle.py <bundle_dir>` from the kit directory — standard library
only, nothing to install. Fix every error and re-run until it exits 0; warnings are advice.
Review the secret-scan matches by hand. Then report: tier achieved, card count, bespoke count, replay count and
verification result, every unresolved item, and what the receiving team will **not** be able
to reproduce.

That last sentence matters more than bundle size. Be explicit about the gaps.
