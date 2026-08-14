# Streamlit Design Modernization Specification

**Status:** Implemented and validated

**Scope:** Presentation and layout only

**Functional changes permitted:** None

**Validation record (2026-08-14):** 155 tests passed; all five pages and
Buy/Sell/Transfer states were rendered at desktop, tablet, and phone widths;
the functional-diff audit found no changes to calculations, persistence,
schemas, widget keys, validation rules, session-state behavior, or data files.

## 1. Objective

Modernize the Streamlit application's visual design, information hierarchy,
responsive behavior, and presentation consistency while preserving every
existing workflow and result.

This project is a design refactor. It must not alter portfolio calculations,
validation rules, persistence, database schema, transaction semantics, widget
meaning, supported actions, or the data shown to the user.

## 2. Non-Negotiable Functional Boundary

The implementation must preserve all existing behavior, including:

- The optional application-password gate.
- Supabase as the production source of truth and CSV as the fallback/test
  implementation.
- Existing page names and navigation destinations.
- Existing Buy, Sell, and Transfer behavior. Transfer must continue to record
  history without moving holdings; this project must not complete or redefine
  transfers.
- Existing symbol resolution and Yahoo Finance lookup behavior.
- Existing calculations, formulas, rounding, stored financial fields, and
  displayed values.
- Existing validation rules and error/success messages.
- Existing preview-versus-process behavior.
- Existing session-state reset and retention behavior.
- Existing consolidated-record edit, replace, and delete behavior.
- Existing trade deletion and holdings rebuild behavior.
- Existing filters and their values.
- Existing charts, chart data, timeframes, and market-data requests.
- Existing table columns, CSV download support, and underlying data.

Do not modify the public `DataManager` interface, either persistence backend,
`TradeCalculator`, Supabase setup, table schemas, or data files.

If a desired visual improvement would require changing functionality, omit it
and document it as a future recommendation instead.

## 3. Allowed Implementation Surface

Changes should be limited to:

- Streamlit layout composition in `app.py`.
- Presentation-only helpers in `utils/ui_helpers.py`.
- CSS and theme configuration.
- Display labels or supporting descriptive copy only when the meaning remains
  identical and existing test expectations are preserved or deliberately
  updated for presentation-only wording.
- New pure presentation helpers that do not read or write persistence and do
  not calculate portfolio values.
- Tests that validate rendering, layout structure, and preservation of
  behavior.

Refactoring page rendering into presentation functions is allowed only if it
does not change execution order, widget keys, state semantics, or data access.

## 4. Design Direction

Use a restrained financial-dashboard aesthetic:

- Neutral dark surfaces that work with Streamlit's current dark theme.
- One blue/indigo brand accent for primary actions and selection states.
- Emerald only for positive values or confirmed success.
- Red only for destructive actions, errors, or negative values.
- Subtle borders, moderate corner radii, and limited shadows.
- Clear typographic hierarchy with compact supporting copy.
- Consistent spacing based on an 8px rhythm.
- Tabular numerals where practical for financial values.

Avoid gradients, glassmorphism, oversized emojis, ornamental animation, or
styles that obscure native focus and accessibility states.

## 5. Global Application Shell

### Requirements

- Retain the sidebar and existing navigation selectbox behavior.
- Improve the sidebar's visual hierarchy with a compact brand treatment and
  short supporting label.
- Reduce excess page-top whitespace.
- Apply a consistent maximum content width while allowing tables and charts to
  use the available screen.
- Create reusable presentation styles for:
  - Page headers and subtitles.
  - Section headers.
  - Metric groups.
  - Form panels.
  - Informational callouts.
  - Primary, secondary, and destructive buttons.
- Preserve visible keyboard focus indicators.
- Hide Streamlit's deployment chrome only if this can be done safely without
  hiding application controls.

### Button semantics

- Normal submit/process actions use the brand primary color.
- Preview actions use a neutral secondary treatment.
- Delete actions use red.
- Do not target buttons by `:first-child`, `:last-child`, or column position.
- Button styling must use stable Streamlit attributes, explicit wrappers, or
  narrow selectors that cannot recolor unrelated buttons.

## 6. Consolidated Record Page

### Requirements

- Preserve the page title and explanatory text.
- Present the four existing metrics as a cohesive responsive metric group.
- Do not change the values or rename "Total Value" in this implementation.
- Present filters in a compact, visually grouped filter panel.
- Preserve the table, column order, row numbering, formatting, download,
  search, and fullscreen behavior.
- Keep the modification controls below the table.
- Place the modification controls in a clearly differentiated management
  panel so they do not compete with the portfolio summary.
- Preserve the record selector, edit form, confirmation checkbox, and delete
  action exactly.
- Style Save Changes as primary and Delete Record as destructive.

## 7. Trade Entry Page

### Requirements

- Preserve the Trade Type selectbox and its Buy/Sell/Transfer options.
- Visually group account and security selection as the first section.
- Present date, quantity, price, and commission in a balanced responsive grid.
- Preserve every widget key, default, constraint, and immediate rerun behavior.
- Keep the holding summary directly associated with the stock selection.
- Preserve Preview Trade and Process Trade placement and behavior.
- Style Preview Trade as secondary and Process Trade as primary.
- Present existing preview metrics in a bordered summary panel without
  changing their labels, values, number, or order.
- Preserve all validation, spinners, success handling, and form reset behavior.
- Do not add a destination account or otherwise alter Transfer.

