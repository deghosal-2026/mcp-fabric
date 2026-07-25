# UI Test Cases — Shared Components

> **Area:** Components  
> **Plan reference:** Layer 1 (38 tests)  
> **Test prefix:** `TC-SC`  
> **Last updated:** 2026-07-24

---

## 1. Badge

### TC-SC-001: Renders label text

**Description:** Verify the Badge component displays the provided label string as visible text content. This is the most basic rendering contract of the component.

**Severity:** Critical

**Preconditions:**
- Badge component imported and available

**Test Steps:**
1. Render `<Badge label="trusted" />`

**Expected Results:**
- The text "trusted" is visible in the rendered output
- `screen.getByText('trusted')` returns a non-null element
- The element has `toBeInTheDocument()` assertion passing

---

### TC-SC-002: Known variant applies correct color class

**Description:** Badge maps known variant/status strings to Tailwind color classes. Each known value must produce the correct background and text color combination so users can visually distinguish status at a glance.

**Severity:** Critical

**Preconditions:**
- Badge component imported

**Test Steps:**
1. Render `<Badge label="trusted" />`
2. Inspect the rendered span's className attribute

**Expected Results:**
- className contains both `bg-green-100` and `text-green-800`

**Full variant mapping (verify all):**

| Variant | Expected classes |
|---|---|
| `trusted` | `bg-green-100 text-green-800` |
| `restricted` | `bg-yellow-100 text-yellow-800` |
| `approval-gated` | `bg-orange-100 text-orange-800` |
| `unreviewed` | `bg-red-100 text-red-800` |
| `healthy` | `bg-green-100 text-green-800` |
| `degraded` | `bg-yellow-100 text-yellow-800` |
| `unhealthy` | `bg-red-100 text-red-800` |
| `active` | `bg-green-100 text-green-800` |
| `deprecated` | `bg-gray-100 text-gray-800` |
| `pending` | `bg-yellow-100 text-yellow-800` |
| `approved` | `bg-green-100 text-green-800` |
| `denied` | `bg-red-100 text-red-800` |
| `admin` | `bg-purple-100 text-purple-800` |
| `editor` | `bg-blue-100 text-blue-800` |
| `viewer` | `bg-gray-100 text-gray-800` |

**Test data note:** Test at least one from each color group (green, yellow, orange, red, purple, blue, gray) to validate distinct mappings exist.

---

### TC-SC-003: Unknown variant falls back to gray

**Description:** When the variant/label string does not match any known entry in the color map, the Badge must gracefully fall back to a neutral gray color scheme instead of rendering with no color or crashing.

**Severity:** Major

**Preconditions:**
- Badge component imported

**Test Steps:**
1. Render `<Badge label="some-custom-status-that-does-not-exist" />`
2. Inspect the rendered span's className

**Expected Results:**
- className contains `bg-gray-100`

---

### TC-SC-004: Variant prop overrides label for color

**Description:** The `variant` prop exists to separate display text from color logic. When `variant` is provided, the Badge should use `variant` to determine color while using `label` for the visible text. This allows displaying one text value while using a different status's color scheme.

**Severity:** Normal

**Preconditions:**
- Badge component imported

**Test Steps:**
1. Render `<Badge label="custom" variant="trusted" />`
2. Check visible text
3. Check className

**Expected Results:**
- Visible text is "custom" (from label prop), NOT "trusted"
- className contains `bg-green-100` (from variant prop lookup)

---

### TC-SC-005: Long label truncated

**Description:** Badge labels should not break page layout when they contain unusually long text. The component applies CSS truncation to cap visual width.

**Severity:** Normal

**Preconditions:**
- Badge component imported

**Test Steps:**
1. Render `<Badge label="this is a very long label that could potentially break the page layout" />`
2. Inspect className

**Expected Results:**
- className contains `truncate`
- className contains `max-w-[200px]`
- The label text is fully present in the DOM (accessible via `textContent` or `title`) but visually clipped

---

## 2. LoadingState

### TC-SC-006: Default renders 3 skeleton rows

**Description:** LoadingState shows animated placeholder shapes while content loads. When no row count is specified, it should default to 3 skeleton rows as a reasonable visual placeholder for most list/table views.

**Severity:** Critical

