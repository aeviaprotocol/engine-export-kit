# The two-phase protocol

**Last verified: 2026-10-06**

Working with a studio has two phases with different costs, different commitments, and
different things they make possible. Running them in order is what keeps the first
conversation cheap.

```
  PHASE 1 — qualify                        PHASE 2 — play
  ──────────────────────                   ──────────────────────
  They run ASK.md in their repo            They integrate our SDK
  We get: content data, effect             We get: a live connection to
  vocabulary, rules, replays               THEIR engine, driven by agents

  Cost to them:  hours                     Cost to them:  days
  Commitment:    none                      Commitment:    a dependency in their build
  Fidelity:      our rebuild may drift     Fidelity:      exact, by construction
  Throughput:    high (we own the sim)      Throughput:    one real-time instance
  ──────────────────────                   ──────────────────────
            └──────── the gate ────────────┘
```

**Neither phase replaces the other.** They enable different methods, and the honest reason
to do both is below.

---

## Phase 1 — qualify

`ASK.md`, run by their coding agent inside their own repository. The source never leaves.
Output is a bundle: content data as it exists, the extracted effect vocabulary, the rules
that only reading can establish, and recorded games.

What it buys us, in order of value:

1. **The vocabulary-shape measurement** (step 1). Decides whether this game can be rebuilt at all, in minutes.
2. **Enough to build agents against** — action space, card data, rules. Needed in Phase 2 as well, so it is never wasted work.
3. **Replays as a regression corpus** — useful for a rebuild *and* as the smoke test for a Phase 2 integration.
4. **A real signal about the studio.** A team that completes Phase 1 will complete Phase 2. One that stalls on it was never going to integrate an SDK.

Phase 1 is also the only phase that works when the studio will not add a dependency to
their build, which is a normal and reasonable position early on.

---

## The gate: what Phase 1 tells us

The measurement from `ASK.md` step 1 is the decision.

| Measurement | Means | Then |
|---|---|---|
| **Concentrated** — a handful of operations cover 80% of card behavior, small tail | A reusable vocabulary exists. Most cards become data. | A faithful rebuild is realistic. Phase 2 becomes an upgrade, not a necessity. |
| **Diffuse** — hundreds of operations for 80%, most of the vocabulary used by one or two cards | There is no vocabulary. Per-card behavior is pinned only by the replays that exercise it. | **A faithful rebuild needs an impractical number of replays. Go to Phase 2.** |

Calibration from two real engines of comparable size, same genre:

| | Cards | Ops for 80% | Tail | Verdict |
|---|---|---|---|---|
| Forge — cards in a text DSL | 34,074 | 24 | 15% | Concentrated |
| XMage — one class per card | 32,498 | 2,083 | 92% | Diffuse |

**A new game built by a small team is more likely to look like XMage than Forge**, because a
card DSL is something you build only once the collection gets large. So expect the gate to
point at Phase 2 more often than not — and be glad the measurement is five minutes rather
than five weeks of discovering it the hard way.

---

## Phase 2 — the playable SDK

They integrate a small library. Our agent connects and plays their actual engine.

**Not yet built.** Its interface should be designed against a real Phase 1 bundle, not
invented in advance. What is already settled:

### Shape

An inversion of the usual wrapper. Instead of us wrapping their game, **they expose an
endpoint and we drive it**:

```
new_match(config)            -> match handle
observe(player)              -> what that player can legally see
legal_actions(player)        -> the actions they may take
apply_action(player, action)
is_over() / outcome()

snapshot() / restore(s)      -- optional, and worth a lot: it unlocks search agents
```

That is the Gymnasium/PettingZoo contract, turned around. Do not invent a different one.

### Transport

A local socket or stdio with JSON, **not a binary dependency**. Language-agnostic, trivial to
implement from C#, C++, Java or anything else, and it keeps the studio in control of their own
process.

Precedent worth pointing at: `bottled_ai` plays a commercial deckbuilder through a community
mod over stdio, as an external process with a 10-second budget per decision, and reaches a
~52% win rate. For a turn-based card game a socket is comfortably fast enough.

### What it gives the studio

This is the part that makes integration worth their time, and it should lead the pitch:

- **A playtest bot.** Agents that play thousands of games against their current balance.
- **An AI opponent** they can ship, if ours is good enough.
- **Replay recording for free** — the SDK records as a byproduct, so Phase 1's manual work never has to be repeated.
- **Balance findings.** 100,000 games surfaces degenerate lines no playtester reaches.

### What it does not give us

**Throughput.** One real-time instance is roughly 10–100 games per minute. That is plenty for
LLM-agent evaluation, which is latency-bound anyway, and for playtesting. It is nowhere near
enough for reinforcement learning from scratch, which wants 10⁶+ steps per second
(`framework/01-taxonomy.md` A6, `framework/07-limitations.md` L7).

---

## Why both, and not just Phase 2

The two phases produce tools suited to different methods. This is the part that is easy to get
wrong by assuming the SDK makes the rebuild pointless.

| | Phase 2: SDK on their engine | Phase 1: our rebuilt simulator |
|---|---|---|
| Fidelity | exact | measured, imperfect (`packs/<game>/fidelity.md`) |
| Throughput | one real-time instance | parallel, faster than real time |
| Fork / snapshot | only if they expose it | ours by construction |
| Methods it serves | M8 LLM agents, M1 search (if snapshot), evaluation, playtesting | M5 RL from scratch, M3 self-play, large-scale search |
| Runs without them | no | yes |

So: **Phase 2 for anything where being exactly right matters.** Phase 1's simulator for
anything that needs volume. An agent trained at volume on the rebuilt simulator, then
evaluated through the SDK on the real engine, is the combination that uses both for what each
is good at — and the fidelity report is what tells you whether that transfer is trustworthy.

---

## Sequencing with a studio

1. Send `ASK.md`. One file, hours of their time, no commitment.
2. Read the gate. Report back what we found — including the vocabulary measurement, which is genuinely useful to them regardless, since it quantifies how much one-off logic their codebase carries.
3. If concentrated: build the simulator, show them agent results, and propose the SDK as the way to make those results exact.
4. If diffuse: say so plainly, skip the rebuild, and propose the SDK as the only path that works. The Phase 1 bundle is still the foundation for the agents.
5. Either way, lead the SDK pitch with the playtest bot. It is a thing they want; our agent evaluation is the side effect.
