# UI Test Cases — Integration, Security, Edge Case, Performance & E2E

> **Area:** Integration Flows, Security & Data Leak, Edge Case & Resilience, Performance Benchmarks, E2E  
> **Plan reference:** Layers 6–10 (37 tests)  
> **Test prefixes:** `TC-INT`, `TC-SEC`, `TC-EDGE`, `TC-PERF`, `TC-E2E`  
> **Last updated:** 2026-07-24

---

## 1. Integration Flows

> **File:** `ui/src/tests/flows/`  
> **Test prefix:** `TC-INT`  
> **Count:** 5 tests

These tests combine multiple pages, stores, and components to verify end-to-end behavior within the React app (no Docker required). They cover the critical user journeys that touch auth, navigation, data fetching, and error boundaries.

---

### TC-INT-001: Full auth lifecycle — login to dashboard, navigate to servers, logout

**Description:** Verifies the complete authenticated user journey from login through data viewing to logout. The user logs in, sees the dashboard with populated data, navigates to the servers page, verifies server data renders, then logs out and is redirected to the login page. This ensures auth state, routing guards, and data fetching work correctly together.

**Severity:** Critical

**Preconditions:**
- `login()` API mock returns a valid token and user object
- `fetchServers()` and `fetchDashboardStats()` return populated data
- Router is wrapped around the app component
- `useAuthStore` starts with `token: null`

**Test Steps:**
1. Render `<App />` (which contains the router and auth guard)
2. Verify redirect to `/login` — login form is visible
3. Fill in username and password fields
4. Click submit — mock `login()` resolves
5. Verify `useAuthStore.getState().token` is set to the mock token
6. Verify navigation to `/` — dashboard page renders with stat cards
7. Click the "Servers" link in the sidebar
8. Verify URL changes to `/servers`
9. Verify server table renders with mock server data (name, endpoint, health)
10. Click the logout button (top bar)
11. Verify `localStorage` items `fabric_token` and `fabric_user` are removed
12. Verify URL changes to `/login`
13. Verify the login form is visible again

**Expected Results:**
- Login form is shown when unauthenticated
- Successful login populates the auth store and navigates to dashboard
- Dashboard renders fetched stats (server count, healthy, pending approvals)
- Sidebar navigation navigates to `/servers` without full page reload
- Servers page renders the server table with data from the mock API
- Logout clears all session state and returns to the login page
- After logout, the user cannot navigate back to `/` without re-authenticating

---

### TC-INT-002: Auth interceptor does not fire on login page 401

**Description:** When the login API call itself returns a 401 (invalid credentials), the app must show an error message on the login form. It must NOT trigger the auth interceptor's logout/redirect logic, which would cause a confusing double-redirect or infinite loop. This test verifies the login endpoint is excluded from the 401 interceptor.

**Severity:** Critical

**Preconditions:**
- Mock `login()` rejects with a 401 response (or returns `{ ok: false, status: 401 }`)
- Spy on `useAuthStore.getState().logout`
- Spy on `window.location.href` assignment

**Test Steps:**
1. Render the Login page
2. Enter valid-looking credentials
3. Click submit
4. Wait for the API call to reject with 401
5. Check whether `logout()` was called
6. Check whether `window.location.href` was changed
7. Check the DOM for error-related content

**Expected Results:**
- `logout()` is NOT called (the interceptor must skip `/auth/login` paths)
- `window.location.href` is NOT changed (no redirect)
- An error message is visible on the login page: "Invalid credentials" or "Login failed"
- The user can retry without being redirected away

---

### TC-INT-003: Trust Posture — select agent class, change trust, verify mutation

**Description:** The Trust Posture page lets the user select an agent class, then change trust levels for individual servers. This test verifies the cross-page data flow: agent classes are fetched, selecting one updates local state, and changing a server's trust level calls the mutation with the correct `classId`, `serverId`, and `trustLevel`.

**Severity:** Important

**Preconditions:**
- Mock `fetchAgentClasses()` returns 2 classes: `[{ id: 'cls-1', name: 'Code Search' }, { id: 'cls-2', name: 'KB Server' }]`
- Mock `fetchServers()` returns 2 servers with trust assignments
- Mock `setTrustAssignment()` resolves successfully

**Test Steps:**
1. Render the TrustPosture page
2. Wait for agent class dropdown to populate — verify both class names visible
3. Select "Code Search" (id: `cls-1`) from the agent class dropdown
4. Verify the selected class ID is stored in component state (`cls-1`)
5. Find the first server card and click its trust level dropdown
6. Change the trust level from "trusted" to "restricted"
7. Verify `setTrustAssignment()` is called with the correct arguments

**Expected Results:**
- Agent class dropdown is populated from the `fetchAgentClasses()` API call
- Selecting a class stores its `classId` in component state
- Changing a server's trust level calls `setTrustAssignment(serverId, classId, trustLevel)`
- The `classId` passed to the mutation matches the selected dropdown value (`cls-1`), not a hardcoded value
- The mutation is called with the correct `serverId` and the new `trustLevel`

---

### TC-INT-004: ErrorBoundary — child crashes, fallback shows, retry keeps crashing, "Go to Dashboard" present

**Description:** ErrorBoundary must catch rendering errors from any child component and display a fallback UI. If the user clicks "Try Again" but the component still crashes (uncrashable error), the ErrorBoundary must re-catch and prevent an infinite recovery loop. A "Go to Dashboard" link must be present to let the user navigate away.