**Preconditions:**
- LoadingState component imported

**Test Steps:**
1. Render `<LoadingState />`
2. Count child elements in the container

**Expected Results:**
- The rendered container has exactly 3 child elements (rows)
- Each row element is present in the DOM

---

### TC-SC-007: Custom row count renders specified number

**Description:** Pages with different content densities need different numbers of skeleton rows. A detail view might need 5, a minimal panel might need 1. The `rows` prop must allow this.

**Severity:** Normal

**Preconditions:**
- LoadingState component imported

**Test Steps:**
1. Render `<LoadingState rows={5} />`
2. Count child elements
3. Render `<LoadingState rows={1} />`
4. Count child elements

**Expected Results:**
- First render: exactly 5 children
- Second render: exactly 1 child

---

### TC-SC-008: Pulse animation class present

**Description:** The visual animation effect on skeleton rows is achieved via Tailwind's `animate-pulse` utility. Verify this class is present so the loading state produces the expected animated visual feedback.

**Severity:** Normal

**Preconditions:**
- LoadingState component imported

**Test Steps:**
1. Render `<LoadingState />`
2. Inspect className of each child row

**Expected Results:**
- Every child element's className contains the string `animate-pulse`

---

## 3. ErrorState

### TC-SC-009: Renders error message text

**Description:** ErrorState communicates failure information to the user. The provided message must be displayed prominently so users understand what went wrong.

**Severity:** Critical

**Preconditions:**
- ErrorState component imported

**Test Steps:**
1. Render `<ErrorState message="Database connection failed" />`

**Expected Results:**
- The exact text "Database connection failed" is visible
- The message is rendered as a text node, not as HTML (no XSS vector — see security tests)

---

### TC-SC-010: Retry button fires onRetry callback

**Description:** ErrorState provides a "Retry" button that lets users attempt the failed operation again. The `onRetry` callback must be invoked exactly once per click.

**Severity:** Critical

**Preconditions:**
- Mock callback function created via `vi.fn()`

**Test Steps:**
1. Render `<ErrorState message="Failed to load" onRetry={mockCallback} />`
2. Find the retry button by its role (`button`)
3. Click the button

**Expected Results:**
- `mockCallback` is called exactly 1 time
- `mockCallback` is called with no arguments

---

### TC-SC-011: No retry button when onRetry omitted

**Description:** ErrorState can be used in read-only contexts where the user should not attempt retry (e.g., audit logs for a viewer role). When `onRetry` is not provided, no button should render.

**Severity:** Normal

**Preconditions:**
- ErrorState component imported

**Test Steps:**
1. Render `<ErrorState message="Access denied" />`
2. Query for any button element

**Expected Results:**
- `screen.queryByRole('button')` returns `null`
- The error message is still visible

---

## 4. EmptyState

### TC-SC-012: Renders message text

**Description:** EmptyState informs users when there is no data to display. The message must be clearly visible and understandable.

**Severity:** Critical

**Preconditions:**
- EmptyState component imported

**Test Steps:**
1. Render `<EmptyState message="No servers found" />`

**Expected Results:**
- The text "No servers found" is visible

---

### TC-SC-013: Action button fires onAction callback

**Description:** EmptyState can include a call-to-action button (e.g., "Register your first server") that takes users to the relevant action. This button must invoke the provided callback.

**Severity:** Normal

**Preconditions:**
- Mock callback created via `vi.fn()`

**Test Steps:**
1. Render `<EmptyState message="No servers" actionLabel="Add Server" onAction={mockCallback} />`
2. Find the action button by its text "Add Server"
3. Click the button

**Expected Results:**
- `mockCallback` is called exactly 1 time

---

### TC-SC-014: No action button when onAction omitted

**Description:** Some empty states are informational only (e.g., empty search results with no suggested action). In these cases, no button should render.

**Severity:** Minor

**Preconditions:**
- EmptyState component imported

**Test Steps:**
1. Render `<EmptyState message="No results" />`
2. Query for any button element

**Expected Results:**
- No button element is present

---

## 5. PageState

### TC-SC-015: Loading state shows skeleton

**Description:** PageState is a generic wrapper that handles the 3 core data-fetching states. When the query is loading, it must display skeleton placeholders, not the actual content.

**Severity:** Critical

