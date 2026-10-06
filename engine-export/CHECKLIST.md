# Acceptance checklist

Work top to bottom. Report which items pass. Anything unchecked goes in `NOTES.md` with a
reason — an acknowledged gap is fine, an unacknowledged one is not.

## Blocking — do not send without these

```
[ ] All randomness routes through ONE seedable generator owned by the game state
[ ] Same-seed replay verified: 100 seeds, 2 clean processes, identical final states
[ ] 100+ golden replays generated
[ ] Every shipped replay verified to reproduce exactly on a clean process
[ ] Hash canonicalization documented (key ordering + number formatting)
[ ] python3 validate_bundle.py <bundle_dir> exits 0
[ ] Secret scan run and matches reviewed by hand
[ ] No source code in the bundle
[ ] MANIFEST.json complete, with SHA-256 checksums for every file
```

## Rules

```
[ ] RULES.md covers all 11 sections of the template
[ ] Resolution order for simultaneous effects is specified               ← most-missed
[ ] Implemented behavior documented where it differs from design intent
[ ] Every win/loss/draw condition listed, including deck-out and timeout
[ ] Every zone listed with ordering, limits, overflow and per-player visibility
[ ] Timing edge cases covered (death mid-resolution, zone change, dangling references)
```

## Cards

```
[ ] cards.json validates against templates/cards.schema.json
[ ] Every card has exact in-game text in effect_text_exact
[ ] Keywords enumerated with exact semantics in effects.md
[ ] Bespoke cards (effect_dsl: null) listed in NOTES.md — NOT approximated
[ ] Bespoke count reported, and under ~5% (or the DSL gap is flagged)
[ ] Balance/version history included for cards that have changed
[ ] Unreleased content decision made: included / anonymized / excluded
[ ] If anonymized: subtypes and tribal names remapped CONSISTENTLY
```

## State and actions (Tier 1+)

```
[ ] state-schema.json covers card instance state, not just definition ids
[ ] Stable card instance identity survives serialization
[ ] RNG position included in the state
[ ] Per-turn counters included
[ ] Per-player visibility included
[ ] Zone ordering explicit (deck order especially)
[ ] Serialize-resume verified at EVERY action of a full game
[ ] actions.md includes one fully worked enumeration example
[ ] Legal-action set confirmed deterministic given the state
```

## Determinism killers

```
[ ] Wall-clock dependence: absent, or documented
[ ] Thread/async order dependence: absent, or documented
[ ] Hash iteration order in game logic: absent, or documented
[ ] Float arithmetic in game logic: absent, or exposure documented
[ ] Cross-platform replay: verified, or explicitly not tested
```

## Replays

```
[ ] Coverage table filled (per deck, per win condition, bespoke cards,
    shortest/longest, multi-trigger collisions, max board/hand, mirrors)
[ ] 10+ replays specifically exercising bespoke cards
[ ] 10+ replays with simultaneous trigger collisions
[ ] No replay references an excluded card
[ ] REPLAYS.md documents format, generation method and verification result
```

## Fork (Tier 1+, optional but high value)

```
[ ] State cloning supported and documented
[ ] No shared mutable references between a clone and its original
[ ] Sub-seed policy for divergent branches documented
[ ] Approximate cost per clone measured and reported
```

## Honesty

```
[ ] NOTES.md: known bugs the clone must reproduce
[ ] NOTES.md: intentional quirks that look like bugs
[ ] NOTES.md: unresolved behaviors — flagged, not guessed
[ ] NOTES.md: what the receiving team will NOT be able to reproduce
```

## The one test that matters most

```
[ ] Your own engine, given each golden replay's seed and action list, reproduces that
    replay's final state EXACTLY, byte for byte, on a clean process.
```

If that fails, the bundle is not ready — and you have found a real determinism bug, which
is worth more to you than the export.
