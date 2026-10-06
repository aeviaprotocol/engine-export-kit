# 03 — Randomness, state and fork

**Last verified: 2026-10-06**

> **This file changed in v0.2.** It used to require a seedable, single-source RNG. It no
> longer does, and that removes what was the single biggest obstacle to exporting a game.
> If you read an earlier version: you can keep calling `Math.random()` wherever you already
> do.

---

## The distinction that makes this cheap

Two different things get confused, and separating them is what lets you skip the refactor:

| To... | You need | Who provides it |
|---|---|---|
| **Reimplement** the game | the **distributions** — "1–3 uniform", "30% chance", "uniform permutation" | readable from your code, or declared in the log |
| **Validate** against a recorded game | the **realized outcomes** — what actually came out, in order | your replay log |

Neither needs your RNG to be seedable, single-sourced, or reproducible. A rebuilt engine in
replay mode **consumes your recorded outcomes instead of generating its own**, which makes
your shuffle algorithm, your draw order and your language's RNG implementation irrelevant.

Those three were the usual reasons an export failed. They no longer apply.

---

## What you do have to do: log it

Every random decision, appended in the order it happens:

```json
{"seq": 0, "where": "setup.shuffle.p0", "kind": "permutation",
 "result": ["card_014", "card_001", "card_001"]}
{"seq": 1, "where": "card.bolt.damage_roll", "kind": "int", "range": [1, 3], "result": 2}
{"seq": 2, "where": "card.hex.proc",        "kind": "bool", "p": 0.3,       "result": false}
```

`kind` is one of `int`, `bool`, `choice`, `permutation`, `float`. `seq` is contiguous from 0.

**`result` must use stable, serializable identifiers** — card ids, or indices into the input
sequence. Not object references, not `repr()` output, never memory addresses. This sounds
obvious and is the first thing a real export gets wrong: dumping a shuffled deck with the
language's default serializer yields something like
`"<game.Card object at 0x7a3e8e...>"`, which is different on every run and means nothing to
anyone else. The validator rejects it.

**For `choice`, option order matters.** The receiving engine must offer the same options in
the same order, or a recorded choice is ambiguous. If your order is not obvious from the
data, say what it is.

Practically: wrap your random calls in a logging helper, or monkeypatch the RNG in a debug
build. If your engine already has a replay or spectate feature, you may have most of this.

**Missing a call site is recoverable and self-diagnosing.** The rebuilt engine runs out of
log entries at a precise point, and the error names the site it was expecting — so you are
told exactly which one you missed. Iterative, not all-or-nothing.

### Two fields that carry real weight

**`where`** — any stable label for the call site. When a rebuild drifts from your engine,
this names the exact decision point where control flow parted, and it fires *at that moment*
rather than one action later as a mismatched state. It is a strictly better diagnostic than a
state hash, and it costs you a string literal.

**`range` / `p`** — the distribution, not just the outcome. **This is the one that prevents a
silent failure**, so it is worth being precise about why:

> A recorded `2` sits inside both `[1,3]` and `[1,4]`. If the log records only the outcome, a
> rebuild that reads the range wrong **reproduces every one of your replays perfectly** — and
> then generates out-of-distribution games the moment an agent plays. Every automated check
> passes. Nobody notices.

Declaring the distribution turns that into an exact, immediate error. Sites where you omit it
remain unverifiable, and the receiving team must record them as such.

---

## The cheaper substitute: complete state dumps

Instrumenting random call sites is the one part of this that takes real engineering. There is
a path that skips it: **emit a complete state dump after every action**, including deck order,
and let the receiving team validate transitions rather than replay games.

It works because the state after a shuffle *is* the shuffle result. Measured on a real engine
over 869 transitions with no random log whatsoever: a correct rebuild matched **98.5%**, with
the 1.5% residue falling exactly on the transitions that consume randomness; a rebuild with
one planted bug dropped to 93.1%, and every extra mismatch named the single wrong field.

The residue is not just tolerable noise — **it locates your random call sites**, which is the
work you skipped.

Two things it costs, both worth stating plainly:

- **Distributions are invisible.** Dumps show what came out, never the range it came from. A rebuild cannot distinguish a 1–3 roll from a 1–4 roll, so games it *generates* may be out of distribution while every transition still validates. Mitigate with a one-line note per random site declaring the distribution.
- **No whole-game replay.** Single-step validation never confirms that a full game comes out the same end to end, so errors that compound over a long game go unchecked.

Prefer the random log where it is cheap. Take this path where it is not — full dumps plus a
short list of distributions is close to as good, and usually much less work.

## State serialization — useful, not required

If you can serialize game state, include dumps at the start, after each turn, and at the end.
They are what let a divergence be localized to the action that caused it rather than to the
whole game.

If you cannot, say so and skip them. Replays still work; debugging is slower.

Where a serializer exists, these are the fields most often forgotten:

- **Card instance state** — damage, buffs, counters, attachments, summoning sickness, "has attacked this turn", silenced flags, cost modifiers. A definition id is not enough.
- **Stable instance identity** that survives serialization — effects referencing "the minion that triggered this" need it.
- **Zone ordering**, deck order especially.
- **Per-turn counters** — "cards played this turn", "second spell this turn".
- **Per-player visibility** — which player knows what.
- Pending resolution, if a state can be captured mid-resolution.

Note what is *not* on that list any more: the RNG's internal position. The log carries it.

### If you serialize, declare your canonicalization

Key ordering and number formatting. A rebuild in another language has to match it byte for
byte, or every hash mismatches for a reason unrelated to the game. Integers everywhere in
game logic is the robust choice; accumulated floats diverge across platforms.

---

## Fork — worth a sentence even though we do not ask for it

If state serializes, the receiving team gets state cloning nearly free, and that unlocks
forward search — enumerating candidate lines and simulating each. It is the strongest cheap
method for turn-based card games.

You do not have to build it. But if your state has shared mutable references that make deep
copying unsafe, mentioning it saves the other side a day.

---

## What this buys you

The logging is the part you keep, and it is foundational tooling rather than a favor:

- **Reproducible bug reports.** Replay the exact game instead of "it happened once."
- **A regression suite.** Change a card, replay 500 recorded games, see precisely what moved.
- **Balance CI.** Thousands of simulated games per commit.

A studio that adds random logging has a replay system. The export is the side effect.