**Preconditions:**
- Query object with `isLoading: true`, no error, no data

**Test Steps:**
1. Create query: `{ isLoading: true, data: undefined, error: null, refetch: vi.fn() }`
2. Render page with `<PageState query={query}>{data => <div>content</div>}</PageState>`
3. Check rendered output

**Expected Results:**
- Skeleton loading elements are visible (pulsing divs)
- The children callback content ("content") is NOT rendered

---

### TC-SC-016: Error state shows message and retry

**Description:** When the query encounters an error, PageState must display the error message and provide a retry mechanism.

**Severity:** Critical

**Preconditions:**
- Query object with error set, loading complete

**Test Steps:**
1. Create query: `{ isLoading: false, data: undefined, error: new Error('API timeout'), refetch: vi.fn() }`
2. Render with PageState
3. Check for error UI elements

**Expected Results:**
- The word "Error" is visible as a heading
- The error message "API timeout" is visible
- A retry button is present
- Clicking retry calls `query.refetch()`

---

### TC-SC-017: Empty state when data is null

**Description:** When the query completes successfully but returns no data (null or undefined), PageState must show an empty state rather than rendering children with null data.

**Severity:** Critical

**Preconditions:**
- Query object with no error, no data, loading complete

**Test Steps:**
1. Create query: `{ isLoading: false, data: null, error: null, refetch: vi.fn() }`
2. Render with PageState

**Expected Results:**
- "No data available" text is visible
- The children callback is NOT executed

---

### TC-SC-018: Renders children with populated data

**Description:** When all conditions are met (loaded, no error, data present), PageState must execute the children render function with the query data.

**Severity:** Critical

**Preconditions:**
- Query object with loaded data

**Test Steps:**
1. Create query: `{ isLoading: false, data: ['apple', 'banana'], error: null, refetch: vi.fn() }`
2. Render with PageState where children renders a list
3. Verify children were called with correct data

**Expected Results:**
- Children callback is executed
- The rendered content from children is visible
- Children received the data array `['apple', 'banana']`

---

### TC-SC-019: Transition from error to loading on refetch

**Description:** When the user clicks retry after an error, the state should transition back to loading to indicate the retry is in progress. This gives immediate visual feedback.

**Severity:** Normal

**Preconditions:**
- Query starts in error state

**Test Steps:**
1. Render with `query = { isLoading: false, error: new Error('fail'), ... }` — error state shows
2. Update query to `{ isLoading: true, error: null, ... }` — simulate retry

**Expected Results:**
- After step 1: error message visible
- After step 2: error message disappears, skeleton reappears

---

### TC-SC-020: Transition from loading to error

**Description:** When a fetch that was loading fails, the UI must transition cleanly from skeleton to error state without leaving stale loading elements.

**Severity:** Normal

**Preconditions:**
- Query starts in loading state

**Test Steps:**
1. Render with `query = { isLoading: true, ... }` — skeleton shows
2. Update query to `{ isLoading: false, error: new Error('timeout'), data: null, ... }`

**Expected Results:**
- After step 1: skeleton visible
- After step 2: error message and retry button replace the skeleton

---

## 6. Modal

### TC-SC-021: Renders nothing when closed

**Description:** When `open={false}`, the Modal must render nothing to the DOM. Rendering a hidden modal with CSS (`display: none`) is acceptable but testing-library queries should not find its content. The simplest and most reliable approach is conditional rendering (return null).

**Severity:** Critical

**Preconditions:**
- Modal component imported

**Test Steps:**
1. Render `<Modal open={false} onClose={vi.fn()} title="Edit Server"><p>Form fields</p></Modal>`
2. Query for any modal-related content

**Expected Results:**
- `screen.queryByText('Edit Server')` returns null
- `screen.queryByText('Form fields')` returns null

---

### TC-SC-022: Renders content when open

**Description:** When `open={true}`, the Modal must render its title and children content visible in the DOM. The title is rendered as an `<h2>` element.

**Severity:** Critical

**Preconditions:**
- Modal component imported

**Test Steps:**
1. Render `<Modal open={true} onClose={vi.fn()} title="Edit Server"><p>Form fields</p></Modal>`
2. Find the dialog content

