## 2026-04-12 - Added ARIA Labels to Icon-Only Buttons
**Learning:** Found an accessibility issue pattern specific to this app's components where icon-only buttons (like '⋯' for options, '❓' for help) lack textual descriptions.
**Action:** Next time, always check `button` elements that only contain icons or single-character emoji/symbols for missing `aria-label` attributes.
