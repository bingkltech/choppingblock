## 2024-04-13 - Navigation Sync & A11y Polish
**Learning:** The horizontal and vertical navigations were decoupled and missing clear `aria-current` traits, making keyboard and screen reader usage less intuitive. Disconnected local component state was preventing the TopNavbar from actually changing main views.
**Action:** Next time ensuring global/shared state is properly passed to all duplicate/mirrored navigation components to keep the app's views in sync, and consistently applying `:focus-visible` to interactive elements.