**Expected Results:**
- Title "Edit Server" visible (rendered as `<h2>`)
- Child content "Form fields" visible
- Close button (×) visible

---

### TC-SC-023: Closes on Escape key

**Description:** Pressing the Escape keyboard key must close the modal by calling `onClose`. This is a critical accessibility requirement for keyboard users and a standard UX pattern.

**Severity:** Critical

**Preconditions:**
- Modal open with `onClose` spy

**Test Steps:**
1. Render `<Modal open={true} onClose={onCloseSpy} title="Test">Content</Modal>`
2. Simulate pressing the Escape key (`keyboard('{Escape}')` or dispatch `keydown` event with `key: 'Escape'`)

**Expected Results:**
- `onCloseSpy` is called exactly once

---

### TC-SC-024: Closes on overlay click

**Description:** Clicking the semi-transparent overlay background outside the modal content must close the modal. This is a standard dismiss pattern. The implementation must ensure that clicking the modal content itself does NOT close it (event target check).

**Severity:** Normal

**Preconditions:**
- Modal open with `onClose` spy
- Overlay element identified (the outermost `bg-black/50` div)

**Test Steps:**
1. Render Modal with `onClose` spy
2. Click on the overlay element (use `data-testid` to identify it, or click on the area outside the content panel)
3. Verify `onClose` was called

**Expected Results:**
- `onClose` called exactly once

---

### TC-SC-025: Click on modal content does not close

**Description:** The overlay click handler must check that the click target is the overlay itself, not a child element. Clicking inside the white modal panel should never close the dialog. This prevents accidental dismissal when interacting with form fields inside the modal.

**Severity:** Normal

**Preconditions:**
- Modal open with `onClose` spy

**Test Steps:**
1. Render `<Modal open={true} onClose={spy} title="Test"><input type="text" /></Modal>`
2. Click on the input field inside the modal content area
3. Verify `onClose` was NOT called

**Expected Results:**
- `onClose` is not called
- Modal remains open

---

### TC-SC-026: Confirm button disabled when confirmDisabled is true

**Description:** The Modal's confirm button must respect the `confirmDisabled` prop to prevent submission when required form fields are empty or validation fails. The disabled state must be visually and functionally applied.

**Severity:** Normal

**Preconditions:**
- Modal open with `onConfirm` spy

**Test Steps:**
1. Render `<Modal open={true} onConfirm={spy} confirmDisabled={true} confirmLabel="Save">...</Modal>`
2. Find the confirm button

**Expected Results:**
- Confirm button text is "Save"
- Button element has the `disabled` attribute set

---

### TC-SC-027: Confirm button not disabled when confirmDisabled is false

**Description:** When `confirmDisabled` is false or omitted, the confirm button must be enabled and clickable.

**Severity:** Normal

**Preconditions:**
- Modal open with `onConfirm` spy

**Test Steps:**
1. Render `<Modal open={true} onConfirm={spy} confirmLabel="Save">...</Modal>`
2. Find the confirm button
3. Click it

**Expected Results:**
- Confirm button does NOT have the `disabled` attribute
- Clicking the button calls `onConfirm`

---

### TC-SC-028: Loading state shows "Loading..." text

**Description:** When `loading={true}`, the confirm button should show a loading indicator ("Loading...") and be disabled to prevent double-submission while the async operation is in flight.

**Severity:** Normal

**Preconditions:**
- Modal open with loading mutation

**Test Steps:**
1. Render `<Modal open={true} onConfirm={spy} loading={true} confirmLabel="Save">...</Modal>`
2. Find confirm button

**Expected Results:**
- Button text is "Loading..." (not "Save")
- Button is disabled

---

## 7. ConfirmDialog

### TC-SC-029: ConfirmDialog renders with destructive styling

**Description:** ConfirmDialog wraps Modal with destructive confirmation actions (delete, deprecate, deactivate). The confirm button must use red (destructive) color to signal risk.

**Severity:** Normal

**Preconditions:**
- ConfirmDialog imported

**Test Steps:**
1. Render `<ConfirmDialog open={true} title="Delete Server" message="Are you sure?" onConfirm={vi.fn()} onClose={vi.fn()} />`

**Expected Results:**
- Title "Delete Server" visible
- Message "Are you sure?" visible
- Confirm button has `bg-red-500` class (destructive styling)
- Confirm button text defaults to "Delete"