**Severity:** Critical

**Preconditions:**
- A test component that always throws on render: `const Crashy = () => { throw new Error('Kaboom') }`
- Wrap Crashy in ErrorBoundary inside a Router context

**Test Steps:**
1. Render `<ErrorBoundary><Crashy /></ErrorBoundary>` inside a MemoryRouter
2. Verify "Something went wrong" heading is visible (fallback UI)
3. Verify the error message "Kaboom" is displayed
4. Find the "Try Again" button and click it
5. Verify the ErrorBoundary attempts to re-render Crashy
6. Crashy throws again — ErrorBoundary re-catches
7. Verify the fallback UI is still shown
8. Verify a "Go to Dashboard" link is present with `href="/"`

**Expected Results:**
- First crash: fallback UI renders with "Something went wrong" and the error message
- "Try Again" button is visible
- Clicking "Try Again" re-renders children; if they crash again, ErrorBoundary catches again
- No infinite render loop — the fallback UI stays stable after the second crash
- A "Go to Dashboard" link is visible with `href="/"` so the user can navigate away

---

### TC-INT-005: ErrorBoundary "Go to Dashboard" sets window.location.href to '/'

**Description:** The "Go to Dashboard" link in the ErrorBoundary fallback must navigate away from the broken page by setting `window.location.href = '/'`. This provides a hard navigation escape hatch when the React router itself may be compromised by the error.

**Severity:** Important

**Preconditions:**
- Spy on `window.location.href` (using `Object.defineProperty` or a mock)
- ErrorBoundary rendered with a crashing child inside a MemoryRouter

**Test Steps:**
1. Render `<ErrorBoundary><Crashy /></ErrorBoundary>` so the fallback is showing
2. Find the "Go to Dashboard" link or button
3. Click it
4. Verify `window.location.href` was assigned

**Expected Results:**
- The "Go to Dashboard" element is an `<a>` tag or `<button>` with an `onClick` handler
- Clicking it sets `window.location.href` to `'/'` (or the full URL `'http://localhost:3000/'`)
- The assignment happens exactly once

---

## 2. Security & Data Leak

> **Test prefix:** `TC-SEC`  
> **Count:** 8 tests  
> **Severity guidance:** Every finding in this section blocks release.

These tests validate that MCP Fabric's UI does not expose sensitive data through accidental channels. Token leakage, XSS injection, password exposure, and credential persistence are all release-blocking concerns.

---

### TC-SEC-001: Token not logged to console

**Description:** The authentication token (`fcp_` prefixed string) must never appear in any `console.log` call during or after the login flow. Accidental console logging of tokens can leak credentials in browser dev tools, CI logs, or error reporting services. This test spies on all `console.log` calls and asserts the token string never appears as an argument.

**Severity:** Critical

**Preconditions:**
- Spy on `console.log` via `vi.spyOn(console, 'log')`
- Mock login API returns a known token value: `'fcp_live_abc123def456'`

**Test Steps:**
1. Render the Login page
2. Enter credentials and submit
3. Wait for login to complete and navigate to dashboard
4. Interact with the dashboard (render data, click elements)
5. Inspect all `console.log` call arguments

**Expected Results:**
- `console.log` may have been called any number of times (logging is allowed)
- No invocation of `console.log` has the string `'fcp_live_abc123def456'` as any argument
- The token substring `'fcp_'` does not appear in any log argument
- Also verify `console.warn`, `console.error`, and `console.info` for the same (spy on all four)

---

### TC-SEC-002: Token not in rendered DOM attributes

**Description:** The auth token must not appear in any DOM attribute (data-*, class, id, aria-*, title, href, src, or any custom attribute) after the login flow completes. If React dev tools or a DOM inspector can find the token in the rendered HTML, it can be extracted by malicious browser extensions or XSS attacks.

**Severity:** Critical

**Preconditions:**
- Mock login API returns a known token: `'fcp_live_abc123def456'`
- App rendered with a logged-in state (token in auth store)

**Test Steps:**
1. Set `useAuthStore` state with the known token
2. Render the full App (dashboard page after login)
3. Query the rendered DOM for all elements
4. For each element, inspect its `outerHTML` for token-like patterns

**Expected Results:**
- No element's `outerHTML` contains the string `fcp_live_abc123def456`
- No element's `outerHTML` contains the substring `fcp_` (the token prefix)
- Specifically check: `data-*` attributes, `class` attribute, `id` attribute, `title` attribute, `aria-*` attributes, inline `style`, `name` attribute, custom `data-testid`
- The token is stored ONLY in the Zustand store and localStorage, never serialized to the DOM

---

### TC-SEC-003: Token and user data cleared from localStorage on logout

**Description:** When the user logs out, all persisted session data (`fabric_token`, `fabric_user`) must be immediately removed from localStorage. Leaving stale tokens in storage poses a security risk if an attacker gains access to the machine or if the browser tab is restored.

**Severity:** Critical

**Preconditions:**
- `localStorage` contains `fabric_token` and `fabric_user` (simulate logged-in state)
- Auth store is initialized with token and user

