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

## Named bindings — required, not optional

The vocabulary below is not enough on its own. A card pool of any real size needs **named,
reusable sub-logic**: a value computed once and referenced in several places, or a
sub-effect chained after another.

Measured against Forge's 34,074 Magic card scripts: **75.4% of cards use a named variable**
(`SVar`), and chained sub-effects (`SubAbility$`) are routine. A DSL without this cannot
express three quarters of a real collection, however long its operation list is.

```json
{
  "definitions": {
    "X": {"dynamic": "count", "selector": "self_minion", "filter": {"subtype": "beast"}}
  },
  "effects": [
    {"op": "deal_damage", "amount": {"ref": "X"}, "target": {"selector": "enemy_hero"}},
    {"op": "draw",        "amount": {"ref": "X"}, "target": {"selector": "self_player"},
     "then": {"op": "discard", "amount": 1, "target": {"selector": "self_player"}}}
  ]
}
```

Three things this gives you, each of which is otherwise impossible:

- **One evaluation, many uses.** `X` is computed once. Writing the expression twice is a different card whenever state changes mid-resolution.
- **Chaining.** `then` runs only if the parent effect resolved, which is distinct from being the next item in `effects`.
- **Scope.** Document whether a definition is visible to chained sub-effects and to triggers the effect creates. Getting this wrong is a silent divergence.

## Primitive vocabulary

A starting set. **Extend it to fit your game** — this is a template, not a standard. What
matters is that it is closed, documented, and that every composed card uses only listed
primitives.

**Before building any of it, measure whether a vocabulary exists at all.** This is the single
most important measurement in the export, it takes minutes, and getting it wrong wastes weeks.

Count the distinct operations, how many cover 80% of occurrences, and what share of the
vocabulary is used by two cards or fewer. Two real engines, same genre, comparable size,
opposite answers:

| | Cards | Distinct ops | Ops for 80% | Tail (≤2 cards) | Verdict |
|---|---|---|---|---|---|
| **Forge** — cards in a text DSL | 34,074 | 194 | **24** | 15% | **Concentrated** |
| **XMage** — one Java class per card | 32,498 | 8,469 | **2,083** | **92%** | **Diffuse** |

**Concentrated** → a reusable vocabulary genuinely exists. Build the top ~25 operations, get
most of the collection working as data, and treat the tail as a tail. Forge also carries 253
keywords and 1,207 distinct parameter names, so do not plan for 25 to be the final number.

**Diffuse** → **there is no vocabulary to extract, and you should not build a DSL.** When
card-specific logic becomes a card-specific class, the "vocabulary" is a catalogue of one-offs:
92% of XMage's effect classes serve two cards or fewer. Writing a DSL for that is writing
32,000 special cases. Ship the card catalogue plus exact rules text instead, and let the
replays specify per-card behavior — which means the corpus needs to be much larger, because
each card is pinned only by the replays that exercise it.

The practical consequence: in a diffuse codebase, **replay count replaces DSL coverage** as
the thing that determines whether a rebuild is faithful. Negotiate for it up front.

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
