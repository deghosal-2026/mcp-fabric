# UI Test Cases — Navigation & Routing

> **Area:** Navigation & Routing  
> **Plan reference:** Layer 5 (16 tests)  
> **Test prefix:** `TC-NAV`  
> **Last updated:** 2026-07-24

---

## 1. Auth Guard & Redirects

### TC-NAV-001: No token redirects to /login

**Description:** When no auth token exists, the `Layout` component should redirect to `/login` immediately. Any protected route must be inaccessible without authentication. This is the primary auth enforcement mechanism.

**Severity:** Critical

**Preconditions:**
- `useAuthStore` returns `token: null`, `user: null`
- App is rendered with `<BrowserRouter>` wrapping `<Routes>`

**Test Steps:**
1. Mock `useAuthStore` to return `{ token: null, user: null }`
2. Render `App` component
3. Assert that the `<Navigate to="/login" />` redirect occurs within `Layout`

**Expected Results:**
- The `LoginPage` renders instead of any protected page
- The heading "MCP Fabric" is visible (from `LoginPage` line 53)
- Username and password input fields are present
- No sidebar, topbar, or page content from any protected route is rendered
- `window.location.pathname` is `/login`

---

### TC-NAV-002: Token renders layout with sidebar

**Description:** When a valid token exists, the `Layout` component renders the full admin interface including `Sidebar`, `TopBar`, and the route's page content via `<Outlet />`. This validates the core authentication-gated rendering path.

**Severity:** Critical

**Preconditions:**
- `useAuthStore` returns a valid token and user object
- Mock user: `{ username: 'admin', role: 'admin' }`

**Test Steps:**
1. Mock `useAuthStore` with `{ token: 'fcp_test_token', user: { username: 'admin', role: 'admin' } }`
2. Render `App` component at route `/`
3. Assert sidebar is rendered
4. Assert topbar is rendered
5. Assert page content is rendered

**Expected Results:**
- Sidebar heading "MCP Fabric" and subtitle "Admin Console" are visible
- Sidebar nav links are rendered (filtered by role)
- Topbar shows "Welcome, admin" and role badge
- The Dashboard page heading "Dashboard" is visible
- No redirect to `/login` occurs

---

### TC-NAV-003: Catch-all redirects to /

**Description:** The catch-all route `path="*"` in `App.tsx` line 40 redirects any unrecognized path to `/` via `<Navigate to="/" replace />`. This prevents 404s and ensures navigation always resolves to a valid page.

**Severity:** Important

**Preconditions:**
- `useAuthStore` returns a valid token
- User role has access to Dashboard

**Test Steps:**
1. Mock auth store with token and user
2. Render `App` at route `/nonexistent-page`
3. Assert redirect to `/`

**Expected Results:**
- The Dashboard page renders (heading "Dashboard" visible)
- `Navigate` with `replace` prevents back-button from returning to the invalid URL
- No error boundary is triggered
- Other pages (sidebar, topbar) render normally

---

## 2. Route Resolution

### TC-NAV-004: Each route renders correct page

**Description:** Every registered route in `App.tsx` (lines 29–39) must render its corresponding page component with the correct heading. This validates the route-to-page mapping for all 11 protected routes plus the public login route.

**Severity:** Critical

**Preconditions:**
- `useAuthStore` returns token and user with role `admin`
- API calls for each page's data are mocked to return empty/success responses (to avoid loading/error states)

**Test Steps:**
1. For each route in the table below, render `App` at that route path
2. Assert the expected heading text is visible in the rendered output

| Route | Expected Page Heading |
|---|---|
| `/` | "Dashboard" |
| `/servers` | "Servers" |
| `/capabilities` | "Capability Catalog" |
| `/agent-classes` | "Agent Classes" |
| `/policies` | "Policy Editor" |
| `/audit` | "Audit Log" |
| `/approvals` | "Approvals" |
| `/packs` | "Capability Packs" |
| `/alerts` | "Alerts" |
| `/admin/users` | "Admin Users" |
| `/trust` | "Trust Posture" |
| `/login` | "MCP Fabric" (login heading) |

**Expected Results:**
- Each route renders the correct `<h1>` tag with the expected text
- No layout is rendered for `/login` (no sidebar, no topbar)
- Layout (sidebar + topbar) is rendered for all other routes
- No console errors or crashes

---