**Test Steps:**
1. Set `localStorage.setItem('fabric_token', 'fcp_live_secret123')`
2. Set `localStorage.setItem('fabric_user', JSON.stringify({ id: 'usr-1', username: 'admin' }))`
3. Initialize auth store
4. Call `useAuthStore.getState().logout()`
5. Check `localStorage` for both keys

**Expected Results:**
- `localStorage.getItem('fabric_token')` returns `null`
- `localStorage.getItem('fabric_user')` returns `null`
- `useAuthStore.getState().token` is `null`
- `useAuthStore.getState().user` is `null`
- No other keys with `fabric_` prefix remain in localStorage

---

### TC-SEC-004: XSS in server name renders as text, not executed

**Description:** Server names are user-controlled (set during registration). If a server name contains an HTML/script injection like `<script>alert('xss')</script>`, the admin UI must render it as escaped text, not execute it as HTML. React's JSX auto-escaping should handle this, but the test confirms no `dangerouslySetInnerHTML` bypass exists in the server rendering path.

**Severity:** Critical

**Preconditions:**
- Mock `fetchServers()` returns a server with `name: "<script>alert('xss')</script>"`
- Spy on `alert()` to catch any script execution

**Test Steps:**
1. Set up mock with XSS payload in server name
2. Render the Servers page
3. Search the DOM for `<script>` elements
4. Check the rendered text content of the server name cell

**Expected Results:**
- `document.querySelector('script')` returns `null` (no `<script>` element was created)
- `alert()` was NOT called
- The cell text content is `"<script>alert('xss')</script>"` — the raw string is visible
- The angle brackets are rendered as literal text characters in the DOM

---

### TC-SEC-005: XSS in audit event details renders via React auto-escaping

**Description:** Audit event `details` is a JSONB field that can contain arbitrary strings from MCP server responses. If a server sends malicious HTML in its response details, the audit page must render it through React's standard JSX auto-escaping — never via `dangerouslySetInnerHTML`.

**Severity:** Critical

**Preconditions:**
- Mock `fetchAuditEvents()` returns an event with `details: { message: "<img src=x onerror=alert('xss')>" }`
- Spy on `alert()`

**Test Steps:**
1. Render the Audit page with the XSS payload in event details
2. Find the details cell or panel for the malicious event
3. Inspect the rendered output

**Expected Results:**
- `alert()` was NOT called
- The rendered text contains the literal string `"<img src=x onerror=alert('xss')>"` with visible angle brackets
- The `<img>` element was NOT created in the DOM
- The component rendering `details` uses `{details.message}` (JSX expression), NOT `dangerouslySetInnerHTML`
- If the `details` field is rendered as formatted JSON, the output is still text-escaped

---

### TC-SEC-006: No password in error messages

**Description:** If the API returns an error response that contains the user's `password` field (e.g., validation error echoing back the request body), the login page must display a generic error message only. Raw API error bodies must never be shown directly, as they could leak credentials in the UI.

**Severity:** Critical

**Preconditions:**
- Mock `login()` rejects with an error response body containing `password` and `username` fields: `{ message: "Validation failed", errors: { password: "Too short", username: "admin" } }`
- The error reaches the Login page component

**Test Steps:**
1. Render the Login page
2. Enter username `"admin"` and password `"abc"` (short password to trigger validation)
3. Click submit
4. Wait for the API to reject
5. Inspect the rendered error message

**Expected Results:**
- An error message is visible on the page
- The error message is generic — "Login failed" or "Invalid credentials"
- The word `"password"` does NOT appear anywhere in the rendered error UI
- The submitted password value `"abc"` does NOT appear anywhere in the rendered error UI
- The API response body is not dumped directly onto the page

---

### TC-SEC-007: No token_hash exposure — UI shows token_prefix only

**Description:** After generating an agent class token, the UI must display only the token prefix (`fcp_****`) never the full token or its hash. If an attacker can read the full token from the screen, they can authenticate as that agent class. The full token must only be shown once at generation time, in a dedicated warning banner.

**Severity:** Critical

**Preconditions:**
- Mock `generateAgentClassToken()` returns `{ token: "fcp_live_generated123456", token_prefix: "fcp_****" }`
- AgentClasses page rendered

**Test Steps:**
1. Render the AgentClasses page
2. Open the tokens modal for an agent class
3. Click "Generate" to create a new token
4. Note the displayed token value in the warning banner
5. Close the modal
6. Reopen the tokens modal
7. Inspect the displayed token information

**Expected Results:**
- At generation time: the full token `"fcp_live_generated123456"` is shown in a warning banner with text "It will not be shown again"
- When viewing the token list (modal reopened): only `token_prefix` is shown per token
- Each token row displays `"fcp_****"` — the full hash is never visible
- The UI does not display any field labeled `token_hash` or containing the full hash

---

### TC-SEC-008: Close modal with generated token then reopen — token gone

**Description:** The generated token non-recoverability is a critical security property. Once the user closes the modal that showed the generated full token, reopening must show only the prefix. This prevents token leakage through casual browsing or screen sharing after the initial generation flow.

**Severity:** Important

**Preconditions:**
- Mock `generateAgentClassToken()` returns `{ token: "fcp_live_secret789", token_prefix: "fcp_****" }`
- AgentClasses page rendered
- Tokens modal for an agent class is open

**Test Steps:**
1. Click "Generate" token button
2. Verify the full token `"fcp_live_secret789"` is displayed with the "It will not be shown again" warning
3. Close the modal (click overlay or close button)
4. Reopen the tokens modal (click "View Tokens" or equivalent)
5. Inspect the DOM for the full token string
6. Inspect the DOM for the token prefix

