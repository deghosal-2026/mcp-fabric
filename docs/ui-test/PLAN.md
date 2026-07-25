# MCP Fabric — UI Test Plan

> **Version:** 1.0  
> **Status:** Draft  
> **Last updated:** 2026-07-24  
> **Phase:** 10 (Testing)  
> **Coverage target:** 95%+ line coverage for `ui/src/`

---

## Table of Contents

1. [Scope & Principles](#1-scope--principles)
2. [Environment & Tooling](#2-environment--tooling)
3. [Test Layers Overview](#3-test-layers-overview)
4. [Layer 0: Infrastructure](#4-layer-0-infrastructure)
5. [Layer 1: Shared Components](#5-layer-1-shared-components)
6. [Layer 2: Auth & Session](#6-layer-2-auth--session)
7. [Layer 3: API Client](#7-layer-3-api-client)
8. [Layer 4: Page Smoke Tests](#8-layer-4-page-smoke-tests)
9. [Layer 5: Navigation & Routing](#9-layer-5-navigation--routing)
10. [Layer 6: Integration Flows](#10-layer-6-integration-flows)
11. [Layer 7: Security & Data Leak](#11-layer-7-security--data-leak)
12. [Layer 8: Edge Case & Resilience](#12-layer-8-edge-case--resilience)
13. [Layer 9: Performance](#13-layer-9-performance)
14. [Layer 10: E2E (Docker Compose)](#14-layer-10-e2e-docker-compose)
15. [Test Data Matrix](#15-test-data-matrix)
16. [Risk Register](#16-risk-register)
17. [Findings Log](#17-findings-log)

---

## 1. Scope & Principles

### In Scope

- All 12 admin UI pages
- All 11 shared components
- API client (`ui/src/api/client.ts`)
- Auth store (`ui/src/stores/authStore.ts`)
- Routing and navigation
- All user-visible error, loading, and empty states
- Cross-cutting security concerns (token handling, data exposure, XSS)
- Boundary and edge-case behavior
- All states covered in PRD Journeys 1–29 and spec Sections 1–24

### Out of Scope (Initial Pass)

- Visual regression testing (screenshots)
- Cross-browser testing (Chrome-only for CI)
- Mobile/responsive layout testing
- Accessibility audit (manual, outside test automation)
- Performance benchmarking (separate activity)
- API contract conformance (tested in backend Phase 10)

### Testing Principles

1. **State coverage over line coverage** — every loading/error/empty/populated transition must be tested. Line coverage is a baseline, not a target.
2. **Security tests are not optional** — token leakage, XSS in rendered data, localStorage poisoning, and auth bypass must each have at least one dedicated test.
3. **No E2E-only coverage** — every E2E scenario must have a unit or integration test counterpart. E2E is for validation, not discovery.
4. **Test the boundary, not the library** — don't test that `@tanstack/react-query` works (it does). Test that your code handles its outputs correctly.
5. **Every mutation has a race-condition test** — rapid clicks, concurrent mutations, stale-after-navigate.

---

### Design Decision: Page State Reset on Navigation

> **Status:** Accepted | **Last reviewed:** 2026-07-24

Filters, modals, and scroll position are stored in local React state and reset when the user navigates away from a page. This is intentional — admin tools prioritize fresh state over state preservation. If URL-synced filters are needed in the future, implement with `useSearchParams` and add a test layer.

---

## 2. Environment & Tooling

| Concern | Choice | Rationale |
|---|---|---|
| Test runner | Vitest | Vite-native, fast, Watch mode, compatible with React Testing Library |
| DOM environment | jsdom (via `@testing-library/jest-dom`) | Lightweight, sufficient for all component/page tests |
| Rendering | `@testing-library/react` | Queries by accessible roles/text, not implementation details |
| User events | `@testing-library/user-event` | Simulates real browser interactions (clicks, typing) better than `fireEvent` |
| API mocking | Vitest module mock (`vi.mock`) | Mock `../api/client` at module level for page tests |
| MSW | Not used initially | Adds complexity; module mocking is sufficient for unit/page tests. Evaluate for E2E later. |
| Coverage | `c8` via Vitest | `threshold: 95` for `ui/src/`, per-file minimum `80` |
| E2E | `docker-compose` + curl scripts (not Playwright) | Matches spec Section 22 CI pipeline; Playwright deferred |

### Configuration File

```typescript
// ui/vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.*', 'src/test/**', 'src/vite-env.d.ts'],
      thresholds: {
        lines: 95,
        functions: 90,
        branches: 85,
        statements: 95,
      },
    },
  },
})
```

### Setup File

```typescript
// ui/src/test/setup.ts
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
})
```

---

## 3. Test Layers Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Layer 10: E2E (3 tests)                   │
│  Full Docker Compose lifecycle, curl-based smoke tests      │
├─────────────────────────────────────────────────────────────┤
│                    Layer 9: Performance (2 tests)            │
│  500-row table render, 50 rapid toasts                     │
├─────────────────────────────────────────────────────────────┤
│                 Layer 8: Edge Case & Resilience (12 tests)   │
│  localStorage poison, fetch network failure, abort race     │
├─────────────────────────────────────────────────────────────┤
│                Layer 7: Security & Data Leak (8 tests)       │
│  Token leak in logs, XSS in rendered data, auth bypass      │
├─────────────────────────────────────────────────────────────┤
│                 Layer 6: Integration Flows (5 tests)         │
│  Cross-page trust flow, login→navigate→logout              │
├─────────────────────────────────────────────────────────────┤
│              Layer 5: Navigation & Routing (5 tests)         │
│  Sidebar links, role filtering, catch-all redirect          │
├─────────────────────────────────────────────────────────────┤
│                Layer 4: Page Smoke Tests (28 tests)          │
│  12 pages × 2 states + 4 deep-flow pages                    │
├─────────────────────────────────────────────────────────────┤
│                  Layer 3: API Client (10 tests)              │
│  Headers, 401 intercept, error parse, query builder         │
├─────────────────────────────────────────────────────────────┤
│                Layer 2: Auth & Session (8 tests)             │
│  Login/MFA flow, store persistence, token expiry race       │
├─────────────────────────────────────────────────────────────┤
│              Layer 1: Shared Components (24 tests)           │
│  Modal, Table, Toast, Badge, PageState, FilterBar           │
├─────────────────────────────────────────────────────────────┤
│              Layer 0: Infrastructure (5 tests)              │
│  Vitest config, setup file, test harness verification       │
└─────────────────────────────────────────────────────────────┘
```

**Total: ~110 tests** across 11 layers.

---

## 4. Layer 0: Infrastructure

> **Effort:** 1h | **File:** `ui/src/test/setup.ts`, `vitest.config.ts`

### T0-01: Test harness boots
- Vitest loads configuration
- jsdom environment active
- `document.getElementById('root')` creates a container

### T0-02: Setup file runs
- `cleanup()` called after each test
- `localStorage.clear()` restores state
- `vi.restoreAllMocks()` clears mocks

### T0-03: React Testing Library renders a component
- `render(<div>hello</div>)`
- `screen.getByText('hello')` finds the element
- DOM assertions work (`toBeInTheDocument()`)

### T0-04: Path alias resolution
- `import { ... } from '@/components/shared/Modal'` resolves (if aliases configured)
- If no aliases, relative imports work

### T0-05: Coverage threshold verification
- `vitest --coverage` reports per-file and aggregate thresholds
- CI job fails if below threshold

---

## 5. Layer 1: Shared Components

> **Effort:** 4h | **File:** `ui/src/components/**/*.test.tsx` (colocated)

### 5.1 LoadingState (`LoadingState.test.tsx`) — 2 tests

| # | Test | Assertion |
|---|---|---|
| T1-01 | Renders correct number of skeleton rows | Default 3 rows, custom `5` renders 5 |
| T1-02 | Skeleton elements have pulse animation class | Class contains `animate-pulse` |

### 5.2 ErrorState (`ErrorState.test.tsx`) — 3 tests

| # | Test | Assertion |
|---|---|---|
| T1-03 | Renders error message text | `screen.getByText('Something went wrong')` exists |
| T1-04 | Retry button fires `onRetry` callback | Clicking button calls mocked `onRetry` once |
| T1-05 | No retry button when `onRetry` omitted | `queryByRole('button')` returns null |

### 5.3 EmptyState (`EmptyState.test.tsx`) — 3 tests

| # | Test | Assertion |
|---|---|---|
| T1-06 | Renders message text | Core message visible |
| T1-07 | Action button renders and fires callback | CTA button calls `onAction` |
| T1-08 | No action button when `onAction` omitted | Button not rendered |

### 5.4 Badge (`Badge.test.tsx`) — 4 tests

| # | Test | Assertion |
|---|---|---|
| T1-09 | Known variant applies correct color class | `trusted` → `bg-green-100`, `restricted` → `bg-yellow-100` |
| T1-10 | Unknown variant falls back to gray | `unknown-status` → `bg-gray-100` |
| T1-11 | `variant` prop overrides `label` for color | `variant="trusted"` with `label="custom"` uses green |
| T1-12 | Renders label text | Text content matches `label` prop |
| T1-12b | Long label truncated with `truncate` class | Label > 30 chars → CSS `truncate` + `max-w-[200px]` applied, no layout break |

### 5.5 Modal (`Modal.test.tsx`) — 5 tests

| # | Test | Assertion |
|---|---|---|
| T1-13 | Renders nothing when `open=false` | Container is not in DOM |
| T1-14 | Renders content when `open=true` | Title and children visible |
| T1-15 | Closes on Escape key | `onClose` called once |
| T1-16 | Closes on overlay click | `onClose` called once (verify target check) |
| T1-17 | Confirm button disabled when `confirmDisabled=true` | Button has `disabled` attribute |

### 5.6 ConfirmDialog (`ConfirmDialog.test.tsx`) — 3 tests

| # | Test | Assertion |
|---|---|---|
| T1-18 | Renders destructive styling pass-through to Modal | Confirm button has `bg-red-500` |
| T1-19 | Cancel button fires `onClose` | Click cancel → `onClose` called |
| T1-20 | Confirm button fires `onConfirm` | Click confirm → `onConfirm` called |

### 5.7 Toast (`Toast.test.tsx`) — 4 tests

| # | Test | Assertion |
|---|---|---|
| T1-21 | `addToast('success', msg)` renders message | Toast text visible |
| T1-22 | Auto-dismisses after 5s | `setTimeout` called with 5000ms |
| T1-23 | Multiple toasts stack | 3 toasts → 3 rendered elements |
| T1-24 | Color per type | `success` → `bg-green-500`, `error` → `bg-red-500` |

### 5.8 Table (`Table.test.tsx`) — 5 tests

| # | Test | Assertion |
|---|---|---|
| T1-25 | Renders column headers | All headers from `columns` visible |
| T1-26 | Renders data rows | 5 items → 5 rows in tbody |
| T1-27 | Row click fires `onRowClick` | Click row → callback with correct row data |
| T1-28 | Pagination controls show when `pagination` provided | Info bar, Next button visible |
| T1-29 | No pagination when `pagination` omitted | Info bar not rendered |

### 5.9 FilterBar (`FilterBar.test.tsx`) — 4 tests

| # | Test | Assertion |
|---|---|---|
| T1-30 | Renders filter dropdowns | One select per filter option group |
| T1-31 | Selecting a filter fires `onFilter` | Change value → `onFilter` called with `{ key: value }` |
| T1-32 | Search input fires with 300ms debounce | Type "abc" → 300ms later `onFilter` called with search param |
| T1-33 | Clear all button resets filters | Click clear → `onFilter` called with `{}` |

### 5.10 PageState (`PageState.test.tsx`) — 4 tests

| # | Test | Assertion |
|---|---|---|
| T1-34 | Loading state: renders skeleton when `isLoading=true` | Pulse animation divs rendered |
| T1-35 | Error state: renders error message when `error` set | Error text, retry button visible |
| T1-36 | Empty state: renders "No data" when data is `null | undefined` |
| T1-37 | Populated state: renders children with data | Children function called with data |

**Total Layer 1: 38 tests**

---

## 6. Layer 2: Auth & Session

> **Effort:** 3h | **File:** `ui/src/stores/authStore.test.ts`, `ui/src/pages/Login.test.tsx`

### 6.1 Auth Store — 5 tests

| # | Test | Assertion |
|---|---|---|
| T2-01 | Initializes token from localStorage | `localStorage.setItem('fabric_token', 'x')` → store has `token: 'x'` |
| T2-02 | Initializes user from localStorage JSON | Valid JSON in `fabric_user` → parsed correctly |
| T2-03 | **LocalStorage poison:** Invalid JSON in `fabric_user` | `JSON.parse` throws → store has `user: null`, corrupt key removed from localStorage, app does not crash |
| T2-04 | `login()` persists token + user | After login, both localStorage items set, store state updated |
| T2-05 | `logout()` clears token + user | After logout, both localStorage items removed, store state null |

### 6.2 Login Page — 5 tests

| # | Test | Assertion |
|---|---|---|
| T2-06 | Renders username + password form | Both input fields visible, submit button disabled when empty |
| T2-07 | Submit calls `login()` API | Click submit → `login(username, password)` called with correct values |
| T2-08 | Displays error on API failure | Mock `login()` throws → error message rendered |
| T2-09 | MFA flow: shows code input after first step | Mock `login()` returns `{ mfa_required: true }` → MFA form replaces login form |
| T2-10 | MFA verify: calls API and navigates | Enter 6-digit code → `verifyMfa()` called → `login()` called with response → navigate to `/` |

### 6.3 Session Continuity — 2 tests

| # | Test | Assertion |
|---|---|---|
| T2-11 | **Token expiry mid-session:** 401 on API call triggers redirect | Mock `fetchServers()` returns 401 → `logout()` called → `window.location.href` set to `/login` |
| T2-12 | **Login page ignores 401 interceptor for login endpoint** | `POST /auth/login` returning 401 does not call `logout()` (prevents double-clear) |

**Total Layer 2: 12 tests**

---

## 7. Layer 3: API Client

> **Effort:** 2h | **File:** `ui/src/api/client.test.ts`

### 7.1 Fetcher — 6 tests

| # | Test | Assertion |
|---|---|---|
| T3-01 | Attaches auth header when token exists | Mock `useAuthStore.getState().token` → header `Authorization: Bearer <token>` |
| T3-02 | Omits auth header when token is null | No token → no `Authorization` header |
| T3-03 | Sets Content-Type + Accept headers | Both `application/json` and `application/vnd.fabric.v1+json` present |
| T3-04 | 401 calls logout and redirects | `res.status = 401` → `logout()` called, `window.location.href` set |
| T3-05 | Non-OK response throws structured error | `res.status = 400`, body `{ message: "bad request" }` → throws `Error('bad request')` |
| T3-06 | **Network failure:** `fetch()` throws (no response) | `fetch` rejects → error propagates, no `logout()` called |

### 7.2 Query Builder — 2 tests

| # | Test | Assertion |
|---|---|---|
| T3-07 | Builds query string from params | `{ a: '1', b: '2' }` → `?a=1&b=2` |
| T3-08 | Skips undefined params | `{ a: '1', b: undefined }` → `?a=1` |

### 7.3 login() return type — 1 test

| # | Test | Assertion |
|---|---|---|
| T3-09 | login returns token + user + mfa_required | Shape matches `LoginResponse` |

### 7.4 queryClient defaults — 1 test

| # | Test | Assertion |
|---|---|---|
| T3-10 | Default staleTime is 30s | `queryClient.defaultQueryOptions().staleTime === 30000` |

**Total Layer 3: 10 tests**

---

## 8. Layer 4: Page Smoke Tests

> **Effort:** 8h | **File:** `ui/src/pages/*.test.tsx`

### Pattern

Every page test follows this structure:

```typescript
// Template for each page test
describe('<PageName>', () => {
  // 1. Render with mock data → verify key elements
  // 2. Render loading state → verify skeleton
  // 3. Render error state → verify error + retry
  // 4. (Optional) Render empty data → verify empty state
})
```

### 8.1 DashboardPage — 3 tests

| # | Test | Assertion |
|---|---|---|
| T4-01 | Renders 4 stat cards with mock data | Server count, healthy, pending approvals, degraded all visible |
| T4-02 | Renders recent servers + pending approvals + audit sections | All 3 panel headings visible |
| T4-03 | Empty state when no servers registered | "No pending approvals" text for empty approvals |

### 8.2 ServersPage — 4 tests

| # | Test | Assertion |
|---|---|---|
| T4-04 | Renders server table with health/trust badges | Name, endpoint, health, trust columns render |
| T4-05 | Register modal opens and submits | Fill form → submit → `registerServer()` called with correct data |
| T4-06 | Labels split on comma | Type `security, production` → sent as `['security', 'production']` |
| T4-07 | Filter change triggers query refetch | Change health filter → new query key `['servers', { health_status: 'healthy' }]` |

### 8.3 CapabilitiesPage — 4 tests

| # | Test | Assertion |
|---|---|---|
| T4-08 | Renders capability table with status badges | Name, domain, status columns |
| T4-09 | Create modal: submit calls `createCapability()` | Form → submit → API called |
| T4-10 | Deprecate: confirm dialog opens and submits | Click deprecate → confirm dialog → confirm → `deprecateCapability()` called with 14 grace days |
| T4-11 | Filter change triggers refetch | Status filter change → new query key |

### 8.4 AgentClassesPage — 3 tests

| # | Test | Assertion |
|---|---|---|
| T4-12 | Renders agent class table | Name, description, namespace columns |
| T4-13 | Create modal submits | Form → submit → `createAgentClass()` called |
| T4-14 | **Token show-once flow:** generate token displays it with warning banner | Click Generate → token visible → "It will not be shown again" warning present |
| T4-14b | **Token non-recoverability:** close modal and reopen → token gone | Generate token → close modal (overlay click) → reopen tokens modal → `createdToken` state is null, warning banner gone, only "Generate" button shown |

### 8.5 PoliciesPage — 3 tests

| # | Test | Assertion |
|---|---|---|
| T4-15 | Renders deployed policy list | Version + date displayed for each policy |
| T4-16 | New Policy opens editor modal | Textarea with Rego placeholder present |
| T4-17 | Deploy submits and refreshes list | Submit → `deployPolicy()` called → `queryClient.invalidateQueries` called for `['policies']` |

### 8.6 AuditPage — 3 tests

| # | Test | Assertion |
|---|---|---|
| T4-18 | Renders audit event table | Time, type, actor, target columns |
| T4-19 | Export button calls `exportAudit()` | Click Export → `exportAudit()` called |
| T4-20 | Filter by event type updates query | Change event type → query key changes |

### 8.7 ApprovalsPage — 3 tests

| # | Test | Assertion |
|---|---|---|
| T4-21 | Renders approval table with status badges | Agent, capability, status columns |
| T4-22 | Review side panel opens with request details | Click Review → panel shows agent/capability/server info |
| T4-23 | Approve/Deny calls `resolveApproval()` with correct status | Approve → `resolveApproval(id, 'approved')`, Deny → `resolveApproval(id, 'denied')` |

### 8.8 PacksPage — 2 tests

| # | Test | Assertion |
|---|---|---|
| T4-24 | Renders pack cards | Pack name, description visible |
| T4-25 | Create pack submits + assign modal opens | Create → form → submit, Assign → class selector modal |

### 8.9 AlertsPage — 2 tests

| # | Test | Assertion |
|---|---|---|
| T4-26 | Renders alert table | Message, rule, fired time columns |
| T4-27 | Acknowledge button calls API | Click Acknowledge → `acknowledgeAlert(id)` called |

### 8.10 AdminUsersPage — 3 tests

| # | Test | Assertion |
|---|---|---|
| T4-28 | Renders user table with role/status badges | Username, email, role, status, MFA columns |
| T4-29 | Invite modal submits | Fill form → submit → `inviteUser()` with username/email/role |
| T4-30 | Deactivate button (hide for self) | Current user row does not show Deactivate button |

### 8.11 TrustPosturePage — 4 tests

| # | Test | Assertion |
|---|---|---|
| T4-31 | Renders server cards with trust-colored borders | Card has border color matching trust level |
| T4-32 | Agent class selector fetches and displays classes | Dropdown populated from `fetchAgentClasses()` |
| T4-33 | Trust level change calls `setTrustAssignment()` with selected class ID | Select new trust level → API called with correct classId, serverId, trustLevel |
| T4-34 | **No-op when no class selected:** changing trust level does nothing | `selectedClassId` empty → mutation not called |

### 8.12 LoginPage — Already covered in Layer 2 (T2-06 through T2-10)

**Total Layer 4: 34 tests**

---

## 9. Layer 5: Navigation & Routing

> **Effort:** 2h | **File:** `ui/src/App.test.tsx`

### 9.1 Layout — 4 tests

| # | Test | Assertion |
|---|---|---|
| T5-01 | No token redirects to `/login` | Render App without token → Navigate to `/login` |
| T5-02 | Token renders sidebar with nav links | With token → all nav items rendered |
| T5-03 | **Role filtering:** admin sees all links, viewer sees only permitted | `user.role = 'admin'` → 11 links; `user.role = 'viewer'` → 4 links |
| T5-04 | Catch-all route redirects to `/` | Navigate to `/nonexistent` → renders Dashboard |

### 9.2 Sidebar active state — 1 test

| # | Test | Assertion |
|---|---|---|
| T5-05 | Active link has `bg-blue-600` class | Dashboard link when at `/` has active class; Servers link does not |

### 9.3 TopBar — 1 test

| # | Test | Assertion |
|---|---|---|
| T5-06 | Shows username + role | `user.username` and `user.role` rendered |
| T5-07 | Logout calls `logout()` and navigates to `/login` | Click Logout → store cleared → navigated to `/login` |

**Total Layer 5: 7 tests**

---

## 10. Layer 6: Integration Flows

> **Effort:** 4h | **File:** `ui/src/tests/flows/`

These tests combine multiple components/pages to verify end-to-end behavior within the React app (no Docker required).

### 10.1 Full Auth Lifecycle — 2 tests

| # | Test | Assertion |
|---|---|---|
| T6-01 | Login → dashboard → navigate → logout | Mock API: login returns token → store populated → dashboard renders → navigate to /servers → page renders → logout → redirected to /login |
| T6-02 | **Auth interceptor + login error interaction:** 401 on login page | Mock `login()` returns 401 → error message shown, NOT redirected (prevent double-redirect) |

### 10.2 Trust Posture Cross-Page Flow — 1 test

| # | Test | Assertion |
|---|---|---|
| T6-03 | Select agent class → change trust → verify mutation | Mock `fetchAgentClasses()` returns 2 classes → select one → change trust level on a server → `setTrustAssignment()` called with selected classId, not hardcoded |

### 10.3 Error Boundary Recovery — 2 tests

| # | Test | Assertion |
|---|---|---|
| T6-04 | Child component crash shows fallback UI | Render component that throws → "Something went wrong" + error message visible |
| T6-05 | **Recovery loop:** "Try again" on uncrashable error | Click "Try again" → component re-renders → crashes again → ErrorBoundary re-catches. Verify: user is NOT stuck in an infinite loop — "Go to Dashboard" link is present with `href="/"` |
| T6-06 | **Go to Dashboard navigates away** | Click "Go to Dashboard" → `window.location.href` set to `'/'` |

**Total Layer 6: 5 tests**

---

## 11. Layer 7: Security & Data Leak

> **Effort:** 3h | **Severity:** Critical

These tests validate that MCP Fabric's UI does not expose sensitive data through accidental channels. Every finding in this layer blocks release.

### 11.1 Token Handling — 3 tests

| # | Test | Assertion |
|---|---|---|
| T7-01 | **Token not logged to console:** Verify `console.log` is not called with token value | Spy on `console.log` → exercise full login flow → `console.log` arguments never contain the token string |
| T7-02 | **Token not in React dev tools:** Verify token is not set as a DOM attribute or in component `displayName` | Render app → inspect DOM elements for `token` in `data-*` attributes, `class`, `id` → none match token pattern `fcp_` |
| T7-03 | **Token cleared on logout:** `localStorage` items removed | After `logout()` → `localStorage.getItem('fabric_token')` is null, `fabric_user` is null |

### 11.2 XSS Prevention — 3 tests

| # | Test | Assertion |
|---|---|---|
| T7-04 | **HTML injection in rendered data:** Server name contains `<script>alert('xss')</script>` | Rendered as text, NOT executed. `document.querySelector('script')` is null |
| T7-05 | **HTML injection in audit event details:** `details` JSONB contains malicious HTML | Rendered through React (auto-escaped), not via `dangerouslySetInnerHTML` |
| T7-06 | **URL injection in endpoint field:** Server endpoint `javascript:alert(1)` is set as `href` | Link component handles safely or renders as plain text |

### 11.3 Data Exposure — 2 tests

| # | Test | Assertion |
|---|---|---|
| T7-07 | **No password/secret in error messages:** API returns error with `password` in body | Login form renders generic error, not the raw body |
| T7-08 | **No token_hash exposure:** `AgentIdentity` renders `token_prefix` only | UI displays `fcp_****`, never the full hash or token |

**Total Layer 7: 8 tests**

---

## 12. Layer 8: Edge Case & Resilience

> **Effort:** 4h

### 12.1 Modal Edge Cases — 2 tests

| # | Test | Assertion |
|---|---|---|
| T8-01 | **Focus trap:** Tab cycles within modal, does not reach background | Open modal → tab 3 times → focus remains inside modal (`document.activeElement` is modal child) |
| T8-02 | **Scroll lock:** Body overflow hidden when modal open | `document.body.style.overflow` is `'hidden'` while modal open, restored on close |

### 12.2 Toast Edge Cases — 2 tests

| # | Test | Assertion |
|---|---|---|
| T8-03 | **Rapid toasts:** 10 toasts fired in 100ms | All 10 render, each independently tracked, none lost |
| T8-04 | **Toast auto-dismiss timing:** Each toast dismisses independently at 5s from its creation | Fire toast at t=0, fire another at t=2s → first dismisses at t=5s, second at t=7s |

### 12.3 Table Edge Cases — 2 tests

| # | Test | Assertion |
|---|---|---|
| T8-05 | **Empty array:** Empty data array | Table renders headers only, no rows, no crash |
| T8-06 | **Single row:** One item in data | One row rendered, pagination shows total=1 |

### 12.4 PageState Edge Cases — 2 tests

| # | Test | Assertion |
|---|---|---|
| T8-07 | **Transition: error → loading:** Query transitions from error to refetching | Loading skeleton replaces error state |
| T8-08 | **Transition: populated → loading (refetch):** Query refetches | Existing data is replaced by skeleton during refetch (or `keepPreviousData` is verified) |

### 12.5 Network Resilience — 3 tests

| # | Test | Assertion |
|---|---|---|
| T8-09 | **Fetch throws TypeError (network down):** `fetch()` rejects before response | Error thrown, not caught by 401 interceptor, `logout()` NOT called |
| T8-10 | **Malformed JSON response:** API returns `{invalid` | `res.json()` throws → caught → generic message shown, not crash |
| T8-11 | **Empty response body on error:** API returns 500 with no body | `res.json().catch(() => ({}))` → message falls back to `Request failed: 500` |

### 12.6 Mutation Edge Cases — 4 tests

| # | Test | Assertion |
|---|---|---|
| T8-12 | **Double-click submit:** Two rapid clicks on confirm button before re-render | Mutation function called exactly once (guarded by `isPending`) |
| T8-13 | **Navigate away during mutation:** User clicks register, then immediately navigates to another page | Mutation still completes, toast may show briefly, no error from unmounted component |
| T8-14 | **Non-Error throw in onError:** API client throws a string `'timeout'` instead of `Error` | `addToast` called with `'timeout'` (not `'undefined'`), no runtime crash |
| T8-15 | **Non-Error throw: null rejection** | Caught value is `null`, `.message` would fail → toast shows generic fallback, no crash |

**Total Layer 8: 15 tests**

### 12.7 Optimistic Rollback — 2 tests

| # | Test | Assertion |
|---|---|---|
| T8-16 | **TrustPosture optimistic update:** User changes trust level → dropdown shows new value immediately | `pendingChanges` state updated before API call completes |
| T8-17 | **Rollback on error:** `setTrustAssignment` fails → dropdown reverts to original value, toast shows error | `pendingChanges` entry for serverId removed, dropdown reads from query data again |

---

## 13. Layer 9: Performance Benchmarks (Manual)

> **Effort:** 1h | **Run cadence:** Before each release candidate | **Tool:** Custom benchmark script (`ui/benchmarks/`)

These are manual benchmarks, not CI assertions. jsdom render timings don't reflect real browser performance. Run on a production-like machine, record results in `docs/ui-test/findings/`.

### Benchmark Procedure

```bash
cd ui
npx vitest run benchmarks/ --reporter=json > benchmarks/results.json
# Review results/compare against previous run
```

### Benchmark Scenarios

| # | Scenario | Measure | Threshold (soft) |
|---|---|---|---|
| T9-01 | Render Table with 500 rows | DOM node count, render completion | < 500ms in Chrome, no jank |
| T9-02 | Fire 50 toasts programmatically | All render, container overflow behavior | No crash, scroll within container |
| T9-03 | Full page load: Dashboard with 4 concurrent queries | Time from mount to all skeletons replaced | < 2s (network latency excluded) |

### Pass/Fail Criteria

Benchmarks are advisory. A regression >20% from baseline triggers a review, not a block. Record each run in findings with:
- Date, browser version, OS
- Raw timing values
- Comparison to previous baseline

**Total Layer 9: 3 benchmark scenarios (manual)**

---

## 14. Layer 10: E2E (Docker Compose)

> **Effort:** 3h | **Script file:** `tests/e2e/test_admin_ui.sh`

These are curl-based smoke scripts that run against `docker-compose up`. Not automated in CI initially — run manually before release.

| # | Test | Assertion |
|---|---|---|
| T10-01 | Health check | `curl /v1/health` returns 200 with `healthy` |
| T10-02 | Admin login | `POST /auth/admin/login` with bootstrap creds returns token |
| T10-03 | Register server → verify in list | `POST /servers` → `GET /servers` includes the new server |
| T10-04 | Create capability → map tool → list | `POST /capabilities` → `POST /capabilities/{id}/mappings` → verify in list |
| T10-05 | Full request lifecycle | Token → connect → capability request → verify audit event |
| T10-06 | UI static build | `npm run build` succeeds, dist/ directory populated |

**Total Layer 10: 6 tests**

---

## 15. Test Data Matrix

### Mock Server Tool Definitions

Used by integration and E2E tests. Defined in `tests/fixtures/mock_mcp_server.py` (backend) but needed in UI tests as mock API response shapes.

| Server | Tools | Trust Default |
|---|---|---|
| KB Server | `search_kb(query, max_results)`, `get_article(id)`, `list_categories()`, `ask_question(query)` | trusted |
| Code Search | `search_code(query, file_pattern, max_results)`, `search_symbols(query)` | trusted |
| Git History | `git_diff(repo, since, until)`, `git_log(repo, max_count)`, `git_status(repo)` | trusted |
| Deployment | `deploy(service, env, version)`, `rollback(service, env)`, `health_check(service)` | restricted |
| Vulnerability Scanner | `scan(service, depth)`, `list_dependencies(service)`, `check_deprecation(dependency)` | approval-gated |

### Mock API Response Data

Place in `ui/src/test/fixtures/`:

```typescript
// ui/src/test/fixtures/servers.ts
export const mockServers = {
  items: [
    {
      id: 'srv-1',
      name: 'KB Server',
      endpoint: 'http://localhost:3001',
      owner_team: 'platform',
      labels: ['knowledge', 'internal'],
      trust_level: 'trusted' as const,
      health_status: 'healthy' as const,
      team_namespace: 'team:platform',
      decommissioned_at: null,
      created_at: '2026-07-01T00:00:00Z',
    },
    // ... more fixtures
  ],
  pagination: { total: 1, has_more: false, per_page: 50 },
}
```

---

## 16. Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Test Coverage |
|---|---|---|---|---|---|
| R1 | localStorage poison crashes app on load | Low | High | Catch `JSON.parse` in authStore init | T2-03 |
| R2 | Token displayed in console or DOM by accident | Low | Critical | Lint rule + manual inspection + T7-01/T7-02 | T7-01, T7-02 |
| R3 | Rapid double-click submits duplicate mutations | Medium | Medium | `isPending` guard + test | T8-12 |
| R4 | Modal focus leak to background elements | Medium | Medium | Focus trap implementation + test | T8-01 |
| R5 | XSS via server-controlled data (name, endpoint) | Low | Critical | React auto-escape + audit log test | T7-04, T7-05, T7-06 |
| R6 | Stale cursor after concurrent data mutation | Medium | Low | API handles gracefully; user refreshes | Not covered (API-side) |
| R7 | Error boundary infinite recovery loop | Low | Medium | Default fallback prevents browser white screen | T6-05 |
| R8 | Login page double-redirect on 401 | Low | Medium | Interceptor skips logout for login endpoint | T2-12, T6-02 |
| R9 | 401 interceptor fires during login | Medium | Medium | Conditional check: skip if path is `/auth/login` | T2-12 |
| R10 | Toast ID overflow in long sessions | Very Low | Low | Use `crypto.randomUUID()` instead of incrementing counter | T8-03 |

---

## 17. Findings Log

> Test findings are captured in `docs/ui-test/findings/YYYY-MM-DD-<title>.md`.

### Finding Template

```markdown
# Finding: <short title>

**Date:** YYYY-MM-DD  
**Test:** T<layer>-<number>  
**Severity:** Critical / Important / Minor  
**Status:** Open / Fixed / WontFix

## Description
What was found.

## Reproduction
Steps to reproduce (or test that failed).

## Evidence
- Error message / stack trace
- Screenshot (if applicable)

## Root Cause
Why it happened.

## Fix
What was changed to fix it (or why WontFix).

## Regression Test
How we'll catch this in the future.
```

### Linked Issues

Each finding that results in a code change must have a corresponding GitHub issue labeled `type:bug` or `type:security`.

---

## Appendix A: Test Execution

### Local Run

```bash
cd ui
npm test              # Watch mode
npm test -- --run     # Single run
npm test -- --coverage  # With coverage
```

### CI (GitHub Actions)

```yaml
# Added to .github/workflows/ci.yml
test-ui:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with: { node-version: "20" }
    - run: cd ui && npm ci
    - run: cd ui && npm test -- --run --coverage
    - uses: codecov/codecov-action@v4
      with: { flags: ui, file: ./ui/coverage/lcov.info }
```

### Pre-Commit Check

```bash
cd ui && npm run typecheck && npm test -- --run
```

---

## Appendix B: Test Progress Tracker

| Layer | Tests | Written | Passing | Coverage |
|---|---|---|---|---|
| 0: Infrastructure | 5 | — | — | — |
| 1: Shared Components | 37 | — | — | — |
| 2: Auth & Session | 12 | — | — | — |
| 3: API Client | 10 | — | — | — |
| 4: Page Smoke Tests | 34 | — | — | — |
| 5: Navigation & Routing | 7 | — | — | — |
| 6: Integration Flows | 5 | — | — | — |
| 7: Security & Data Leak | 8 | — | — | — |
| 8: Edge Case & Resilience | 13 | — | — | — |
| 9: Performance | 2 | — | — | — |
| 10: E2E (Docker Compose) | 6 | — | — | — |
| **Total** | **145** | **0** | **0** | **0%** |