### TC-NAV-005: Login route does not check auth

**Description:** The `/login` route is defined outside the `Layout` wrapper (line 27 of `App.tsx`), so it bypasses the token check entirely. Even with no token, the login form must render without being redirected.

**Severity:** Critical

**Preconditions:**
- `useAuthStore` returns `token: null`, `user: null`

**Test Steps:**
1. Mock `useAuthStore` with `{ token: null, user: null }`
2. Render `App` at route `/login`
3. Assert LoginPage renders

**Expected Results:**
- The heading "MCP Fabric" is visible
- Username input and Password input fields are rendered
- Submit button labeled "Login" is present (disabled until fields filled)
- No `Navigate` to `/login` occurs (no infinite redirect loop)
- No sidebar or topbar is rendered

---

## 3. Role-Based Sidebar Filtering

### TC-NAV-006: Admin role sees all 11 sidebar links

**Description:** Users with `role: 'admin'` must see all 11 navigation items in the sidebar. The `Sidebar` component filters by `item.roles.includes(user.role)`.

**Severity:** Critical

**Preconditions:**
- `useAuthStore` returns token and `user: { username: 'admin', role: 'admin' }`

**Test Steps:**
1. Mock auth store with admin role
2. Render `Sidebar` (or `App` at `/`)
3. Assert all 11 nav link labels are visible

**Expected Results:**
- All 11 nav items are rendered as `<NavLink>` elements:
  1. Dashboard
  2. Servers
  3. Capabilities
  4. Agent Classes
  5. Policies
  6. Audit Log
  7. Approvals
  8. Capability Packs
  9. Alerts
  10. Admin Users
  11. Trust Posture
- Each label is visible text in the sidebar
- All links have correct `to` paths matching the navItems array

---

### TC-NAV-007: Editor role sees 10 sidebar links

**Description:** Users with `role: 'editor'` must see all nav items except "Admin Users" (which is `roles: ['admin']` only). Editor gets 10 items.

**Severity:** Important

**Preconditions:**
- `useAuthStore` returns token and `user: { username: 'editor', role: 'editor' }`

**Test Steps:**
1. Mock auth store with editor role
2. Render `Sidebar` (or `App` at `/`)
3. Assert 10 nav link labels are visible
4. Assert "Admin Users" is NOT rendered

**Expected Results:**
- 10 `<NavLink>` elements are rendered
- Visible labels: Dashboard, Servers, Capabilities, Agent Classes, Policies, Audit Log, Approvals, Capability Packs, Alerts, Trust Posture
- "Admin Users" is absent from the DOM (`queryByText('Admin Users')` returns null)
- The path `/admin/users` is still accessible by direct URL navigation (no client-side route guard other than Layout token check)

---

### TC-NAV-008: Viewer role sees 6 sidebar links

**Description:** Users with `role: 'viewer'` must see only the read-only nav items. Based on the `navItems` role arrays, viewer has access to 6 items: Dashboard, Servers, Capabilities, Audit Log, Alerts, Trust Posture.

**Severity:** Important

**Preconditions:**
- `useAuthStore` returns token and `user: { username: 'viewer', role: 'viewer' }`

**Test Steps:**
1. Mock auth store with viewer role
2. Render `Sidebar` (or `App` at `/`)
3. Assert only 6 nav link labels are visible
4. Assert the 5 excluded labels are NOT rendered

**Expected Results:**
- 6 `<NavLink>` elements are rendered
- Visible labels: Dashboard, Servers, Capabilities, Audit Log, Alerts, Trust Posture
- Absent labels (queryByText returns null): Agent Classes, Policies, Approvals, Capability Packs, Admin Users
- No errors from attempting to access `item.roles.includes(user.role)` with a role that has no items filtered out

---

## 4. Sidebar Active State

### TC-NAV-009: Active link has bg-blue-600 class

**Description:** The `NavLink` component applies `isActive`-based class logic. The currently active route's link must have `bg-blue-600` while inactive links use `text-gray-300 hover:bg-gray-800`. This is defined in `Sidebar.tsx` lines 35–40.

**Severity:** Important

**Preconditions:**
- Auth store returns token and user with role `admin`

**Test Steps:**
1. Mock auth store with admin user
2. Render `App` at `/servers`
3. Find the "Servers" NavLink and the "Dashboard" NavLink
4. Inspect their className attributes