**Expected Results:**
- After generation: full token visible in the warning banner
- After close and reopen: the full token `"fcp_live_secret789"` is NOT present in the DOM
- Each token in the list shows only its prefix, e.g., `"fcp_****"`
- The `createdToken` state in the component is `null` after modal close
- The warning banner is gone — only "Generate" button and token list are shown

---

## 3. Edge Case & Resilience

> **Test prefix:** `TC-EDGE`  
> **Count:** 15 tests

These tests verify that the admin UI behaves correctly under unusual conditions: corrupted data, unexpected throw types, rapid user interactions, network failures, and boundary states.

---

### TC-EDGE-001: localStorage corrupted JSON in fabric_user — app loads without crash

**Description:** If the `fabric_user` key in localStorage contains corrupted JSON (e.g., `"{bad json"`), the auth store must catch the `JSON.parse` error and set `user` to `null`. The app must not crash on load, and the login page must render normally.

**Severity:** Critical

**Preconditions:**
- `localStorage.setItem('fabric_token', 'fcp_valid_token')` (token is valid)
- `localStorage.setItem('fabric_user', '{bad json')` (corrupted JSON)
- No uncaught exception handlers in test

**Test Steps:**
1. Set localStorage with valid token and corrupted user JSON
2. Import/create the auth store
3. Check if `useAuthStore.getState()` throws
4. Check `useAuthStore.getState().user`
5. Check `localStorage.getItem('fabric_user')` after store init
6. Render the App with this store state

**Expected Results:**
- Store creation does NOT throw — `JSON.parse` error is caught
- `useAuthStore.getState().user` is `null`
- `useAuthStore.getState().token` is `'fcp_valid_token'` (token is still valid)
- The corrupted `fabric_user` key is removed from localStorage (or cleared)
- The App renders the dashboard (token is valid, so user navigates in), NOT a crash screen

---

### TC-EDGE-002: Non-Error throw in onError — string rejection

**Description:** The API client or a mutation's `onError` handler may receive a non-`Error` rejection value (e.g., a string `'timeout'`). The error display logic must handle this gracefully by displaying the string value as the toast message, not crashing on `.message` access.

**Severity:** Important

**Preconditions:**
- A mutation or API call that `onError` receives the string `'timeout'`
- ToastProvider wrapping the test component
- Spy on `addToast`

**Test Steps:**
1. Render a component that calls a mutation whose `onError` receives `'timeout'`
2. Trigger the mutation
3. Wait for the error to be handled

**Expected Results:**
- No runtime error is thrown (specifically no `TypeError: Cannot read properties of undefined (reading 'message')`)
- `addToast` is called with `'error'` type and `'timeout'` as the message text
- The toast renders "timeout" text in the DOM
- The UI is not crashed — the page remains interactive

---

### TC-EDGE-003: Non-Error throw — null rejection

**Description:** If a promise rejects with `null` (not an Error instance), the error handler must not crash when accessing `.message` on the null value. It must fall back to a generic error message.

**Severity:** Important

**Preconditions:**
- A mutation or API call rejects with `null`
- ToastProvider wrapping

**Test Steps:**
1. Trigger an action that causes a rejection with `null`
2. Wait for error handling to complete

**Expected Results:**
- No runtime error is thrown (no `TypeError: Cannot read properties of null (reading 'message')`)
- A generic fallback message like "An unexpected error occurred" is shown in a toast
- The page remains functional and interactive

---

### TC-EDGE-004: Double-click submit — mutation called once only

**Description:** When the user rapidly clicks the confirm/submit button twice before the component re-renders with `isPending`, the mutation must execute exactly once. Unchecked double-submission can cause duplicate server registrations, duplicate approval resolutions, or duplicate tool mappings.

**Severity:** Critical

**Preconditions:**
- A mutation with `isPending` guard (button disabled when `isPending` is true)
- Spy on the mutation function
- The mutation resolves after a short delay (use `vi.fn().mockResolvedValue(...)` with a fake delay or manual control)

**Test Steps:**
1. Render a page with a submit button (e.g., Register Server modal)
2. Mock the mutation to NOT become pending instantly (simulate async delay)
3. Click the submit button twice in rapid succession (use `userEvent.click()` twice with no await in between, or dispatch two click events)
4. Wait for the mutation to settle

**Expected Results:**
- The mutation function is called exactly 1 time
- The second click did not trigger a second API call
- The button is disabled after the first click (or `isPending` is true)
- If the mutation manages to fire twice, the test fails

---

### TC-EDGE-005: Modal focus trap — Tab cycles within modal

**Description:** When a modal is open, pressing the Tab key must cycle focus through focusable elements inside the modal. Focus must never reach elements in the background page. This is critical for keyboard accessibility and prevents users from accidentally interacting with background content.

**Severity:** Important

**Preconditions:**
- Modal open with multiple focusable children: input, button, select
- Background page has focusable elements (sidebar links, header buttons)
- Render within the full App layout (or a wrapper with enough background elements)

**Test Steps:**
1. Render a page with an open modal containing 3 focusable elements: input, cancel button, confirm button
2. Focus the first element in the modal (the input)
3. Press Tab
4. Check `document.activeElement`
5. Press Tab again
6. Check `document.activeElement`
7. Press Tab a third time