---

### TC-SC-030: Cancel fires onClose

**Description:** Clicking Cancel in the ConfirmDialog must dismiss the dialog without executing the destructive action.

**Severity:** Critical

**Preconditions:**
- Mock callbacks for onConfirm and onClose

**Test Steps:**
1. Render ConfirmDialog with spies
2. Click the "Cancel" button

**Expected Results:**
- `onClose` called exactly once
- `onConfirm` is NOT called

---

### TC-SC-031: Confirm fires onConfirm

**Description:** Clicking the confirm/delete button must execute the destructive action callback.

**Severity:** Critical

**Preconditions:**
- Mock callbacks

**Test Steps:**
1. Render ConfirmDialog with spies
2. Click the confirm button (text: "Delete")

**Expected Results:**
- `onConfirm` called exactly once
- `onClose` is NOT called

---

### TC-SC-032: Custom confirmLabel renders

**Description:** The ConfirmDialog accept a custom `confirmLabel` prop to override the default "Delete" text for non-delete destructive actions (e.g., "Deprecate", "Deactivate").

**Severity:** Normal

**Preconditions:**
- ConfirmDialog imported

**Test Steps:**
1. Render `<ConfirmDialog open={true} title="Deprecate" message="Sure?" confirmLabel="Deprecate" onConfirm={vi.fn()} onClose={vi.fn()} />`

**Expected Results:**
- Confirm button text is "Deprecate"

---

## 8. Toast

### TC-SC-033: addToast renders message in the DOM

**Description:** Calling `addToast` from the Toast context must immediately render the toast message as a visible element in the DOM.

**Severity:** Critical

**Preconditions:**
- Component wrapped in `<ToastProvider>`

**Test Steps:**
1. Render a test component inside ToastProvider that calls `addToast('success', 'Server registered')`
2. Look for the toast message

**Expected Results:**
- The toast message "Server registered" is visible in the DOM
- The toast appears in the toast container (fixed bottom-right)

---

### TC-SC-034: Correct color per toast type

**Description:** Each toast type (success, error, info) must render with its corresponding color so users can quickly identify the nature of the notification.

**Severity:** Normal

**Preconditions:**
- ToastProvider wrapping test component

**Test Steps:**
1. Fire `addToast('success', 'Done')`
2. Inspect toast className
3. Repeat for `error` and `info` types

**Expected Results:**
- `success` toast has `bg-green-500`
- `error` toast has `bg-red-500`
- `info` toast has `bg-blue-500`

---

### TC-SC-035: Auto-dismiss after 5 seconds

**Description:** Toasts must automatically disappear after 5 seconds to prevent notification clutter. The dismiss timer must start from the moment the toast is created.

**Severity:** Normal

**Preconditions:**
- Spy on `setTimeout` or use fake timers via `vi.useFakeTimers()`

**Test Steps:**
1. Call `addToast('info', 'Temporary message')`
2. Check that a timer was scheduled

**Expected Results:**
- `setTimeout` was called with a callback and 5000ms duration
- After 5000ms elapse (using fake timers), the toast is removed from the DOM

---

### TC-SC-036: Multiple toasts stack

**Description:** When multiple toasts fire in quick succession, they should stack vertically in the display order without replacing each other.

**Severity:** Normal

**Preconditions:**
- ToastProvider wrapping test component

**Test Steps:**
1. Fire 3 toasts sequentially: `addToast('success', 'A')`, `addToast('error', 'B')`, `addToast('info', 'C')`

**Expected Results:**
- All 3 toasts (A, B, C) are visible simultaneously
- They are ordered in the container (newest at bottom or top, depending on design)
- Each has its own independent dismiss timer

---

### TC-SC-037: 50 rapid toasts all render without crash (benchmark)

**Description:** The toast system must handle high-frequency notifications without crashing or performance degradation. 50 rapid toasts in 100ms is an edge case that should not break the UI.

**Severity:** Minor (performance boundary)

**Preconditions:**
- ToastProvider wrapping test component

**Test Steps:**
1. Fire 50 toasts within 100ms (loop `addToast('info', 'msg-N')` 50 times)
2. Wait for all renders to settle

