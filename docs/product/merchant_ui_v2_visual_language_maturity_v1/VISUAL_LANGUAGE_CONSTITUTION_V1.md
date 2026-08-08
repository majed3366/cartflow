# CartFlow Visual Language Constitution V1

**Status:** Authoritative for Merchant UI V2+ visual surfaces (pending owner freeze)  
**Date (UTC):** 2026-08-08  
**Applies to:** Home, Decision Workspace, and all future V2 surfaces  
**Does not replace:** Product logic, APIs, or Merchant UI V2 architecture

---

## 1. Purpose

This constitution freezes the mature CartFlow visual vocabulary so identity is:

- distinctive
- coherent
- semantically meaningful
- recognizable without logo or color
- scalable across product surfaces

Architecture remains locked. This document locks **visual language**.

---

## 2. Canonical DNA (non-negotiable)

Every Commerce Object and micro-mark inherits:

1. **Open structural geometry** — mass with a controlled opening (not a closed badge circle)
2. **Controlled interruption** — measured gap / pin
3. **Central silence** — void that means unresolved meaning
4. **Tapered direction** — continuation has a thin→thick or thick→thin energy
5. **Asymmetric balance** — no mirrored ornament
6. **Densification** — confidence increases mass / alignment
7. **Recovery scoop** — bottom-open continuation after uncertainty
8. **Directional continuation** — routes terminate into action / wait / recovery

### Forbidden dialects

- Generic circles / dotted loading rings as identity
- Workflow node diagrams (equal connected circles)
- Chart widgets pretending to be Evidence
- Icon packs (Lucide/Material) as Commerce Objects
- Neon, AI glow, particle ambience
- Continuous looping dashboard motion
- Badges as the primary priority signal

---

## 3. Commerce Object family (canonical)

| Kind | Truth | Geometric idea |
|------|-------|----------------|
| `attention` | Merchant should look here | Open-C frame + directional wedge |
| `ev-sparse` | Few separated facts | Open frame + sparse staggered marks |
| `ev-gathering` | Facts accumulating | Marks increasing, still irregular |
| `ev-aligned` | Agreement forming | Parallel equal marks |
| `ev-converging` | Meaning consolidating | Marks compress toward navy mass |
| `insufficient` | Not enough to decide | Thin mute marks + open silence |
| `uncertainty` | Unknown cause / state | Open frame + central void |
| `meaning` | Interpretation consolidating | Open frame + consolidating bar |
| `decision-forming` | Decision not sealed | Partial mass fill |
| `decision-ready` | Decision densified | Sealed mass with remnant opening |
| `hesitation` | Almost / interrupt | Open frame + warm scarce break |
| `waiting` | External / not yet | Interrupted continuation dashes |
| `recovery-opportunity` | Recovery possible | Scoop |
| `recovery-continue` | Recovery advancing | Scoop + taper continuation |
| `return` | Customer return path | Scoop + return taper |
| `momentum` / `movement` | Commerce progression | Taper dash + tip |
| `complete` | Movement finished | Sealed mass + terminal |
| `blocked` | Progression stopped | Open frame + hard stop square |

**Rule:** Only render an object if Living Store / projection truth supports it.

### State transformation (one family)

```
Sparse → Gathering → Aligned → Converging → Decision Forming → Decision Ready → Continuation
```

States must feel related (shared open-frame DNA + progressive densification).

---

## 4. Evidence grammar

Field states (`.cf2-evfield[data-cf2-density]`):

| State | Meaning |
|-------|---------|
| `sparse` | Few, separated, open |
| `gathering` | Increasing concentration |
| `mixed` | Conflict / uneven agreement |
| `aligned` | Consistent parallel structure |
| `converging` | Dense, navy-weighted consolidation |
| `insufficient` | Mute, thin, honest emptiness |

Must remain distinct in grayscale.

---

## 5. Decision grammar

Tension on Decision Mass / route (`data-cf2-tension`):

| Tension | Meaning | Visual |
|---------|---------|--------|
| `open` | Not enough evidence | Light mass, thin mute anchor |
| `forming` / `low` / `high` | Forming / tension | Teal→navy gradient anchor |
| `waiting` | External dependency | Interrupted continuation |
| `ready` / `resolved` | Available / confirmed | Dense mass, strong anchor |

Merchant should distinguish these **before** reading copy.

---

## 6. Recovery grammar

| State | Object |
|-------|--------|
| Opportunity | `recovery-opportunity` |
| In progress / continuation | `recovery-continue` |
| Returned | `return` |
| Lost / blocked | `blocked` (+ insufficient when truthful) |

Never a generic success checkmark.

---

## 7. Commerce in Motion

### Static (required in screenshots)

Behaviors: gather, drift, converge, hesitate, interrupt, densify, resolve, continue, recover, complete  

Expressed via: density change, taper, progressive spacing, convergence, controlled breaks, asymmetry, continuation beyond decision.

### Runtime (optional, semantic only)

| Event | Motion |
|-------|--------|
| Evidence arrival | `.cf2-evfield.is-arriving` join (≤520ms) |
| Decision formation | `.cf2-dmass.is-forming` settle (≤640ms) |

### Motion governance

Calm · short · functional · interruptible · `prefers-reduced-motion` compatible.

No neon, ambient loops, particles, AI glow, continuous dashboard motion.

---

## 8. Attention Gravity

Priority controls: scale, proximity, density, contrast, surrounding silence, object relationships.

Badges are secondary metadata only.

---

## 9. Micro-grammar

Shared organism marks:

- Living Route taper spine + wash
- Route node terminals (evidence → decision mass → action tip)
- Evidence field align axis
- Decision mass anchor bar
- Action terminus clip continuation
- Momentum underline progression
- Silence / taper separators
- Capsule quiet secondary rail

---

## 10. Design System integration

Commerce Objects and Motion are **not** a parallel DS.

They plug into V2 surfaces: panels, actions, empty, loading, notifications, data views, mobile patterns — using the same DNA.

Loading must use CartFlow state grammar (waiting / gathering), never a generic spinner as identity.

---

## 11. Responsive simplification

Mobile may reduce glyph size and stacking density.

Identity and semantics must survive. Do not shrink desktop grammar into decorative noise.

---

## 12. Validation laws

- Grayscale + logo/wordmark hidden must still read as CartFlow structure
- Blind recognition must distinguish from analytics / fintech / AI SaaS / workflow / loaders / charts
- Real Living Store truth only — never fake evidence

---

## 13. Freeze statement

Until this constitution is amended by an explicit Visual Language task:

**No new object dialects. No decorative motion. No expansion of V2 to other sections without applying this grammar.**