**Expected Results:**
- The "Servers" NavLink element's className contains `bg-blue-600` and `text-white`
- The "Dashboard" NavLink element's className does NOT contain `bg-blue-600` — it contains `text-gray-300` instead
- The `end` prop is set `{item.to === '/'}` so that `/` only matches exactly `/`, not `/servers` (the Dashboard link is not active when at `/servers`)

---

## 5. TopBar

### TC-NAV-010: TopBar shows username

**Description:** The `TopBar` component renders `{user?.username}` inside a `<span>` with class `font-medium text-gray-900`. This displays the logged-in user's name on every protected page.

**Severity:** Important

**Preconditions:**
- Auth store returns user with `username: 'jdoe'`

**Test Steps:**
1. Mock auth store with `{ token: 'x', user: { username: 'jdoe', role: 'admin' } }`
2. Render `TopBar` (or `App` at `/`)
3. Assert username is rendered

**Expected Results:**
- The text "jdoe" is visible
- The parent text reads "Welcome, jdoe" (from the `TopBar` template: `Welcome, <span>{user?.username}</span>`)
- `screen.getByText('jdoe')` returns a non-null element inside the header

---

### TC-NAV-011: TopBar shows role badge

**Description:** The `TopBar` component renders `{user?.role}` as a badge-style `<span>` with classes `text-xs px-2 py-1 bg-gray-100 rounded text-gray-600`. This visually indicates the user's authorization level.

**Severity:** Minor

**Preconditions:**
- Auth store returns user with `role: 'admin'`

**Test Steps:**
1. Mock auth store with `{ token: 'x', user: { username: 'admin', role: 'admin' } }`
2. Render `TopBar` (or `App` at `/`)
3. Assert role badge is rendered

**Expected Results:**
- The text "admin" is visible in the topbar's role badge area
- The badge element has classes `text-xs`, `px-2`, `py-1`, `bg-gray-100`, `rounded`, and `text-gray-600`
- The badge is positioned to the right of the welcome message, before the Logout button

---

### TC-NAV-012: TopBar logout clears session

**Description:** Clicking the "Logout" button in `TopBar` must call the auth store's `logout()` function and navigate to `/login`. This is defined in `TopBar.tsx` lines 9–12.

**Severity:** Critical

**Preconditions:**
- Auth store returns token and user
- `logout()` and `navigate()` are mocked

**Test Steps:**
1. Mock `useAuthStore` to return `{ token: 'x', user: { username: 'admin', role: 'admin' }, logout: vi.fn() }`
2. Mock `useNavigate` to return `vi.fn()`
3. Render `TopBar`
4. Click the "Logout" button

**Expected Results:**
- `logout()` is called exactly once
- `navigate()` is called with `'/login'`
- After `logout()`, the auth store state is cleared (token and user set to null)
- No errors thrown during logout

---

## 6. ErrorBoundary

### TC-NAV-013: ErrorBoundary catches render crash

**Description:** When a child component throws during render, the `ErrorBoundary` class component (via `getDerivedStateFromError`) sets `hasError: true` and displays a fallback UI with the error message. This prevents the entire app from crashing to a white screen.

**Severity:** Critical

**Preconditions:**
- ErrorBoundary wraps a component that throws
- The thrown error has a `.message` property

**Test Steps:**
1. Render `<ErrorBoundary><ThrowingComponent /></ErrorBoundary>` where `ThrowingComponent` throws `new Error('Test crash')` in its render
2. Assert the fallback UI appears

**Expected Results:**
- The text "Something went wrong" is visible (the fallback heading)
- The error message "Test crash" is displayed in the `<p>` tag
- "Try again" button is rendered
- "Go to Dashboard" link is rendered with `href="/"`
- `console.error` is called with the error and component stack (via `componentDidCatch`)

---

### TC-NAV-014: ErrorBoundary "Try again" resets error state

**Description:** Clicking the "Try again" button calls `this.setState({ hasError: false, error: null })`, which resets `ErrorBoundary` state and re-renders `this.props.children`. If the child no longer throws, normal UI is restored.

**Severity:** Important

**Preconditions:**
- ErrorBoundary is in the error state (`hasError: true`)
- The child component is conditionally stable (does not throw on re-render)