**Expected Results:**
- All 50 toast message elements are visible in the DOM
- No runtime errors or crashes
- Each toast has a unique identifier / message

---

### TC-SC-038: Each toast dismisses independently at 5s from creation

**Description:** Toast dismiss timers must be independent per toast. A toast created at t=2s must dismiss at t=7s, regardless of when other toasts were created. This prevents one early dismiss from removing all toasts.

**Severity:** Normal

**Preconditions:**
- Fake timers enabled (`vi.useFakeTimers()`)

**Test Steps:**
1. Call `addToast('info', 'First')` at t=0s
2. Advance timer to t=2s
3. Call `addToast('info', 'Second')` at t=2s
4. Advance timer to t=5s

**Expected Results:**
- At t=5s (3s after First was created, but 5s have elapsed for First): "First" toast is dismissed
- "Second" toast is still visible (only 3s have elapsed for Second)

**Test Steps continued:**
5. Advance timer to t=7s

**Expected Results:**
- At t=7s (5s after Second was created): "Second" toast is dismissed
- No toasts remain

---

## 9. Table

### TC-SC-039: Renders column headers from ColumnDef

**Description:** The Table component must render header text from the ColumnDef array. Each header is rendered in a `<th>` element inside `<thead>`.

**Severity:** Critical

**Preconditions:**
- Table component imported
- Column definitions with known headers

**Test Steps:**
1. Render `<Table data={[]} columns={[
  { header: 'Name', accessorKey: 'name' },
  { header: 'Status', accessorKey: 'status' }
]} />`

**Expected Results:**
- Text "Name" visible in the table header
- Text "Status" visible in the table header
- Headers are inside `<thead>` element

---

### TC-SC-040: Renders correct number of data rows

**Description:** The Table must render one `<tr>` per data item in the `data` array.

**Severity:** Critical

**Preconditions:**
- 3 data items provided

**Test Steps:**
1. Render Table with `data={[{ name: 'A', status: 'ok' }, { name: 'B', status: 'warn' }, { name: 'C', status: 'error' }]}`
2. Count rows in the table body

**Expected Results:**
- `<tbody>` contains exactly 3 `<tr>` elements
- Each row contains the correct cell data (accessorKey values)

---

### TC-SC-041: Row click fires onRowClick with row data

**Description:** When `onRowClick` is provided, clicking a row must invoke the callback with the clicked row's data. This supports navigation to detail views.

**Severity:** Normal

**Preconditions:**
- `onRowClick` spy

**Test Steps:**
1. Render Table with `onRowClick={spy}` and data items
2. Click the first row (use row text or testid)

**Expected Results:**
- `spy` is called exactly once
- The first argument is a Row object containing the first data item

---

### TC-SC-042: Pagination bar visible when pagination prop provided

**Description:** When `pagination` is provided, the table must show a pagination bar with total count and navigation controls.

**Severity:** Normal

**Preconditions:**
- Pagination object with total and hasMore

**Test Steps:**
1. Render Table with `pagination={{ total: 50, hasMore: true }}`

**Expected Results:**
- Text "Total: 50" is visible in the pagination bar
- "Next" button is visible (when hasMore is true and onNext is provided)
- "Previous" button is visible (when onPrev is provided — currently no pages implement this)

---

### TC-SC-043: No pagination bar when pagination prop omitted

**Description:** When not paginating (e.g., small lists), the table should not render a pagination bar.

**Severity:** Normal

**Preconditions:**
- Table rendered without pagination prop

**Test Steps:**
1. Render `<Table data={data} columns={columns} />` (no pagination prop)
2. Check for pagination-related text

**Expected Results:**
- No "Total:" text visible
- No pagination buttons visible

---

### TC-SC-044: Empty data renders headers only

**Description:** An empty data array must render the table headers with a zero-row body. No crash.

**Severity:** Normal

**Preconditions:**
- Table with `data={[]}`

**Test Steps:**
1. Render Table with empty data array

**Expected Results:**
- Headers render correctly
- `<tbody>` has 0 rows
- No runtime error or crash

---

### TC-SC-045: Single row renders correctly

**Description:** A single-item data array must render one row with correct cell values and pagination showing total=1.

**Severity:** Normal

**Preconditions:**
- Data array with 1 item

**Test Steps:**
1. Render Table with 1 data item

