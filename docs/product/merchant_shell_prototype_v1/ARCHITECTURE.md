# Architecture

## Layers

| Layer | Desktop | Mobile ≤1023 |
|-------|---------|--------------|
| UtilityRow | Brand + account | Brand + account + utility menu |
| GlobalUpbar | Inline destinations | Same destinations, horizontal scroll |
| ContextualSidebar | In-flow column | Off-canvas; closed = edge handle on Page Stage |
| PageStage | Placeholder blocks | Placeholder blocks |

## Single registries (prototype-local)

- `GLOBAL[]` — platform destinations
- `CONTEXTUAL{}` — Home: نظرة عامة، الملخص · Workspace: ما يحتاج قرارك

No duplicate destination lists. Account drawer does not host Global destinations.
