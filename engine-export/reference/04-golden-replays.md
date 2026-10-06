# 04 — Golden replays

**Last verified: 2026-10-05**

The validation protocol, and the single most important part of the bundle.

**Why:** a rules document is an interpretation. Golden replays are ground truth. The
receiving team reimplements your engine, replays the games, and either matches you exactly
or knows precisely which card or which rule they got wrong. Without them, a clone is a guess
that nobody can check — and the failure is silent: it plays plausibly and differs subtly.

A bundle with 500 good replays and no written spec is more useful than a polished spec with
20 replays.

---

## What a replay is

Deck lists, the recorded random outcomes, the complete ordered action list, and optional
state dumps. Schema: `../templates/replay.schema.json`.

**There is no seed.** Randomness is carried as a `random_log` of what actually came out, so
replaying never depends on matching your RNG, shuffle algorithm or draw order — see
`03-determinism.md`.

```json
{
  "replay_id": "replay-0001",
  "engine_version": "1.4.2+abc1234",
  "setup": {
    "players": [
      { "id": 0, "deck": ["card_001", "card_001", "card_014"], "hero": "hero_02" },
      { "id": 1, "deck": ["card_007", "card_022"], "hero": "hero_01" }
    ],
    "first_player": 0
  },
  "random_log": [
    { "seq": 0, "where": "setup.shuffle.p0", "kind": "permutation",
      "result": ["card_014", "card_001", "card_001"] },
    { "seq": 1, "where": "card.bolt.damage_roll", "kind": "int", "range": [1, 3], "result": 2 }
  ],
  "actions": [
    { "seq": 0, "player": 0, "action": { "type": "mulligan", "keep": [0, 2, 3] } },
    { "seq": 1, "player": 0, "action": { "type": "play_card", "instance": "i_12",
                                         "targets": ["i_31"] } },
    { "seq": 2, "player": 0, "action": { "type": "end_turn" } }
  ],
  "checkpoints": [
    { "after_seq": 1, "state_hash": "sha256:9f2c...", "state": { } }
  ],
  "outcome": { "winner": 0, "reason": "opponent_hero_destroyed", "turns": 11 },
  "final_state_hash": "sha256:4ab8..."
}
```

**Checkpoint policy.** Full state at the start, after every turn, and at the end. A
`state_hash` after *every* action. Full states are bulky; hashes are cheap and localize a
divergence to the exact action that caused it — which is the difference between "our clone
is wrong somewhere" and "our clone is wrong on card_014's trigger order".

---

## Coverage tags must be DERIVED, not asserted

Tag each replay from **what actually happened during the run**, by instrumenting the
recorder — not by assigning labels you believe should apply.

This is not pedantry. In a real end-to-end test of this kit, an exporter assigned
`deck_reshuffle` to every seventh game by arithmetic. Not one of the twenty games ever
reshuffled the deck. A deliberately planted bug inside the reshuffle path then passed all
twenty replays, because no replay reached it — while the bundle advertised coverage of
exactly that mechanic.

**A fabricated tag is worse than no tag**: it converts missing coverage into false
confidence.

The `random_log` makes this checkable for free. The set of `where` labels a replay contains
*is* the set of random code paths it exercised. Derive tags from that, and from whatever
non-random branches you can cheaply instrument.

## Coverage — don't just generate 100 random games

Random games under-sample exactly the behavior that is hardest to reimplement. Deliberately
include:

| Slice | Minimum | Why |
|---|---|---|
| Per deck/archetype in the export | 10 each | Each exercises different cards |
| **Cards with conditional randomness** | 5+ each | A branch that draws randomness only sometimes is where a log most often has a gap |
| Per win condition | 5 each | Deck-out, timeout, draws and simultaneous death are where clones break |
| **Bespoke-card games** | 10+ | Cards with `effect_dsl: null` are undescribed; replays are their *only* specification |
| Shortest games you can produce | 5 | Setup and early-game edge cases |
| Longest games you can produce | 5 | Resource caps, deck exhaustion, overflow, counter limits |
| Multi-trigger collisions | 10 | Resolution order (`01-export-spec.md` §7) — the most common source of divergence |
| Max board / max hand states | 5 | Overflow behavior |
| Mirror matches | 5 | Symmetry breaking and first-player effects |

Generating these is easiest with a scripted agent that plays greedily plus one that plays
randomly, and a filter that keeps games touching the target cards. Random play alone is
fine for bulk but will not reach the interesting states.

---

## Generation and verification

Generate with whatever plays legally — scripted AI, random agent, recorded human games, or
your existing test bots. Playstyle quality does not matter; **legality and coverage do.**

Then verify. This is not optional:

```
for each replay:
    fresh process
    construct the match from seed + setup
    apply every action in sequence
    assert each checkpoint's state_hash matches
    assert final_state_hash matches
    assert outcome matches
```

Report in `replays/REPLAYS.md`:

```markdown
# Golden replays
Count: · Engine version: · Generated by: · Generated on:

## Coverage
| slice | count |

## Verification
Replayed on a clean process: <n>/<n> PASS
Cross-platform:              PASS / FAIL / not tested
Divergences:                 <none, or list with the action seq where each diverged>

## Hashing
What is hashed: <canonical serialization of which fields>
Excluded from the hash: <timestamps, UI state, anything non-deterministic by design>
Canonicalization: <key ordering, number formatting — needed for cross-language agreement>
```

**Only relevant if you included state dumps.** Document the hash canonicalization precisely. The receiving team reimplements in a
different language. If your JSON serializer orders keys differently or formats numbers
differently from theirs, every hash mismatches and the bundle looks broken when it isn't.
Specify key ordering and number formatting, or ship a short reference canonicalizer as data
rather than engine code.

---

## If any replay fails to reproduce on your own engine

With recorded randomness this is much rarer than it used to be, because the replay no longer
depends on your RNG behaving reproducibly. If it still happens, the cause is usually a random
call site that is not being logged, or wall-clock / thread-scheduling influence on game
logic. Both are worth finding regardless of this project.

If it genuinely cannot be fixed in time: exclude the replay, document the cause in
`NOTES.md` under "unresolved", and say which behaviors are therefore unverifiable. Honest
and incomplete beats complete and wrong.