**Expected Results:**
- First Tab: focus moves to the cancel button (input → cancel)
- Second Tab: focus moves to the confirm button (cancel → confirm)
- Third Tab: focus cycles back to the first focusable element (confirm → input)
- At no point does focus land on a background element (sidebar link, top bar, page content)
- If there is a close (×) button, it should be included in the tab order

---

### TC-EDGE-006: Rapid toast — 10 toasts in 100ms all render

**Description:** When toasts fire in rapid succession (e.g., bulk approval results), all must render independently without being lost, collapsed, or causing performance issues. Each toast must be a distinct DOM element with its own message.

**Severity:** Normal

**Preconditions:**
- ToastProvider wrapping
- Test component with access to `addToast`

**Test Steps:**
1. Fire 10 toasts with messages `"Toast 0"` through `"Toast 9"` within 100ms (use a loop with `addToast`)
2. Wait for all renders to settle
3. Query the toast container

**Expected Results:**
- All 10 toast messages are visible in the DOM
- Each message can be found individually via `screen.getByText('Toast N')`
- No toast duplicates or missing messages
- No runtime errors

---

### TC-EDGE-007: Toast independent dismiss — each dismisses at 5s from its creation

**Description:** Each toast maintains its own dismiss timer independent of other toasts. A toast created at t=0s dismisses at t=5s. A toast created at t=2s dismisses at t=7s. This prevents a single fast timer from clearing all toasts prematurely.

**Severity:** Important

**Preconditions:**
- Fake timers enabled (`vi.useFakeTimers()`)
- ToastProvider wrapping

**Test Steps:**
1. At t=0s: fire `addToast('info', 'First')`
2. Advance timer to t=2s
3. At t=2s: fire `addToast('info', 'Second')`
4. Advance timer to t=5s
5. Check rendered toasts
6. Advance timer to t=7s
7. Check rendered toasts

**Expected Results:**
- At t=5s: "First" toast is dismissed (5s elapsed since its creation)
- At t=5s: "Second" toast is still visible (only 3s elapsed since its creation)
- At t=7s: "Second" toast is dismissed (5s elapsed since its creation)
- No toasts remain after t=7s

---

### TC-EDGE-008: Empty array in Table — headers render, no rows, no crash

**Description:** When the Table component receives an empty data array, it must render the column headers and a zero-row body. This is the expected empty state for a table and must not cause rendering errors.

**Severity:** Normal

**Preconditions:**
- Table component imported
- Column definitions provided
- Data array is empty (`[]`)

**Test Steps:**
1. Render `<Table data={[]} columns={[
  { header: 'Name', accessorKey: 'name' },
  { header: 'Status', accessorKey: 'status' }
]} />`

**Expected Results:**
- Column headers "Name" and "Status" are visible in the `<thead>`
- `<tbody>` contains 0 rows
- No runtime errors or crashes
- No "Cannot read property of undefined" errors

---

### TC-EDGE-009: Single row in Table — one row renders correctly

**Description:** When the data array contains exactly one item, the Table must render a single row with correct cell values. Edge cases at boundary values (min=1 data item) are common sources of off-by-one errors.

**Severity:** Normal

**Preconditions:**
- Data array with 1 item
- Pagination object with `total: 1`

**Test Steps:**
1. Render `<Table data={[{ name: 'KB Server', status: 'healthy' }]} columns={[
  { header: 'Name', accessorKey: 'name' },
  { header: 'Status', accessorKey: 'status' }
]} pagination={{ total: 1, hasMore: false }} />`

**Expected Results:**
- 1 row rendered in `<tbody>`
- The row contains the text "KB Server" and "healthy"
- Pagination bar shows "Total: 1"
- No "Next" button (since `hasMore` is false)
- No crash

---

### TC-EDGE-010: Error → loading transition — retry replaces error state with skeleton

**Description:** When the user clicks retry after an error, the UI must immediately transition from the error state back to the loading state (skeleton). This provides clear visual feedback that the retry is in progress before the new data arrives.

**Severity:** Important

**Preconditions:**
- Query starts in error state: `{ isLoading: false, error: new Error('fail'), data: null }`
- Component uses PageState pattern (error → loading → data)

**Test Steps:**
1. Render the component with the query in error state
2. Verify error message and retry button are visible
3. Simulate clicking retry (or update query to loading state)
4. Check the rendered output

**Expected Results:**
- Before retry: error message visible, skeleton NOT visible
- After retry: error message disappears, skeleton loading elements appear
- The transition is instant (skeleton replaces error in the same render cycle)
- No flash of empty or incorrect content

---

### TC-EDGE-011: Populated → loading transition — refetch replaces data with skeleton

**Description:** When the user triggers a refetch while data is already displayed (e.g., pull-to-refresh or an auto-refresh interval), the UI must show the loading skeleton to indicate fresh data is being fetched. The stale data must not remain visible as it may be outdated.

**Severity:** Normal

**Preconditions:**
- Query starts in populated state: `{ isLoading: false, data: [...], error: null }`
- Component uses PageState pattern

**Test Steps:**
1. Render the component with populated data
2. Verify data content is visible (e.g., server rows)
3. Update query to loading state: `{ isLoading: true, data: undefined, error: null }`
4. Check rendered output

