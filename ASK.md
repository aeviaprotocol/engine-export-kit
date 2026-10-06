---
name: game-export-gather
description: Gather the raw material an external team needs to rebuild this card game as a headless simulator for AI testing. Collects the content data files as-is, identifies where the engine makes random decisions, adds logging to record them, and produces replay logs of real games. Gathering only - it does not write specifications.
---

# What we need from you

We want to rebuild your game as a headless simulator, in isolation, so we can run AI agents
against it as many times as we like without touching your build.

**We do the analysis. You ship raw material.** Writing up your rules, classifying card
effects, designing a state schema — that is our job, and we have to do it anyway while
rebuilding. Asking you to do it first would mean you doing work twice.

So this is short. Four things.

---

## 1. Your content data, exactly as it already exists

Card definitions, keywords, sets, stats, effects — in whatever form they live in. JSON, XML,
YAML, CSV, a spreadsheet export, a database dump, ScriptableObjects, resource files.

**Do not transform, clean up or document it.** If it is one messy file, send the messy file.
Normalizing it is our problem, and your normalization would lose information we need.

## 2. Read access to the engine code

A repository invite, or a zip of the relevant modules — the turn loop, the effect system,
the resolution order, the card implementations.

This is how we learn what is random and what the odds are, which rules the code actually
implements versus what the design doc says, and where the edge cases live. It is far more
reliable than you describing it to us, and it means you write nothing.

We do not redistribute it, and nothing from it goes into anything we publish.

**If you cannot share code, say so now** — there is a different, heavier process for that
case, and it is better to know before you start.

## 3. Replay logs — the only part that needs engineering

**This is the one thing only you can do**, because it requires running your engine.

We need recorded games. For each game, a JSON file with:

```json
{
  "replay_id": "game-001",
  "engine_version": "1.4.2+abc1234",
  "setup": {
    "players": [{"id": 0, "deck": ["card_001", "card_001", "card_014"]},
                {"id": 1, "deck": ["card_007", "card_022"]}],
    "first_player": 0
  },
  "random_log": [
    {"seq": 0, "where": "setup.shuffle.p0", "kind": "permutation",
     "result": ["card_014", "card_001", "card_001"]},
    {"seq": 1, "where": "card.bolt.damage_roll", "kind": "int",
     "range": [1, 3], "result": 2},
    {"seq": 2, "where": "card.hex.proc", "kind": "bool", "p": 0.3, "result": false}
  ],
  "actions": [
    {"seq": 0, "player": 0, "action": {"type": "play_card", "instance": "i_12",
                                       "targets": ["i_31"]}},
    {"seq": 1, "player": 0, "action": {"type": "end_turn"}}
  ],
  "state_dumps": [{"after_seq": 1, "state": { }}],
  "outcome": {"winner": 0, "reason": "opponent_hero_destroyed", "turns": 11}
}
```

### The `random_log` is the important part, and it is easier than it sounds

Every time your engine makes a random decision, append what came out. **You do not need a
seedable or single-source RNG, and you do not need reproducibility.** Keep calling
`Math.random()` wherever you already do. We just need to know what it returned.

Our engine replays these outcomes instead of generating its own, so your shuffle algorithm,
your draw order and your language's RNG become irrelevant. That removes what is normally the
biggest obstacle in this kind of handoff.

Two details that carry real weight:

- **`where`** — any stable label for the call site. When our rebuild drifts from yours, this tells us the exact decision point where control flow parted, which is a far better clue than a mismatched end state.
- **`range` / `p`** — the distribution, not just the outcome. A recorded `2` sits inside both `[1,3]` and `[1,4]`, so without the distribution we can reproduce every one of your games perfectly and still generate wrong ones when the agent plays. This single field is what prevents a simulator that looks correct and is not.

Practically: wrap your random calls in a logging helper, or monkeypatch the RNG for a
debug build. If you miss a call site, our engine runs out of log entries at a precise point
and we tell you exactly which one — it is iterative, not all-or-nothing.

### How many, and of what

**20 games** is enough to start. Any play quality — a scripted bot, random legal moves, your
own test harness, or recorded human games. We care about coverage, not skill:

- a few per deck or archetype you want us to support
- at least one ending by each possible win condition, including deck-out, timeout and draws
- a few that exercise your most awkward cards, the ones whose logic you would warn a new hire about
- your shortest and longest games

### `state_dumps`

Whatever your state serializer already produces, at the start, after each turn, and at the
end. If you have no serializer, skip it and say so — the replays still work, we just lose
the ability to pinpoint *where* a divergence started.

## 4. One decision from you

What is in and out of scope. Game modes, unreleased content, anything you would rather not
share. Unreleased cards can be **renamed** — `"Dragonlord Ignis"` → `"card_4471"`, art and
flavor dropped, cost and effect kept exactly. We need to know what a card does, never what
it is called.

**Never send** credentials, server endpoints, keys, player data, telemetry, anti-cheat logic,
matchmaking internals, or pack odds and drop rates. Grep for
`api_key|secret|token|password|https?://` before sending and check the matches by hand.

---

## What you get out of it, independent of us

The replay logging is the part you keep:

- **Reproducible bug reports.** Replay the exact game instead of "it happened once."
- **A regression suite.** Change a card, replay 500 recorded games, see precisely what moved.
- **Balance CI.** Thousands of simulated games per commit.
- **Balance findings from us.** An agent playing 100,000 games finds degenerate lines no playtester will, and rebuilding your rules engine from your code is the most thorough review it will ever get. Both come back to you.

---

## Send

```
content/        your data files, untouched
replays/        20+ JSON files as above
NOTES.md        known bugs we should reproduce, cards you would warn us about,
                anything deliberately out of scope
```

Plus the code access, however you prefer to grant it.

Then we take it from there. Expect questions — mostly about resolution order when several
triggers fire at once, because that is where rebuilds usually go wrong.
