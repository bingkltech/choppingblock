## 2026-04-12 - Added ARIA Labels to Icon-Only Buttons
**Learning:** Found an accessibility issue pattern specific to this app's components where icon-only buttons (like '⋯' for options, '❓' for help, and tab buttons with dynamic icons/labels) lack textual descriptions or screen-reader-specific labels.
**Action:** Next time, always check `button` elements that only contain icons, single-character emoji/symbols, or dynamically mapped content for missing `aria-label` attributes.