**Expected Results:**
- Before refetch: data content is visible, skeleton NOT visible
- After refetch triggered: the previous data is replaced by skeleton loading elements
- No stale data remains visible
- The transition is clean — no half-rendered state

---

### TC-EDGE-012: Network failure (TypeError) — fetch rejects before response

**Description:** When the network is down or the DNS fails, `fetch()` throws a `TypeError` before any response is received. The API client must propagate this error without calling the 401 interceptor (no logout on network errors) and the UI must show a meaningful error message.

**Severity:** Critical

**Preconditions:**
- Global `fetch` mock rejects with a `TypeError`: `vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))`
- Spy on `logout()`
- Component that calls the API client (e.g., Servers page)

**Test Steps:**
1. Mock `fetch` to reject with `TypeError`
2. Render a page that fetches data on mount
3. Wait for the fetch to fail
4. Check that `logout()` was NOT called

**Expected Results:**
- The component shows an error state with a network-related message
- `logout()` is NOT called (network errors are not auth failures)
- The user can click retry to attempt the fetch again
- The error is displayed in a toast or error state, not as a blank page

---

### TC-EDGE-013: Malformed JSON response — res.json() throws

**Description:** If the API returns a response with malformed JSON (e.g., truncated body like `{invalid`), `res.json()` will throw. The error handling code must catch this and display a generic error message. The app must not crash.

**Severity:** Important

**Preconditions:**
- Global `fetch` mock returns a Response with malformed body
- `res.json()` will throw when parsing

**Test Steps:**
1. Mock `fetch` to return `new Response('{invalid', { status: 200, headers: { 'Content-Type': 'application/json' } })`
2. Render a page that calls the API client
3. Wait for the fetch and JSON parsing to fail

**Expected Results:**
- No uncaught error (the `.json()` rejection is caught in the API client)
- A generic error message is displayed: "Failed to parse server response" or similar
- The page shows the error state (not the loading skeleton)
- The app does not crash — the error is handled gracefully

---

### TC-EDGE-014: Empty error body — 500 with no body

**Description:** If the API returns a 500 status with an empty body, the error handler should not crash trying to parse the response. The error message must fall back to a descriptive string like `"Request failed: 500"`.

**Severity:** Important

**Preconditions:**
- Mock `fetch` returns `{ status: 500, ok: false }` with an empty body
- `res.json()` resolves to `{}` or the catch handler provides a fallback

**Test Steps:**
1. Mock `fetch` to return a 500 response with no body (empty string)
2. Render a page that fetches data
3. Wait for the error to propagate to the UI

**Expected Results:**
- No runtime error
- The error message displayed contains `"Request failed: 500"`
- The message is not `"undefined"` or `"[object Object]"`
- The error toast or error state shows the fallback text with the HTTP status code

---

### TC-EDGE-015: Modal scroll lock — body overflow hidden while open, restored on close

**Description:** When a modal opens, the page body must have `overflow: hidden` to prevent background scrolling. When the modal closes, the body must be restored to its original `overflow` value. This prevents users from scrolling behind the modal and ensures a clean dismiss experience.

**Severity:** Important

**Preconditions:**
- Modal component imported
- Initial `document.body.style.overflow` is `''` (default)

**Test Steps:**
1. Render `<Modal open={false} onClose={vi.fn()} title="Test">content</Modal>`
2. Check `document.body.style.overflow`
3. Re-render with `open={true}`
4. Check `document.body.style.overflow`
5. Re-render with `open={false}` (or trigger onClose)
6. Check `document.body.style.overflow`

**Expected Results:**
- Before modal opens: `document.body.style.overflow` is `''` or `'visible'`
- While modal is open: `document.body.style.overflow` is `'hidden'`
- After modal closes: `document.body.style.overflow` is restored to `''` (original value)
- Multiple rapid open/close cycles correctly toggle the value

---

## 4. Performance Benchmarks (Manual)

> **Test prefix:** `TC-PERF`  
> **Count:** 3 benchmark scenarios  
> **Run cadence:** Before each release candidate  
> **Tool:** Custom benchmark script (`ui/benchmarks/`) or manual Chrome DevTools

These are manual benchmarks, not CI assertions. jsdom render timings do not reflect real browser performance. Run on a production-like machine, record results in `docs/ui-test/findings/`.

### Benchmark Procedure

```bash
cd ui
npx vitest run benchmarks/ --reporter=json > benchmarks/results.json
# Review results and compare against previous baseline
```
---

### TC-PERF-001: Render Table with 500 rows

**Description:** The Table component must handle rendering 500 data rows without excessive render time, excessive DOM nodes, or browser jank. This simulates a large server list or audit event export view.

**Severity:** Normal

**Preconditions:**
- Chrome DevTools Performance tab open (or benchmark script ready)
- Data fixture with 500 rows of realistic server/capability/audit data
- Table configured with 6 columns, pagination, and row click handler

**Test Steps:**
1. Generate a data array with 500 rows
2. Render the Table with this data (in a production build, not dev mode)
3. Measure time from mount to render completion (use `performance.mark()` / `performance.measure()` or React Profiler)
4. Count DOM nodes in the table body
5. Check for any console warnings or errors

**Expected Results:**
- Render completes in under 500ms (Chrome, production build)
- DOM node count is reasonable ( < 5000 nodes for 500 rows × 6 columns)
- No layout thrashing warnings
- No runtime errors
- Pagination correctly shows "Total: 500"

