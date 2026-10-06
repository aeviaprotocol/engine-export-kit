# 03 — Determinism, state and fork

**Last verified: 2026-10-05**

The contract that makes everything else possible. If this file's requirements aren't met,
the bundle cannot be validated, the receiving team cannot A/B a change, and golden replays
are meaningless.

Three properties, in order of how much they unlock:

| Property | Unlocks |
|---|---|
| **Seeded determinism** | replays, regression tests, bug reproduction, any trustworthy benchmark |
| **Serializable state** | save/load, resume, spectating, parallel evaluation |
| **Fork (clone a state mid-game)** | forward search — Monte Carlo tree search, enumerate-and-evaluate agents, "did I miss lethal" analysis |

Fork is the one studios don't expect to care about and the one that most changes what an
agent can do. It is also nearly free if state is serializable.

---

## 1. Seeded determinism

### Requirement

> One seed, one action sequence, one identical final state. Every time, on a clean process.

### The single-source rule

All randomness comes from **one** seedable generator, threaded through the game state. Not
the language's global RNG. Not `Math.random()`, `random.random()`, `rand()`, `Random.Range`
or `UnityEngine.Random`. Not one generator per subsystem.

**If your engine doesn't work this way, this is the fix to make first.** It is usually
small and contained: create a `GameRandom` owned by the game state, seed it at match
creation, route every draw through it, and fail the build on any direct use of the global
RNG. The studio gets reproducible bug reports out of it; the export is a side effect.

### Enumerate every draw

In `rng/RNG.md`, list every random decision in the game in the order it occurs:

```markdown
| # | When | What | Distribution | Draws |
|---|------|------|--------------|-------|
| 1 | match setup | first player | uniform 2 | 1 |
| 2 | match setup | deck shuffle (P1) | Fisher-Yates | n-1 |
| 3 | match setup | deck shuffle (P2) | Fisher-Yates | n-1 |
| 4 | mulligan | replacement draws | — | varies |
| 5 | card: <name> | random enemy target | uniform over legal | 1 |
```

Name the shuffle algorithm. "We shuffle the deck" is not reproducible; "Fisher-Yates,
iterating downward, consuming one draw per swap" is.

### The four determinism killers

Check for each explicitly and document any you find — they cause replays to diverge across
machines, which looks like a clone bug and isn't:

1. **Wall-clock** — `now()`, timers, timeouts affecting outcomes rather than just UX.
2. **Thread scheduling / async** — resolution order depending on which coroutine finishes first.
3. **Hash iteration order** — iterating a dictionary or set where order affects the result. Use ordered collections anywhere that touches game logic.
4. **Floating-point** — accumulated float arithmetic in damage or stat calculation can differ across platforms and compiler flags. Integers everywhere in game logic is the robust answer; if you can't, document the exposure.

### Verify it

Not "we believe it's deterministic" — measure:

```
for each of 100 seeds:
    run the same match twice, same actions, two clean processes
    assert serialize(final_state_a) == serialize(final_state_b)
```

Then run it across platforms if you ship on more than one. Report the result in `RNG.md`.

---

## 2. Serializable state

### Requirement

> `deserialize(serialize(s)) == s` functionally: identical legal actions, identical outcome
> distribution under the same seed, for the remainder of the game.

### What gets missed

The schema is almost always incomplete on the first attempt. The usual omissions:

- **Card instance state** — damage taken, buffs, counters, attachments, summoning sickness, "has attacked this turn", silenced flags, cost modifiers. The definition id is not enough.
- **Stable instance identity** — effects that reference "the minion that triggered this" need an id that survives serialization.
- **Pending resolution** — the stack or queue mid-resolution, if a state can be captured there.
- **RNG position** — the generator's internal state, or a draw counter sufficient to resume the stream.
- **Per-turn counters** — "cards played this turn", "second spell this turn", "damage dealt this turn".
- **Visibility** — which player knows what. Needed for correct agent observations *and* for determinization against hidden information.
- **Zone ordering** — deck order especially. An unordered deck breaks replays silently.

### Verify it

```
play a random game, serializing after every single action
for each snapshot:
    deserialize into a fresh engine
    continue with the recorded remaining actions and the same seed
    assert the final state matches the original
```

A snapshot that can't resume identically means the schema is missing a field. This test
finds it precisely.

---

## 3. Fork

### Requirement

> Clone a mid-game state, play N different continuations from it, and each is unaffected by
> the others.

If serialization is correct, fork is `deserialize(serialize(s))` — nearly free. Two things
to get right:

- **No shared mutable references** between the clone and the original. Deep copy, or make game objects immutable.
- **RNG divergence**: forked branches must either share the seed (for a controlled comparison) or take explicit distinct sub-seeds (for Monte Carlo rollouts). Document which, and expose the choice.

Report in `rng/RNG.md`: whether fork is supported, how, and the approximate cost of one
clone (microseconds? milliseconds?). That number sets how deep a search agent can go, so
it is genuinely load-bearing for the receiving team.

### Why it matters

Forward search — enumerating candidate action sequences and simulating each — is the
strongest cheap method for turn-based card games, and it is entirely gated on fork. The
reference result in this genre is a hand-written search agent with no machine learning
reaching a ~52% win rate on a commercial deckbuilder. None of that is possible without
state cloning.

---

## Report template for `rng/RNG.md`

```markdown
# RNG and determinism contract
Engine version:

## Sources of randomness
Number of independent generators: <should be 1>
Algorithm: <e.g. xoshiro256**, PCG32, Mersenne Twister>
Seeded at: <where> · Seed type: <int64?> · State serialized: yes/no

## Draw order
<the table above>

## Shuffle
Algorithm: · Draws consumed: · Direction/iteration order:

## Determinism killers present
Wall-clock:         none / <describe>
Thread scheduling:  none / <describe>
Hash iteration:     none / <describe>
Floating point:     none / <describe>

## Verification
Same-seed replay, 100 seeds, 2 clean processes: PASS / FAIL (<n> divergences)
Cross-platform:     PASS / FAIL / not tested
Serialize-resume at every action: PASS / FAIL

## Fork
Supported: yes/no · Mechanism: · Cost per clone: · Sub-seed policy:
```