## 8. Pre-populate Database Page

### Requirements

- Preserve the page name and all current field labels.
- Present the fields in a balanced responsive panel.
- Keep the resolved holding summary beneath the related inputs.
- Style Add Holding as a normal primary action, never as destructive.
- Preserve validation, calculated cost-per-share display, success handling,
  persistence behavior, and reset behavior.

## 9. Trade History Page

### Requirements

- Preserve all three filters and their current behavior.
- Present filters in a compact responsive filter panel.
- Preserve the table, all displayed financial columns, formatting, download,
  search, and fullscreen behavior.
- Preserve the current order of the table, Delete Trade section, and Summary
  section. Moving these sections is out of scope because this specification is
  strictly non-functional.
- Visually distinguish the Delete Trade panel as destructive while keeping the
  existing selection and rebuild explanation.
- Preserve the selected-trade description, delete behavior, spinner, and
  messages.
- Present the three summary metrics as a consistent responsive metric group.

## 10. Stock Charts Page

### Requirements

- Preserve symbol and timeframe selectors and their options.
- Preserve all current calculations and the current first-matching-row
  behavior; aggregation changes are out of scope.
- Preserve Yahoo Finance calls, cache behavior, price and volume charts, stock
  information, portfolio overview, and allocation pie chart.
- Apply a cohesive presentation to the selector toolbar, metric groups, and
  section spacing.
- Update chart colors, typography, margins, grid lines, and Plotly mode-bar
  presentation only. Do not change chart types, traces, data, hover values, or
  timeframes.
- Ensure chart titles and financial values remain legible in dark mode.

## 11. Responsive Requirements

Validate at minimum at approximately 1440px, 1024px, and 390px viewport widths.

- No page heading or explanatory text may be clipped by the sidebar.
- At narrow widths, the sidebar must start collapsed or otherwise leave the
  main content readable using supported Streamlit configuration/CSS.
- Metric groups must wrap or stack without clipping values.
- Form columns must stack cleanly on narrow screens.
- Filter controls must remain usable without label collisions.
- Horizontal scrolling is acceptable inside wide dataframes, but the page
  itself must not develop unintended horizontal overflow.
- Buttons must remain large enough to identify and activate.
- Charts must remain contained within the content area.

## 12. Accessibility Requirements

- Maintain sufficient contrast for text, controls, borders, and status colors.
- Do not remove focus outlines.
- Do not communicate meaning through color alone.
- Preserve native labels and accessible names for every widget.
- Avoid CSS that changes the DOM's semantic order.
- Respect reduced-motion preferences; no new motion is required.

## 13. Implementation Constraints

- Preserve all existing user changes and unrelated worktree files.
- Do not edit files under `data/`.
- Do not add a frontend framework or replace Streamlit.
- Prefer a centralized CSS system and small pure presentation helpers over
  repeated inline styles.
- Avoid brittle selectors tied to column position or generated class names
  when stable `data-testid` or semantic attributes exist.
- The application must continue to start with the existing dependencies.
- New dependencies require explicit justification and should be avoided.

## 14. Required Validation Gate

Implementation is not complete until every step below passes.

### A. Automated regression validation

1. Run the entire test suite.
2. All existing tests must pass.
3. Add focused tests for any new pure presentation helper.
4. Confirm that no test was deleted, skipped, weakened, or rewritten to hide a
   functional regression.

Expected baseline at specification time: **154 tests passing**.

### B. Functional-diff audit

Review the final diff and explicitly confirm:

- No changes to `utils/calculations.py`.
- No changes to `utils/data_manager.py`.
- No changes to `utils/supabase_data_manager.py`.
- No changes to `utils/data_manager_factory.py`.
- No changes to Supabase schema/setup scripts.
- No changes to files under `data/`.
- No changed widget keys, validation conditions, formulas, persistence calls,
  session-state transitions, or action order.

If any item changed, revert it or explain why it is presentation-only before
declaring completion.

### C. Rendered desktop validation

Run the app locally with the CSV backend and visually inspect all five pages at
approximately 1440px and 1024px widths:

1. Consolidated Record with populated data.
2. Trade Entry in Buy, Sell, and Transfer states.
3. Buy and Sell preview states without processing a trade.
4. Pre-populate Database.
5. Trade History.
6. Stock Charts with a valid symbol when Yahoo Finance is available.

Verify layout, spacing, text clipping, button semantics, table containment,
dark-theme legibility, and absence of runtime exceptions.

### D. Rendered narrow-screen validation

Inspect at approximately 390px width and confirm:

- Main content is readable and not covered by the sidebar.
- Forms and filters stack cleanly.
- Metric values are not clipped.
- The page does not horizontally overflow outside intentional dataframe
  scrolling.

### E. Final report

The implementer must provide:

- Files changed.
- A concise list of visual changes.
- Full test result.
- Desktop and narrow-screen validation results.
- Confirmation that the functional-diff audit passed.
- Any design requirement that could not be safely achieved without functional
  changes.

## 15. Acceptance Criteria

The work is accepted when:

- The application has a cohesive modern financial-dashboard appearance.
- Every existing page and action remains present and behaves identically.
- Primary, secondary, and destructive actions are visually consistent.
- The accidental column-position button styling is removed.
- Desktop and narrow-screen layouts pass the required rendered checks.
- The complete automated test suite passes.
- The functional-diff audit finds no functionality or persistence changes.