**Test Steps:**
1. Render `<ErrorBoundary><StableComponent /></ErrorBoundary>` with an initially stable child
2. Manually simulate error state by calling `getDerivedStateFromError` or using a toggle
3. Click "Try again"

**Expected Results:**
- `ErrorBoundary` internal state `hasError` is set to `false`
- `error` is set to `null`
- The children are re-rendered and visible
- The fallback UI (error message, Try again button) is no longer in the DOM

---

### TC-NAV-015: ErrorBoundary "Go to Dashboard" link renders with href="/"

**Description:** The "Go to Dashboard" element in ErrorBoundary's fallback is an `<a>` tag with `href="/"`. This provides a hard navigation escape hatch that works even if React Router's context is corrupted by the crash.

**Severity:** Important

**Preconditions:**
- ErrorBoundary is in the error state

**Test Steps:**
1. Render `<ErrorBoundary><ThrowingComponent /></ErrorBoundary>`
2. Locate the "Go to Dashboard" element

**Expected Results:**
- The element with text "Go to Dashboard" is a `<a>` tag (not a `<button>` or `<Link>`)
- Its `href` attribute equals `"/"`
- The element has classes `px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50`
- The `<a>` tag ensures navigation works even if React context is corrupted

---

### TC-NAV-016: ErrorBoundary "Go to Dashboard" navigates

**Description:** Clicking the "Go to Dashboard" `<a href="/">` link triggers a full page navigation to `/`. This serves as the ultimate recovery mechanism when the React tree cannot be safely re-rendered.

**Severity:** Important

**Preconditions:**
- ErrorBoundary is in the error state
- `window.location.href` is observable (or mocked)

**Test Steps:**
1. Render `<ErrorBoundary><ThrowingComponent /></ErrorBoundary>`
2. Click the "Go to Dashboard" link
3. Assert navigation occurs

**Expected Results:**
- `window.location.href` is set to `'/'`
- The browser performs a full page load to the root URL
- This bypasses React Router entirely, functioning as a hard recovery mechanism regardless of the error's severity

---

## Appendix: Route Map

| # | Path | Component | Layout | Token Required | Page Heading |
|---|---|---|---|---|---|
| 1 | `/login` | `LoginPage` | None | No | "MCP Fabric" |
| 2 | `/` | `DashboardPage` | Layout | Yes | "Dashboard" |
| 3 | `/servers` | `ServersPage` | Layout | Yes | "Servers" |
| 4 | `/capabilities` | `CapabilitiesPage` | Layout | Yes | "Capability Catalog" |
| 5 | `/agent-classes` | `AgentClassesPage` | Layout | Yes | "Agent Classes" |
| 6 | `/policies` | `PoliciesPage` | Layout | Yes | "Policy Editor" |
| 7 | `/audit` | `AuditPage` | Layout | Yes | "Audit Log" |
| 8 | `/approvals` | `ApprovalsPage` | Layout | Yes | "Approvals" |
| 9 | `/packs` | `PacksPage` | Layout | Yes | "Capability Packs" |
| 10 | `/alerts` | `AlertsPage` | Layout | Yes | "Alerts" |
| 11 | `/admin/users` | `AdminUsersPage` | Layout | Yes | "Admin Users" |
| 12 | `/trust` | `TrustPosturePage` | Layout | Yes | "Trust Posture" |
| 13 | `*` | `Navigate to="/"` | Layout | Yes | — |

## Appendix: Role-to-NavItem Mapping

| Nav Item | Path | Admin | Editor | Viewer |
|---|---|---|---|---|
| Dashboard | `/` | ✓ | ✓ | ✓ |
| Servers | `/servers` | ✓ | ✓ | ✓ |
| Capabilities | `/capabilities` | ✓ | ✓ | ✓ |
| Agent Classes | `/agent-classes` | ✓ | ✓ | ✗ |
| Policies | `/policies` | ✓ | ✓ | ✗ |
| Audit Log | `/audit` | ✓ | ✓ | ✓ |
| Approvals | `/approvals` | ✓ | ✓ | ✗ |
| Capability Packs | `/packs` | ✓ | ✓ | ✗ |
| Alerts | `/alerts` | ✓ | ✓ | ✓ |
| Admin Users | `/admin/users` | ✓ | ✗ | ✗ |
| Trust Posture | `/trust` | ✓ | ✓ | ✓ |
| **Total** | | **11** | **10** | **6** |