**Expected Results:**
- 1 row rendered
- Row contains the correct cell values

---

### TC-SC-046: Next button hidden when no more pages

**Description:** When `pagination.hasMore` is false, the "Next" button should not render (there's nowhere to navigate to).

**Severity:** Normal

**Preconditions:**
- Pagination with hasMore=false

**Test Steps:**
1. Render Table with `pagination={{ total: 5, hasMore: false }}`

**Expected Results:**
- No "Next" button visible

---

## 10. FilterBar

### TC-SC-047: Renders a select dropdown for each filter group

**Description:** FilterBar renders `<select>` elements for each filter group defined in the `filters` prop. Each select must display the group's label and contain option elements.

**Severity:** Critical

**Preconditions:**
- FilterBar imported
- Filter groups defined

**Test Steps:**
1. Render `<FilterBar filters={[{ key: 'status', label: 'Status', options: [{ value: 'active', label: 'Active' }] }]} onFilter={vi.fn()} />`

**Expected Results:**
- Label "Status" is visible
- A `<select>` element is present
- The select contains an `<option>` with value "active" and text "Active"

---

### TC-SC-048: Selecting a filter value fires onFilter

**Description:** Changing a filter dropdown's selected value must call `onFilter` with the filter key and selected value.

**Severity:** Critical

**Preconditions:**
- onFilter spy

**Test Steps:**
1. Render FilterBar with spy
2. Change the status dropdown to "Active"

**Expected Results:**
- `onFilter` is called with `{ status: 'active' }`

---

### TC-SC-049: Multiple filters combine correctly

**Description:** Setting filters on multiple dropdowns must merge them into a single filter object with all active filter keys.

**Severity:** Normal

**Preconditions:**
- Two filter groups: status and team
- onFilter spy

**Test Steps:**
1. Set status to "active"
2. Set team to "platform"

**Expected Results:**
- `onFilter` is called with `{ status: 'active', team: 'platform' }`

---

### TC-SC-050: Search input debounces at 300ms

**Description:** The search input uses a 300ms debounce to avoid firing API requests on every keystroke. The callback must only fire after the user stops typing for 300ms.

**Severity:** Normal

**Preconditions:**
- Fake timers enabled (`vi.useFakeTimers()`)
- FilterBar with `searchPlaceholder="Search..."`

**Test Steps:**
1. Type "abc" into the search input
2. Advance timer by 250ms

**Expected Results:**
- `onFilter` has NOT been called yet (within debounce window)

**Test Steps continued:**
3. Advance timer by another 100ms (total 350ms)

**Expected Results:**
- `onFilter` has been called with `{ search: 'abc' }`
- The debounce timer fired after the 300ms gap

---

### TC-SC-051: Clear all button resets all filters

**Description:** Clicking "Clear All" must reset all filter selections and call `onFilter` with an empty object.

**Severity:** Normal

**Preconditions:**
- FilterBar with active filters

**Test Steps:**
1. Set filter "status" to "active"
2. Click "Clear All" button

**Expected Results:**
- All dropdowns reset to their default (empty/unselected) state
- `onFilter` is called with `{}`

---

### TC-SC-052: Clear all with no active filters is no-op

**Description:** Clicking "Clear All" when no filters are active should still call `onFilter({})` but should not cause unnecessary side effects (e.g., multiple refetches).

**Severity:** Minor

**Preconditions:**
- No filters active (all defaults)

**Test Steps:**
1. Click "Clear All" immediately after render

**Expected Results:**
- `onFilter` called exactly once with `{}`

---

## Summary

| Prefix | Component | Test Count |
|---|---|---|
| TC-SC-001 to 005 | Badge | 5 |
| TC-SC-006 to 008 | LoadingState | 3 |
| TC-SC-009 to 011 | ErrorState | 3 |
| TC-SC-012 to 014 | EmptyState | 3 |
| TC-SC-015 to 020 | PageState | 6 |
| TC-SC-021 to 028 | Modal | 8 |
| TC-SC-029 to 032 | ConfirmDialog | 4 |
| TC-SC-033 to 038 | Toast | 6 |
| TC-SC-039 to 046 | Table | 8 |
| TC-SC-047 to 052 | FilterBar | 6 |
| **Total** | | **52** |
