---
name: game-export
description: Export a card game for external AI testing by running inside the game's own codebase. Extracts the effect vocabulary and random call sites from the source, adds logging, records replay games, and produces a portable bundle. The code never leaves the repository - only extracted data the studio reviews.
---

# Export this game for external AI testing

You are running **inside the studio's own repository**. An outside team wants to rebuild this
game as a headless simulator so they can run AI agents against it in isolation.

**The code never leaves.** You read it; you emit data. Everything you produce goes in a
`bundle/` directory the studio reviews before sending.

That constraint shapes the whole job: the outside team cannot read the source, so anything
that requires reading it has to be extracted here. The good news is that most of it is
**extraction, not authorship** — mechanical, scriptable, and fast even on a very large
codebase.

---

## Step 0 — Report the shape of the codebase before extracting anything

Find and report, with file paths:

| | |
|---|---|
| **Card / content definitions** | data files, a database, or one class per card |
| **Effect / ability system** | how card behavior is expressed |
| **Turn loop** | phases, priority, the state machine |
| **Game state** | what holds the truth |
| **Random call sites** | every place the game draws randomness |
| **Match setup** | deck construction, mulligan, first player, starting resources |

Stop and show this before writing anything. If the studio disagrees with your read of the
architecture, now is when it is cheap to fix.

---

## Step 1 — Extract the effect vocabulary, and measure its shape

This measurement decides the whole approach, and it takes minutes. **Do it before anything
else.**

Count how card behavior is expressed. The method depends on the codebase:

```bash
# Cards defined in a text/data DSL — count the operation names
grep -rhoE '\b(SP|AB|DB)\$ *\w+' cards/ | sort | uniq -c | sort -rn

# Cards defined as code — the effect CLASS names are the vocabulary
grep -rhoE 'new (\w*Effect)\(' src/cards/ | sort | uniq -c | sort -rn

# Cards defined as scripts — the API functions they call
grep -rhoE '\b(Card|Duel|Effect)\.\w+' scripts/ | sort | uniq -c | sort -rn
```

Then report three numbers:

```
distinct operations             : N
operations covering 80% of uses : M
operations used by <=2 cards    : T  (as a % of N)
```

### What the numbers mean — this is the fork in the road

| Shape | Looks like | What follows |
|---|---|---|
| **Concentrated** | a handful of operations cover 80%; small tail | A reusable vocabulary exists. Extract it as a list of operations with their parameters, and most cards become data. |
| **Diffuse** | hundreds of operations needed for 80%; most of the vocabulary used by one or two cards | **There is no vocabulary to extract.** Do not try to build a DSL — you will be writing a catalogue of one-offs. Ship the card catalogue plus the exact rules text, and let the replays specify per-card behavior. |

Measured on two real engines to calibrate: a text-DSL engine needed **24 operations for 80%**
with a **15% tail** (concentrated); a code-per-card engine of similar size needed **2,083 for
80%** with a **92% tail** (diffuse). Same genre, same scale, opposite answers. Assuming the
wrong one wastes weeks.

**If diffuse, say so loudly in your report.** It means the outside team needs far more
replays, because each card's behavior is pinned only by replays that exercise it. That is a
conversation to have before anyone commits.

Whichever shape you find, emit `bundle/effects.md`: the operation list with counts, their
parameters, and the selector/targeting vocabulary. Counts matter — they tell the other side
what to implement first.

---

## Step 2 — Export the content data, as it exists

Copy the card/content data files into `bundle/content/` **untransformed**. If it is one messy
file, copy the messy file. Normalizing it is the other side's problem, and your normalization
would lose information they need.

If cards are classes rather than data, extract one record per card: stable id, cost, type,
stats, the keywords it uses, the exact in-game rules text, and the operations it invokes.
Do not paste source code — emit the structured summary.

---

## Step 3 — Log the randomness

Every random decision, appended in draw order, to `bundle/replays/*.json`:

```json
{"seq": 0, "where": "dealer.shuffle",      "kind": "permutation", "result": [21, 23, 22, 4]}
{"seq": 1, "where": "card.bolt.damage",    "kind": "int",  "range": [1, 3], "result": 2}
{"seq": 2, "where": "card.hex.proc",       "kind": "bool", "p": 0.3,        "result": false}
```

**You do not need a seedable or single-source RNG, and you do not need reproducibility.**
Keep calling `Math.random()` wherever you already do. The rebuilt engine replays these
outcomes instead of generating its own, so your shuffle algorithm and draw order stop
mattering.

Four details, each of which was learned the hard way:

- **`result` must use stable, serializable identifiers** — card ids, or indices into the input. Never object references or `repr()` output. Dumping a shuffled deck with a default serializer yields `"<Card object at 0x7a3e...>"`, which differs every run and means nothing to anyone else.
- **`where`** — any stable label. When the rebuild drifts, this names the exact decision point where control flow parted, which beats a mismatched end state. Deriving it from the call stack costs nothing and needs no edits to game code.
- **`range` / `p`** — the distribution, not just the outcome. A recorded `2` sits inside both `[1,3]` and `[1,4]`, so without this a rebuild reproduces every replay perfectly and then generates out-of-distribution games once an agent plays. Every automated check passes and nobody notices.
- **For `choice`, declare the option order.** A recorded choice is ambiguous otherwise.

Practically: wrap the random calls in a logging helper, or monkeypatch the RNG in a debug
build. **Missing a call site is recoverable**: the rebuilt engine runs out of log entries at a
precise point and names the site it expected.

### Cheaper alternative: skip this step and dump full state instead