---

### TC-PERF-002: Fire 50 rapid toasts

**Description:** The toast system must handle 50 simultaneous notifications without performance degradation, overflow issues, or crashes. This simulates batch operation results (e.g., bulk approval of 50 requests).

**Severity:** Normal

**Preconditions:**
- Chrome DevTools Performance tab open
- ToastProvider wrapping the test page

**Test Steps:**
1. Fire 50 toasts programmatically within a single synchronous loop
2. Wait for all renders to settle
3. Inspect the toast container for scroll behavior
4. Measure render time for the batch

**Expected Results:**
- All 50 toast messages render in the DOM
- The toast container shows a scrollbar (toasts overflow within the container)
- No overflow spills outside the toast container
- No crash or performance freeze
- Each toast can be individually read and identified

---

### TC-PERF-003: Full dashboard load with 4 concurrent queries

**Description:** The Dashboard page fires 4 concurrent API queries on mount (servers count, healthy count, pending approvals, recent audit events). This benchmark measures the time from mount to all skeletons being replaced by actual data.

**Severity:** Important

**Preconditions:**
- Chrome DevTools Performance tab open
- All 4 API mocks return data after realistic delays (simulate network latency with staggered timers)
- Production build (`npm run build` then serve)

**Test Steps:**
1. Clear all caches (localStorage, service workers, browser cache)
2. Navigate to the dashboard page
3. Record the timestamp when the first skeleton element appears
4. Record the timestamp when the last skeleton element is replaced by data
5. Record total time from mount to fully loaded
6. Repeat 3 times and take the median

**Expected Results:**
- Total time from mount to fully loaded: < 2s (network latency excluded — mock data returns within 200ms)
- All 4 stat cards show data simultaneously (no staggered pop-in)
- No skeleton remains visible after loading completes
- No layout shift when skeletons are replaced by data
- No runtime errors in console

---

## 5. E2E (Docker Compose)

> **Test prefix:** `TC-E2E`  
> **Count:** 6 tests  
> **Script file:** `tests/e2e/test_admin_ui.sh`  
> **Run:** `docker-compose up` then execute script

These are curl-based smoke scripts that run against a full `docker-compose` deployment. They are not automated in CI initially — run manually before each release. They validate the backend API contract and static build integrity.

---

### TC-E2E-001: Health check returns healthy

**Description:** Verify the MCP Fabric API service is running and responding to health checks. All other E2E tests depend on the service being healthy, so this is the first test to run.

**Severity:** Critical

**Preconditions:**
- `docker-compose up` running
- Port mapping accessible (e.g., `http://localhost:8000`)

**Test Steps:**
1. Execute `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/v1/health`
2. Execute `curl -s http://localhost:8000/v1/health | jq '.status'`

**Expected Results:**
- HTTP status code is `200`
- Response body JSON has `"status": "healthy"` (or `"status": "ok"`)
- Response time is under 500ms

**Curl Script:**
```bash
#!/bin/bash
BASE="http://localhost:8000"
echo "=== TC-E2E-001: Health Check ==="
curl -s "$BASE/v1/health" | jq .
```

---

### TC-E2E-002: Admin login returns token

**Description:** Verify that the admin bootstrap credentials can authenticate and return a valid JWT token. This confirms the auth flow, user seeding, and token generation work correctly in the Docker environment.

**Severity:** Critical

**Preconditions:**
- Health check passed
- Bootstrap admin credentials known (`admin` / `admin` or from `docker-compose` env)

**Test Steps:**
1. `POST /v1/auth/admin/login` with bootstrap credentials
2. Extract the `token` field from the JSON response
3. Decode the token to verify it is a valid JWT (or at least verify the `fcp_` prefix)
4. Use the token to call a protected endpoint

**Expected Results:**
- HTTP status code is `200`
- Response body contains `token` field starting with `fcp_`
- Response body contains `user` object with `role: "admin"`
- Using the token as `Authorization: Bearer <token>` in a subsequent request returns 200

**Curl Script:**
```bash
#!/bin/bash
BASE="http://localhost:8000"
echo "=== TC-E2E-002: Admin Login ==="
TOKEN=$(curl -s -X POST "$BASE/v1/auth/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.token')
echo "Token: ${TOKEN:0:20}..."
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/v1/servers" | jq '. | length'
```

---

### TC-E2E-003: Register server — verify in list

**Description:** Verify that registering a new MCP server via the API adds it to the servers list. This confirms the server registration flow works end-to-end in the Docker environment.

**Severity:** Critical

**Preconditions:**
- Valid admin token obtained (from TC-E2E-002)
- Server payload with unique name

**Test Steps:**
1. `POST /v1/servers` with name, endpoint, labels, and team_namespace
2. Extract the server `id` from the response
3. `GET /v1/servers` and verify the new server appears in the list
4. Verify the server's initial trust level and health status

**Expected Results:**
- `POST /v1/servers` returns status `201` or `200`
- Response contains server `id`
- `GET /v1/servers` response includes the new server
- The server has `trust_level: "unreviewed"` (default for new registrations)

