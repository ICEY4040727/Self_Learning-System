---
name: Frontend Galgame UI implementation status
description: Tracks which Galgame UI phases are done and what's next — CSS visual polish, scene backgrounds, Home VN-ification
type: project
---

**Completed:** Phase 1-2 of Galgame UI (4-layer layout, DialogBox 4-mode state machine, HudBar, BacklogPanel, typewriter+click-advance+keyboard, SaveLoad)

**Next up:**
- Phase 3: #92 CharacterDisplay integration + expression switching (depends on #109 sprite upload API)
- Phase 4: #104 usability audit fixes
- Galgame visual guide (`docs/galgame_visual_guide.md`): Phase A (CSS polish — frosted glass, bounce animation, font size) → Phase B (scene backgrounds) → Phase C (Home page VN-ification) → Phase D (ambient effects)

**Why:** Functionality is complete but visuals still feel like a web app, not a Galgame. Reviewer recommends starting with Phase A (CSS-only changes, highest visual impact per line of code).

**How to apply:** When implementing UI changes, follow the Galgame visual guide phases. Use CSS variables from main.css. No JS animation libraries (pure CSS). No bright/pink themes (dark academy style).