If instrumenting the random call sites is awkward — scattered calls, a language that makes
wrapping painful, nobody who knows where they all are — **you can skip step 3 entirely** and
instead emit a **complete** state dump after *every* action in step 4. Complete means every
zone in order, including deck order.

That works because the state after a shuffle *is* the shuffle result. The receiving team then
validates one transition at a time: restore from dump N, apply action N, compare to dump N+1.

Measured on a real engine, 869 transitions, no random log at all:

| | Transitions matching |
|---|---|
| Correct rebuild | **98.5%** — the 1.5% residue is exactly the transitions that consume randomness |
| Rebuild with one planted bug | 93.1% — and all 47 extra mismatches named the single wrong field |

So the signal is clean and the noise is small, attributable, and useful: **the residue
identifies your random call sites for you**, which is the step you just skipped.

What you give up by taking this path:

- **Distributions.** Dumps show realized values, never the range they came from. A rebuild cannot learn that a roll is 1–3 rather than 1–4, so the games it *generates* for agent training may be out of distribution even though every transition validates. If you take this path, list the distributions separately — a one-line note per random site is enough.
- **Whole-game replay.** Single-step validation cannot confirm that a full recorded game comes out the same end to end, so compounding errors over a long game go unchecked.

Both are real losses, and this path is still worth it when the alternative is not getting a
bundle at all. **Full state dumps plus a short list of distributions is close to as good as
the random log, and usually much less work.**

---

## Step 4 — Record replays, and derive the coverage tags

**40 games** minimum, more if step 1 came out diffuse. Any play quality — a scripted bot,
random legal moves, the existing test harness.

Per game: setup, the `random_log`, the ordered action list, and — if a state serializer
exists — a state dump at the start, after each turn, and at the end. Dumps are optional but
they are what lets a divergence be located to the action that caused it.

### Tag each replay from what actually happened, never from what you expect

Derive tags by instrumenting the recorder. **Do not assign them by rule.**

This is not pedantry. In a test of this kit, an exporter tagged every seventh game
`deck_reshuffle` by arithmetic. Not one of the twenty games ever reshuffled. A bug planted
inside the reshuffle path then passed all twenty replays — while the bundle advertised
coverage of exactly that mechanic. **A fabricated tag converts missing coverage into false
confidence.**

The `random_log` makes this free: the set of `where` labels a replay contains *is* the set of
random code paths it exercised.

Deliberately seek out: each deck or archetype, each win condition (including deck-out,
timeout and draws), **the branches that are hard to reach** — reshuffles, empty decks, maximum
board or hand states — simultaneous triggers, and the cards whose logic you would warn a new
hire about. Random play alone will not reach these, and those are exactly the paths a rebuild
gets wrong.

---

## Step 5 — Write down only what cannot be extracted

`bundle/rules.md`. Short. The extraction covered the mechanical parts; this covers what
reading alone can answer:

1. **Resolution order when several triggers fire at once.** The single most common cause of a
   wrong rebuild. Stack, queue, or active-player-first? Is it deterministic? Describe the
   behavior the code **implements**, and say so if it differs from design intent.
2. Turn structure and phases, briefly.
3. Every win, loss and draw condition — including simultaneous death.
4. Zones: ordered or not, limits, overflow, who can see what.
5. Timing edge cases: death mid-resolution, zone change mid-resolution, effects referencing
   removed objects.

Then `bundle/NOTES.md`:

- Known bugs the rebuild must reproduce — the replays depend on them, so hiding them produces a clone that silently disagrees
- Intentional quirks that look like bugs
- **Anything you could not determine from the code** — flagged, never guessed. A wrong spec is far worse than a missing one, because it produces a clone that is confidently wrong.
- Cards whose behavior resists description, listed by id
- Deliberately out of scope

---

## Step 6 — Scope, privacy, validate

Unreleased content can be **renamed**: `"Dragonlord Ignis"` → `"card_4471"`, art and flavor
dropped, cost and behavior kept exactly. Behavior is what matters; names are not.

**Never put in the bundle:** source code, credentials, server endpoints, keys, player data,
telemetry, anti-cheat logic, matchmaking internals, pack odds or drop rates. Grep the finished
bundle for `api_key|secret|token|password|https?://` and review every match by hand.

Then validate:

```bash
python3 validate_bundle.py bundle/
```

Standard library only, nothing to install. Errors block; warnings advise. Fix the errors and
re-run until it exits 0.

---

## Step 7 — Report to the studio

```
VOCABULARY : N distinct ops · M cover 80% · T% tail  ->  CONCENTRATED / DIFFUSE
CARDS      : total · how behavior is expressed · how many resist description
RANDOM     : sites logged · sites still unlogged · sites with no declared distribution
REPLAYS    : count · coverage tags DERIVED from the runs · branches never reached
STATE      : serializer available? dumps included?
RULES      : resolution order documented? differs from design intent?
UNRESOLVED : what we could not determine from the code
NOT SENT   : what was held back and why
```

Be explicit about what the receiving team will **not** be able to reproduce. That sentence is
worth more than a larger bundle.

---

## What the studio gets out of this

Every artifact here is foundational tooling, not a favor:

| Produced | Keeps paying for itself as |
|---|---|
| Random logging | Reproducible bug reports: replay the exact game instead of "it happened once" |
| Replay corpus | A regression suite: change a card, replay 500 games, see precisely what moved |
| Extracted effect vocabulary | A balance dashboard, and an honest map of how much one-off logic the codebase carries |
| The coverage measurement | Which code paths the existing tests never reach |

Plus, from the receiving side: balance findings from an agent playing 100,000 games, and the
bugs found while rebuilding the rules engine from the extracted spec — which is the most
thorough review that engine will ever get.
