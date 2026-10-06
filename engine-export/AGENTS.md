# Agent instructions — Engine Export Kit

If you have been asked to export this game for AI testing, produce a headless simulator
spec, make the game reproducible for agent training, or generate golden replays:

**Follow the procedure in `SKILL.md` in this directory.** It is agent-agnostic — ignore
the YAML frontmatter if your tool doesn't use it.

Reference material, read on demand:

| File | When |
|---|---|
| `README.md` | Tiers, bundle layout, what not to send |
| `reference/01-export-spec.md` | The specification of every bundle file |
| `reference/02-effect-dsl.md` | How to express card powers |
| `reference/03-determinism.md` | The RNG, state and fork contract |
| `reference/04-golden-replays.md` | The validation protocol |
| `reference/05-privacy-and-tiers.md` | What to hold back and how to anonymize |
| `CHECKLIST.md` | Acceptance criteria |

Three rules that override convenience: **never put source code or secrets in the bundle**,
**never guess at game behavior** (write it to `NOTES.md` as unresolved instead), and
**never ship without verified golden replays**.
