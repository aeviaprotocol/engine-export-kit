# 02 — Expressing card powers

**Last verified: 2026-10-05**

The hardest part of the export. A card's cost and stats are data; its *power* is behavior,
and behavior usually lives in code. This file is how you get behavior into the bundle
without shipping code.

**The model is Forge** (Magic): card behavior lives in per-card text scripts with
parameters for properties, effects and abilities, editable without recompiling. If your
engine already works that way, export those scripts and you are nearly done. If it doesn't,
build the vocabulary below.

---

## The three buckets

Sort every card into one of these. Report the counts.

### 1. Pure keyword
The engine already implements the mechanic generically. Just name it.

```json
{ "keywords": ["taunt", "charge"], "effect_dsl": null }
```

List every keyword in `effects.md` with its exact semantics. "Taunt" is not
self-explanatory across games — say what it does, including edge cases.

### 2. Composed from primitives
The majority of cards, once you have a decent primitive vocabulary.

```json
{
  "effect_dsl": {
    "trigger": "on_play",
    "effects": [
      { "op": "deal_damage", "amount": 2, "target": { "selector": "enemy_minion", "mode": "choose" } },
      { "op": "draw", "amount": 1, "target": { "selector": "self_player" } }
    ]
  }
}
```

### 3. Bespoke
Genuinely resists expression. Set `effect_dsl` to `null`, record the exact card text, and
list it in `NOTES.md`.

**Never approximate a bespoke card.** An approximation passes every automated check and
produces a clone that plays a different game — the single most damaging outcome of this
whole process. A missing card is visible; a wrong card is not.

If bucket 3 exceeds ~5% of the collection, the vocabulary is too thin. Extend it rather
than approximating the tail.

---

## Primitive vocabulary

A starting set. **Extend it to fit your game** — this is a template, not a standard. What
matters is that it is closed, documented, and that every composed card uses only listed
primitives.

**Effect operations.** `deal_damage` · `heal` · `draw` · `discard` · `destroy` ·
`transform` · `summon` · `return_to_hand` · `modify_stats` (temporary or permanent) ·
`add_keyword` · `remove_keyword` · `gain_resource` · `set_cost_modifier` · `shuffle_into` ·
`search` · `copy` · `counter` · `silence` · `freeze` · `attach` · `move_zone` ·
`force_action` · `prevent`

For each, document: required parameters, whether the amount can be dynamic (see below),
what happens with no legal target, and whether it can fail partway through.

**Target selectors.** Separate *what can be chosen* from *who chooses*:
```
selector : self_player | opponent_player | any_player
         | self_minion | enemy_minion | any_minion
         | self_hero | enemy_hero
         | card_in_hand | card_in_deck | card_in_graveyard
         | zone_all | self_source
mode     : choose (controller picks) | random | all | automatic
filters  : cost / type / subtype / stat comparisons / keyword presence / state flags
count    : fixed N | up_to N | all
```

**Triggers.** When the effect fires:
```
on_play · on_death · on_attack · on_damaged · on_heal
start_of_turn · end_of_turn · on_draw · on_discard
on_summon_other · on_spell_cast · on_zone_change
continuous (an aura; active while present, not an event)
activated (requires a player action and possibly a cost)
```

For each trigger, document: whether it fires for both players' events or only the
controller's, whether it fires on itself, and **where it sits in resolution order**
(`01-export-spec.md` §7).

**Conditions.** Gating:
```json
{ "op": "deal_damage", "amount": 3,
  "condition": { "check": "controls_minion_with_subtype", "value": "dragon" } }
```

**Dynamic values.** Amounts that read from state — the most commonly under-specified part
of a card DSL:
```json
{ "op": "deal_damage",
  "amount": { "dynamic": "count", "selector": "self_minion", "filter": { "subtype": "beast" } } }
```
Document **when** a dynamic value is evaluated: on play, on resolution, or continuously.
Same card text, three different games.

---

## The acceptance test for the DSL

> For every card in bucket 2, replaying its `effect_dsl` against a state produces exactly
> what the engine produces.

Make that a test in your repo. If you can write an interpreter over your own DSL and have
it agree with your engine on the golden replays, the DSL is correct and the receiving team
can trust it. If you can't, say so in `NOTES.md` — an unverified DSL is a hypothesis.

---

## Shortcut if you have no DSL at all

Don't build a full interpreter just for this export. Do this instead:

1. Export cards with `effect_dsl: null` and exact text for **every** card.
2. Build the DSL for the **mechanical keywords** only — usually 80% of cards by play rate.
3. Lean much harder on golden replays: generate 500+ instead of 100, weighted toward games
   that exercise the undescribed cards.
4. List every undescribed card in `NOTES.md`.

The receiving team can then infer behavior from replays and verify against them. Slower for
them, far cheaper for you, and honest. A Tier 0 bundle with 500 well-chosen replays beats a
Tier 1 bundle with approximated card effects.
