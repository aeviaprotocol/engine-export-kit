---
name: game-export-probe
description: Answer whether a card game can be exported as a reproducible headless simulator, and prove it with a handful of verified golden replays. Use when asked to check if a game engine is deterministic enough to export for AI testing, to produce a sample export, or as the first step before a full engine export.
---

# Can this game be exported as a reproducible simulator?

A one-afternoon probe, not a full export. It answers whether a faithful external copy of
this game is possible at all, and proves the answer with evidence rather than opinion.

If the probe succeeds there is a full export specification to follow afterwards. If it
fails, it fails cheaply and tells you exactly why — which is the point.

**Nothing in this asks for source code.** The output is a short report plus a few small
data files.

---

## Why this is worth your afternoon regardless

Everything below is foundational tooling for your own project:

| What the probe tests | What it gives you |
|---|---|
| One seedable random source | Reproducible bug reports: "seed 41823, turn 6" instead of "it happened once" |
| Serializable game state | Save/load, resume, spectate, crash recovery |
| Replaying a recorded game | A regression suite: change a card, replay 500 games, see exactly what broke |
| Headless execution | CI that runs thousands of balance simulations per commit |

A studio that passes this probe has automated balance testing. The export is a side effect.

---

## Step 1 — Answer three questions, in this order

Report the answers before writing any code. They gate everything that follows, and the
first one gates the other two.

### 1. Does all randomness come from ONE seedable generator?

Not the language's global RNG. Not `Math.random()`, `random.random()`, `rand()`, or
`UnityEngine.Random`. Not one generator per subsystem. One generator, owned by the game
state, threaded through every draw — shuffles, random targets, coin flips, everything.

**If the answer is no, stop and say so.** This is the single most common blocker and
nothing else is achievable until it is fixed. The fix is usually small and contained:
create a `GameRandom` owned by the game state, seed it at match creation, route every draw
through it, and fail the build on any direct use of the global RNG.

Also report: the algorithm by name, the shuffle algorithm by name and direction, and
whether anything in game logic depends on wall-clock time, thread scheduling, dictionary
iteration order, or floating-point arithmetic. Each of those four breaks reproducibility.

### 2. Can the complete game state be serialized and restored?

The test: serialize mid-game, restore into a fresh instance, continue with the same seed
and the same remaining actions, and arrive at an identical final state.

What gets forgotten: per-card-instance state (damage, buffs, counters, attachments,
summoning sickness, "has attacked this turn", silenced flags, cost modifiers), stable
instance identity, deck ordering, per-turn counters, and the RNG's own position.

### 3. Can the engine run without a renderer?

If yes, say so prominently — it unlocks a far better option later, where you ship a headless
build and nothing has to be reimplemented by anyone.

---

## Step 2 — Prove it with five golden replays

**This is the actual test.** If you can produce five replays that reproduce exactly, the
whole approach works. If you cannot, nothing else in a larger export would be trustworthy.

Record five complete games. Any play quality — a scripted bot, random legal moves, your own
test harness. For each, write one JSON file:

```json
{
  "replay_id": "probe-01",
  "engine_version": "1.4.2+abc1234",
  "seed": 418237,
  "setup": {
    "players": [
      {"id": 0, "deck": ["card_001", "card_001", "card_014"]},
      {"id": 1, "deck": ["card_007", "card_022"]}
    ],
    "first_player": 0
  },
  "actions": [
    {"seq": 0, "player": 0, "action": {"type": "play_card", "instance": "i_12",
                                       "targets": ["i_31"]},
     "state_hash_after": "sha256:9f2c..."},
    {"seq": 1, "player": 0, "action": {"type": "end_turn"},
     "state_hash_after": "sha256:1b7e..."}
  ],
  "initial_state_hash": "sha256:00ab...",
  "final_state_hash": "sha256:4ab8...",
  "outcome": {"winner": 0, "reason": "opponent_hero_destroyed", "turns": 11}
}
```

`seq` must be contiguous from 0. A hash after **every** action is what makes a divergence
locatable to the action that caused it rather than to the whole game — do not skip them.

State the hashing rules you used: how keys are ordered and how numbers are formatted.
Someone reimplementing in another language has to match them byte for byte, or every hash
mismatches for a reason that has nothing to do with the game.

### Then verify, on a clean process

For each replay: start a fresh process, rebuild the match from the seed and setup, apply
every recorded action, and confirm each hash matches.

Report how many of the five reproduce. **A replay that does not reproduce is a determinism
bug in your engine** — one worth finding regardless of this project, since it is also
blocking your own ability to reproduce player bug reports.

---

## Step 3 — Send a small sample of the content format

Not the whole collection. Ten cards is enough to show the shape, chosen as: three plain
keyword cards, three with composable effects, three with your most awkward bespoke effects,
and one unreleased card **renamed** (`"Dragonlord Ignis"` → `"card_4471"`, flavor and art
dropped, cost and effect kept exactly as-is — behavior is what matters, names are not).

Per card: stable id, cost, type, stats, keywords, the exact in-game text, and how the effect
is represented internally — a script, a data structure, an enum, inheritance, or "hardcoded
per card". That last answer is a valid and useful one; say it plainly if it is the truth.

Also send one page of rules covering turn structure, phases, win conditions, and —
most important — **what happens when several triggers fire at once.** Describe the behavior
your engine actually implements, and note it if that differs from the design intent.

---

## Step 4 — Report

```
RNG:        one seedable source? yes/no · algorithm · shuffle algorithm + direction
            determinism hazards (clock / threads / dict order / floats): ...
STATE:      serializable? yes/no · serialize-restore-resume test: PASS/FAIL
HEADLESS:   can run without a renderer? yes/no
REPLAYS:    __/5 reproduced exactly on a clean process
            hashing rules used: ...
CARDS:      how effects are represented internally: ...
            roughly what share of the collection is bespoke rather than composable: ...
BLOCKERS:   what would have to change for a full export
EFFORT:     rough estimate for the full export, now that you have seen the shape
```

**Do not include** credentials, server endpoints, player data, telemetry, anti-cheat logic,
matchmaking internals, or pack-odds and drop-rate code. Grep the files you are about to send
for `api_key|secret|token|password|https?://` and review the matches by hand.

---

## What good and bad outcomes look like

**5/5 replays reproduce** → a full export is straightforward. Proceed.

**3/5 reproduce** → there is a determinism bug. Finding it is valuable to the studio
independently of this project. Report which replays failed and at which action.

**0/5, because randomness is scattered** → the expected and most common outcome, and not a
dead end. It is a small, contained fix, and it is the one thing worth doing before anything
else here.

**Cannot serialize state** → a bigger lift. Worth discussing scope before committing to it.
