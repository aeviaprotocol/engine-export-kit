# 01 — Export specification

**Last verified: 2026-10-05**

What every file in the bundle must contain. Schemas in `../templates/`.

---

## `MANIFEST.json`

The entry point. A receiving team reads this first to know what they have.
Template: `../templates/MANIFEST.json`. Required: game name, engine version/commit, export
date, tier, file list with SHA-256 checksums, card count, replay count, and the contact for
questions. Checksums matter — a bundle that silently lost a file during transfer is worse
than one that obviously failed.

---

## `rules/RULES.md`

Prose, for a competent engineer who has never played the game. Use this skeleton:

```markdown
# <Game> — Rules specification
Engine version: · Export date: · Audience: reimplementers

## 1. Objective and win conditions
Every way the game can end, including draws, timeouts, decking out, and
simultaneous-death resolution.

## 2. Game setup
Deck size limits and copy limits. Starting hand. Mulligan rules, exactly.
First-player determination. Starting resources and any first/second player asymmetry.

## 3. Zones
Every zone (deck, hand, play/board, graveyard, exile, hero/leader, side zones).
For each: ordered or unordered, size limit, overflow behavior, and visibility per player.

## 4. Turn structure
Phases in order. What happens automatically in each. Where each player may act.
Any phase that can be skipped or repeated.

## 5. Resource system
How resources accrue, cap, carry over, and are spent. Alternate costs.

## 6. Playing cards and taking actions
Legality conditions. Targeting rules and restrictions. What happens to an action whose
target becomes invalid before resolution.

## 7. Resolution order  ← THE SECTION THAT MATTERS MOST
How simultaneous effects resolve. Stack, queue, priority, or active-player-first.
When several triggers fire at once: what order, and is it deterministic?
Can resolution cascade, and is there a depth or loop limit?
Describe the IMPLEMENTED behavior. If it differs from design intent, say so here.

## 8. Combat / attacking
Declaration, ordering, damage assignment, simultaneity, post-combat cleanup.

## 9. State-based effects and continuous modifiers
Auras, buffs, layers. How recalculation is ordered and when it happens.

## 10. Timing edge cases
Death while resolving. Zone change mid-resolution. Effects referencing removed objects.
Replacement effects. Infinite-loop handling.

## 11. Known divergences from design intent
Bugs the clone must reproduce to match replays. This section is a feature.
```

Sections 7 and 11 are the two that determine whether a reimplementation is faithful. Spend
your time there.

---

## `rules/state-schema.json` *(Tier 1+)*

JSON Schema for the complete game state. The test: **two states that serialize identically
must be functionally identical** — same legal actions, same outcome distribution under the
same seed. If anything outside this schema affects play, the schema is incomplete, and that
is exactly the bug class that makes replays diverge.

Must cover: per-player zones with ordering, resources, the full state of every card
instance (not just its definition id — damage, buffs, counters, attachments, summoning
sickness, flags), turn and phase, the pending-resolution stack or queue, the RNG state or
draw counter, and per-player visibility.

**Distinguish card *definition* from card *instance*.** Instances carry mutable state and
need stable identity across the game.

---

## `rules/actions.md` *(Tier 1+)*

How to enumerate every legal action from a given state. This is the most important file for
the receiving team after the replays, because it is the API an agent actually calls.

Specify: the action vocabulary (play card, attack, activate, choose target, pass, concede,
and any choice-point actions), the encoding, how a composite action decomposes into atomic
steps, how targeting choices are represented, how the engine rejects illegal actions, and
**whether the legal-action set is deterministic given the state** (it must be).

Include a worked example: one state, and the complete enumerated legal action set for it.
One concrete example resolves more ambiguity than three pages of prose.

---

## `cards/cards.json`

Validate against `../templates/cards.schema.json`. Every card, with:

- `id` — stable, never reused
- `name`, `set`, `rarity`, `collectible`, `enabled`
- `cost`, `type`, `subtypes`, base stats
- `keywords` — only mechanics the engine handles generically
- `effect_dsl` — behavior per `02-effect-dsl.md`, or `null` if bespoke
- `effect_text_exact` — the exact in-game text, verbatim
- `version` / `balance_history` — if the card has been changed, every revision with dates

Report the bespoke count. Above ~5% means the DSL needs extending; tell the user instead of
approximating the tail.

---

## `cards/effects.md` *(Tier 1+)*

The effect system itself: primitive vocabulary, targeting selectors, trigger events,
resolution semantics, and how composition works. See `02-effect-dsl.md`.

---

## `rng/RNG.md`

See `03-determinism.md`. Must answer: how many independent random sources exist (the right
answer is one), how the seed reaches them, every random draw in the game enumerated in
order, the shuffle algorithm by name, and whether any draw depends on wall-clock, thread
scheduling, hash iteration order, or float arithmetic.

---

## `replays/`

See `04-golden-replays.md`. 100 minimum, 300+ preferred, plus `REPLAYS.md` documenting the
format, how they were generated, and the verification result.

---

## `NOTES.md`

The honesty file, and the one a receiving engineer will thank you for:

```markdown
## Known bugs the clone must reproduce
<behaviors that are wrong but that the replays depend on>

## Intentional quirks
<behavior that looks like a bug and isn't>

## Unresolved
<behavior we could not determine from the code — flagged, not guessed>

## Bespoke cards
<cards whose effects resist the DSL, with why>

## Out of scope
<deliberately excluded: game modes, content, systems>

## What the receiving team will NOT be able to reproduce
<the most valuable section in the bundle>
```