**Curl Script:**
```bash
#!/bin/bash
BASE="http://localhost:8000"
TOKEN="..."  # from TC-E2E-002
echo "=== TC-E2E-003: Register Server ==="
SERVER_ID=$(curl -s -X POST "$BASE/v1/servers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"E2E Test Server","endpoint":"http://localhost:3001","labels":["e2e","test"],"team_namespace":"team:e2e"}' | jq -r '.id')
echo "Server ID: $SERVER_ID"
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/v1/servers" | jq '.items[] | select(.id == "'$SERVER_ID'")'
```

---

### TC-E2E-004: Create capability — map tool — verify

**Description:** Verify the full capability lifecycle: create a capability, then map a tool to it, and verify the mapping appears when listing capabilities. This tests the capability management and tool mapping endpoints.

**Severity:** Critical

**Preconditions:**
- Valid admin token
- At least one registered server (from TC-E2E-003)
- Server has at least one tool available for mapping

**Test Steps:**
1. `POST /v1/capabilities` with name, domain, and description
2. Extract the capability `id`
3. `POST /v1/capabilities/{id}/mappings` with server ID and tool name
4. `GET /v1/capabilities/{id}` and verify the mapping appears

**Expected Results:**
- Capability creation returns status `201`
- Mapping creation returns status `200` or `201`
- `GET /v1/capabilities/{id}` response includes the `servers` or `mappings` array with the mapped server/tool
- The mapped tool's name matches the input

**Curl Script:**
```bash
#!/bin/bash
BASE="http://localhost:8000"
TOKEN="..."
SERVER_ID="..."  # from TC-E2E-003
echo "=== TC-E2E-004: Capability + Tool Mapping ==="
CAP_ID=$(curl -s -X POST "$BASE/v1/capabilities" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"e2e-search","domain":"knowledge","description":"E2E test capability"}' | jq -r '.id')
echo "Capability ID: $CAP_ID"
curl -s -X POST "$BASE/v1/capabilities/$CAP_ID/mappings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"server_id":"'$SERVER_ID'","tool_name":"search_kb"}' | jq .
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/v1/capabilities/$CAP_ID" | jq '.mappings'
```

---

### TC-E2E-005: Full request lifecycle — token → connect → request → audit

**Description:** Verify the complete MCP request lifecycle: an agent token authenticates, connects to a server, sends a tool request, and the request is recorded in the audit log. This is the most comprehensive E2E test covering auth, connection, tool execution, and audit.

**Severity:** Critical

**Preconditions:**
- Valid admin token
- Registered server with mapped capability (from TC-E2E-003 and TC-E2E-004)
- Agent class token for authentication

**Test Steps:**
1. Create an agent class and generate a token
2. Use the agent token to connect to the registered server
3. Send a tool request to the server via the MCP protocol
4. Query the audit log to verify the request was recorded

**Expected Results:**
- Agent class and token created successfully
- Connection to server succeeds
- Tool request returns a response (may be an error from the mock server, but the request was processed)
- Audit log contains an event for the tool request with the correct agent, server, and capability

**Curl Script:**
```bash
#!/bin/bash
BASE="http://localhost:8000"
TOKEN="..."
SERVER_ID="..."
echo "=== TC-E2E-005: Full Request Lifecycle ==="
# Create agent class
CLASS_ID=$(curl -s -X POST "$BASE/v1/agent-classes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"e2e-agent","description":"E2E test agent","namespace":"team:e2e"}' | jq -r '.id')
# Generate agent token
AGENT_TOKEN=$(curl -s -X POST "$BASE/v1/agent-classes/$CLASS_ID/tokens" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq -r '.token')
echo "Agent Token: ${AGENT_TOKEN:0:20}..."
# Connect and request (implementation-specific; may use MCP-over-HTTP or WebSocket)
curl -s -X POST "$BASE/v1/connect" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"server_id":"'$SERVER_ID'"}' | jq .
# Query audit log
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/v1/audit?limit=5" | jq '.items[:2]'
```

---

### TC-E2E-006: UI static build succeeds

**Description:** Verify that the static admin UI can be built without errors. A failed build means no UI can be served, which constitutes a release-blocking issue. This test runs `npm run build` in the UI directory and checks the output.

**Severity:** Critical

**Preconditions:**
- Node.js 20+ available
- Dependencies installed: `cd ui && npm ci`

**Test Steps:**
1. Run `cd ui && npm run build`
2. Check exit code
3. Verify the `dist/` directory exists and contains required files
4. Check build output for errors

**Expected Results:**
- Build exits with code 0
- `dist/` directory is created
- `dist/index.html` exists (entry point)
- `dist/assets/` contains JavaScript and CSS bundles
- No TypeScript errors in build output
- No dependency resolution errors

**Script:**
```bash
#!/bin/bash
echo "=== TC-E2E-006: UI Build ==="
cd ui
npm ci
npm run build
if [ $? -eq 0 ]; then
  echo "BUILD SUCCESS"
  ls -la dist/
else
  echo "BUILD FAILED"
  exit 1
fi
```

---

## Summary

| Prefix | Layer | Test Count |
|--------|-------|------------|
| TC-INT | Layer 6: Integration Flows | 5 |
| TC-SEC | Layer 7: Security & Data Leak | 8 |
| TC-EDGE | Layer 8: Edge Case & Resilience | 15 |
| TC-PERF | Layer 9: Performance Benchmarks | 3 |
| TC-E2E | Layer 10: E2E (Docker Compose) | 6 |
| **Total** | | **37** |
