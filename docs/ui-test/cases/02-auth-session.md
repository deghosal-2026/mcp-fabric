# UI Test Cases — Auth & Session

> **Area:** Auth & Session  
> **Plan reference:** Layer 2 (12 tests), expanded to 17  
> **Test prefix:** `TC-AUTH`  
> **Last updated:** 2026-07-24

---

## 1. Auth Store

### TC-AUTH-001: Store initializes token and user from localStorage

**Description:** The Zustand auth store reads persisted `fabric_token` and `fabric_user` from localStorage when the store is created. This ensures a page refresh or tab restoration preserves the authenticated session without requiring re-login.

**Severity:** Critical

**Preconditions:**
- localStorage is empty before test (cleared in test setup)

**Test Steps:**
1. Set `localStorage.setItem('fabric_token', 'fcp_live_abc123def456')`
2. Set `localStorage.setItem('fabric_user', JSON.stringify({ id: 'usr-1', username: 'admin', role: 'admin', team_namespace: 'team:platform', mfa_enabled: true }))`
3. Import/create `useAuthStore` (or call `useAuthStore.getState()`)
4. Read `token` and `user` from the store

**Expected Results:**
- `useAuthStore.getState().token` equals `'fcp_live_abc123def456'`
- `useAuthStore.getState().user` is an object with `id: 'usr-1'`, `username: 'admin'`, `role: 'admin'`
- The user object matches the `AuthUser` interface shape exactly

---

### TC-AUTH-002: Store initializes with null when localStorage is empty

**Description:** A fresh browser session with no persisted credentials must initialize the store with `null` values. The app must not assume a user is logged in.

**Severity:** Critical

**Preconditions:**
- All localStorage items cleared

**Test Steps:**
1. Confirm `localStorage.getItem('fabric_token')` is `null`
2. Confirm `localStorage.getItem('fabric_user')` is `null`
3. Import/create `useAuthStore`
4. Read store state

**Expected Results:**
- `useAuthStore.getState().token` is `null`
- `useAuthStore.getState().user` is `null`

---

### TC-AUTH-003: localStorage poison — invalid JSON in fabric_user

**Description:** If the `fabric_user` localStorage key contains corrupted data (e.g., truncated JSON, stray characters, or manual tampering), the store must catch the `JSON.parse` error, remove the corrupt key, and set `user` to `null`. The app must not crash or enter an undefined state.

**Severity:** Critical

**Preconditions:**
- `fabric_token` set to a valid token string
- `fabric_user` set to an invalid JSON string (e.g., truncated: `'{"id": "usr-1", "username"'`)

**Test Steps:**
1. Set `localStorage.setItem('fabric_token', 'fcp_live_validtoken')`
2. Set `localStorage.setItem('fabric_user', '{"id": "usr-1", "username":')`  (truncated/invalid JSON)
3. Import/create `useAuthStore`
4. Read store state
5. Check localStorage after store creation

**Expected Results:**
- `useAuthStore.getState().token` equals `'fcp_live_validtoken'` (token is unaffected)
- `useAuthStore.getState().user` is `null` (parse failure handled gracefully)
- `localStorage.getItem('fabric_user')` is `null` (corrupt key removed)
- No exception is thrown during store creation

**Additional test variants (pick one or parameterize):**
- `fabric_user` = `'not-json-at-all'`
- `fabric_user` = `'null'` (JSON literal `null` → `null` is valid JSON, but the function returns `null` from the `JSON.parse` ternary — verify the store has `null` user)
- `fabric_user` = `'{"id": 123}'` (valid JSON but wrong shape — this will parse successfully and be stored; the store does not validate shape)

---

### TC-AUTH-004: login() persists token and user to store and localStorage

**Description:** When `login()` is called after a successful API authentication, the token and user must be saved both in the Zustand store and in localStorage for session persistence.

**Severity:** Critical

**Preconditions:**
- Auth store initialized (token and user are both `null`)

**Test Steps:**
1. Call `useAuthStore.getState().login('fcp_live_newtoken456', { id: 'usr-2', username: 'editor', role: 'editor', team_namespace: 'team:security', mfa_enabled: false })`
2. Read store state
3. Read localStorage values

**Expected Results:**
- `useAuthStore.getState().token` equals `'fcp_live_newtoken456'`
- `useAuthStore.getState().user` matches the provided `AuthUser` object
- `localStorage.getItem('fabric_token')` equals `'fcp_live_newtoken456'`
- `localStorage.getItem('fabric_user')` equals the stringified JSON of the user object
- `JSON.parse(localStorage.getItem('fabric_user')!)` deep-equals the original user object

---

### TC-AUTH-005: logout() clears token and user from store and localStorage

**Description:** When `logout()` is called (from TopBar click or 401 interceptor), the token and user must be removed from both the store and localStorage. No session residue may remain.

**Severity:** Critical

**Preconditions:**
- Store has an active session (`token` and `user` set)

**Test Steps:**
1. Call `useAuthStore.getState().login('fcp_live_tokentoclear', { id: 'usr-3', username: 'viewer', role: 'viewer', team_namespace: 'team:ops', mfa_enabled: false })`
2. Verify preconditions (token and user are set)
3. Call `useAuthStore.getState().logout()`
4. Read store state and localStorage

**Expected Results:**
- `useAuthStore.getState().token` is `null`
- `useAuthStore.getState().user` is `null`
- `localStorage.getItem('fabric_token')` is `null`
- `localStorage.getItem('fabric_user')` is `null`

---

### TC-AUTH-006: isAuthenticated() returns true when token is present

**Description:** `isAuthenticated()` must return `true` when a non-null token exists in the store. This is the primary guard function used by the router and Layout component.

**Severity:** Critical

**Preconditions:**
- Store initialized with no token

**Test Steps:**
1. Verify `useAuthStore.getState().isAuthenticated()` returns `false` initially
2. Call `useAuthStore.getState().login('fcp_live_authcheck', { id: 'usr-4', username: 'test', role: 'viewer', team_namespace: 'team:test', mfa_enabled: false })`
3. Call `useAuthStore.getState().isAuthenticated()`

**Expected Results:**
- After login: `isAuthenticated()` returns `true`

---

### TC-AUTH-007: isAuthenticated() returns false when token is null

**Description:** `isAuthenticated()` must return `false` after logout or when no token has been set. This triggers the login redirect.

**Severity:** Critical

**Preconditions:**
- Store has an active session

**Test Steps:**
1. Login with a valid token
2. Verify `isAuthenticated()` returns `true`
3. Call `useAuthStore.getState().logout()`
4. Call `useAuthStore.getState().isAuthenticated()`

**Expected Results:**
- After logout: `isAuthenticated()` returns `false`

**Edge case:**
- Call `isAuthenticated()` on a freshly created store with empty localStorage: returns `false`

---

## 2. Login Page — Initial Form

### TC-AUTH-008: LoginPage renders username and password form with disabled submit

**Description:** The LoginPage must render two text inputs (username and password) and a submit button. The submit button must be disabled when either field is empty to prevent submission of incomplete credentials.

**Severity:** Critical

**Preconditions:**
- `login()` API function mocked to avoid actual network calls
- `useAuthStore` initialized with null token

**Test Steps:**
1. Render `<LoginPage />`
2. Find the username input field
3. Find the password input field
4. Find the submit button
5. Check submit button disabled state

**Expected Results:**
- Username input is present (input with no `type="password"`)
- Password input is present (input with `type="password"`)
- Submit button is visible with text "Login"
- Submit button has `disabled` attribute (because both fields are empty)
- The form heading "MCP Fabric" is visible

---

### TC-AUTH-009: Submit button enables when both fields have values

**Description:** Once the user types into both username and password fields, the submit button must become enabled to allow form submission.

**Severity:** Normal

**Preconditions:**
- `login()` API function mocked
- LoginPage rendered

**Test Steps:**
1. Type `'admin'` into the username input
2. Type `'password123'` into the password input
3. Check the submit button disabled state

**Expected Results:**
- Submit button does NOT have the `disabled` attribute
- Submit button text is "Login"

---

### TC-AUTH-010: Submit calls login() API with correct credentials

**Description:** On form submission, the `login()` API function must be called with the exact values from the username and password inputs.

**Severity:** Critical

**Preconditions:**
- `login()` mocked to return `{ token: 'fcp_live_mocked', user: { id: 'usr-5', username: 'admin', role: 'admin', team_namespace: 'team:platform', mfa_enabled: true }, mfa_required: false }`
- LoginPage rendered with user typing enabled

**Test Steps:**
1. Type `'admin'` into the username field
2. Type `'s3cret!' into` the password field
3. Click the "Login" submit button
4. Wait for the API call to resolve

**Expected Results:**
- `login()` was called exactly once
- `login()` was called with arguments `('admin', 's3cret!')`

---

### TC-AUTH-011: Successful login persists token and navigates to dashboard

**Description:** After a successful (non-MFA) login API response, the store must be populated with the returned token and user, and the browser must navigate to the `/` route.

**Severity:** Critical

**Preconditions:**
- `login()` mocked to return `{ token: 'fcp_live_mocked_login', user: { id: 'usr-6', username: 'admin', role: 'admin', team_namespace: 'team:platform', mfa_enabled: false }, mfa_required: false }`
- `useNavigate` mocked from react-router-dom
- LoginPage rendered

**Test Steps:**
1. Type `'admin'` and `'pass'` into the fields
2. Click the Login button
3. Wait for all promises to resolve

**Expected Results:**
- `login()` resolves successfully
- `useAuthStore.getState().token` equals `'fcp_live_mocked_login'`
- `useAuthStore.getState().user.username` equals `'admin'`
- `navigate` was called with `'/'`
- The URL would be `/` (dashboard)

---

### TC-AUTH-012: LoginPage shows error message on API failure

**Description:** When the `login()` API call throws an error (e.g., wrong credentials, server error), the error message must be displayed in the UI. The form fields must remain visible so the user can retry.

**Severity:** Critical

**Preconditions:**
- `login()` mocked to reject with `new Error('Invalid username or password')`
- LoginPage rendered

**Test Steps:**
1. Type `'wrong'` and `'creds'` into the fields
2. Click the Login button
3. Wait for the rejected promise

**Expected Results:**
- An error message is visible on screen: "Invalid username or password"
- The error is rendered inside a `div` with red styling (`bg-red-50 text-red-600`)
- The username input is still present and unchanged
- The password input is still present
- The submit button is re-enabled (loading state cleared)
- `navigate` was NOT called
- `useAuthStore.getState().token` is still `null` (no login occurred)

---

### TC-AUTH-013: LoginPage shows generic error for non-Error throws

**Description:** When the API client throws something that is not an `Error` instance (e.g., a string `'timeout'` or a plain object), the LoginPage must display a fallback message rather than crashing or showing `undefined`.

**Severity:** Important

**Preconditions:**
- `login()` mocked to throw a string `'Network failure'` (or similar non-Error value)
- LoginPage rendered

**Test Steps:**
1. Type `'admin'` and `'pass'` into the fields
2. Click the Login button
3. Wait for the catch block to execute

**Expected Results:**
- An error message is visible: "Login failed" (the fallback string)
- The app does not crash
- No `undefined` text is rendered

---

## 3. Login Page — MFA Flow

### TC-AUTH-014: MFA Step 1 — login() returns mfa_required=true, shows MFA code input

**Description:** If the user has MFA enabled, the `login()` API returns `mfa_required: true` along with a temporary MFA token. The LoginPage must switch from the username/password form to an MFA code input form, hiding the original credentials form.

**Severity:** Critical

**Preconditions:**
- `login()` mocked to return `{ token: 'mfa_temp_token_xyz', user: null, mfa_required: true }`
- LoginPage rendered

**Test Steps:**
1. Type `'admin'` and `'pass'` into the fields
2. Click the Login button
3. Wait for the API response

**Expected Results:**
- The username input is no longer visible in the DOM
- The password input is no longer visible in the DOM
- The original submit button ("Login") is no longer visible
- A new form element is rendered with:
  - Label text: "Authentication Code"
  - An input field with placeholder "Enter 6-digit code"
  - A submit button with text "Verify"
- The "MCP Fabric" heading remains visible
- `useAuthStore.getState().token` is still `null` (final login not yet complete)
- `login()` was called exactly once with `('admin', 'pass')`

---

### TC-AUTH-015: MFA verify button disabled when code is fewer than 6 characters

**Description:** MFA codes are typically 6 digits. The Verify button must be disabled until the user has entered at least 6 characters to prevent premature submission of an incomplete code.

**Severity:** Normal

**Preconditions:**
- LoginPage is in MFA state (after `login()` returned `mfa_required: true`)

**Test Steps:**
1. Type `'123'` into the MFA code input (only 3 characters)
2. Check the Verify button's disabled state
3. Type `'456'` to complete 6 characters (`'123456'`)
4. Check the Verify button's disabled state again

**Expected Results:**
- After step 2: Verify button is disabled (`disabled` attribute present)
- After step 4: Verify button is enabled (`disabled` attribute absent)
- Button text is "Verify"

---

### TC-AUTH-016: MFA Step 2 — verifyMfa() succeeds, login() called, navigates to /

**Description:** After the user enters a valid 6-digit MFA code, `verifyMfa()` must be called with the temporary token and the code. On success, the response token must be passed to the store's `login()`, and the user must be navigated to the dashboard.

**Severity:** Critical

**Preconditions:**
- LoginPage in MFA state (mfaToken set to `'mfa_temp_token_xyz'`)
- `verifyMfa()` mocked to return `{ token: 'fcp_live_post_mfa', user: { id: 'usr-7', username: 'admin', role: 'admin', team_namespace: 'team:platform', mfa_enabled: true } }`
- `navigate` mocked

**Test Steps:**
1. Type `'123456'` into the MFA code input
2. Click the Verify button
3. Wait for the API call to resolve

**Expected Results:**
- `verifyMfa()` was called exactly once with arguments `('mfa_temp_token_xyz', '123456')`
- `useAuthStore.getState().token` equals `'fcp_live_post_mfa'`
- `useAuthStore.getState().user.username` equals `'admin'`
- `navigate` was called with `'/'`

---

### TC-AUTH-017: MFA invalid code — error shown, stays on MFA page

**Description:** When the user enters an incorrect MFA code, the `verifyMfa()` call rejects. An error message must be displayed, and the user must remain on the MFA code form (not navigate away or return to credentials form).

**Severity:** Critical

**Preconditions:**
- LoginPage in MFA state
- `verifyMfa()` mocked to reject with `new Error('Invalid authentication code')`

**Test Steps:**
1. Type `'000000'` into the MFA code input
2. Click the Verify button
3. Wait for the rejected promise

**Expected Results:**
- An error message is visible: "Invalid authentication code"
- The MFA code input is still visible and contains `'000000'` (or is cleared — either behavior is acceptable; verify by testing input value after error)
- The Verify button is re-enabled
- The username/password form is NOT shown (user stays on MFA form)
- `navigate` was NOT called
- `useAuthStore.getState().token` is still `null` (login incomplete)

---

## 4. API Client — 401 Interceptor

### TC-AUTH-018: 401 interceptor skips /auth/ endpoints

**Description:** When an API call to an `/auth/*` endpoint receives a 401 response (e.g., invalid credentials during login), the fetcher must NOT call `logout()` or redirect to `/login`. This prevents a double-redirect loop where the login page sends the user back to the login page.

**Severity:** Critical

**Preconditions:**
- `useAuthStore.getState().token` is `'some_token'`
- `fetch()` mock returns a Response with `status: 401` for path `/auth/login`
- Spy on `useAuthStore.getState().logout`

**Test Steps:**
1. Call the internal `fetcher` function (or `login()` which calls fetcher) with path `/auth/login`
2. Catch the thrown error
3. Check if `logout()` was called
4. Check if `window.location.href` was set

**Expected Results:**
- `logout()` was NOT called
- `window.location.href` was NOT changed to `/login`
- An error is thrown with message matching the API response body (or `Request failed: 401`)

---

### TC-AUTH-019: 401 interceptor fires logout + redirect for non-auth endpoints

**Description:** When any non-auth API endpoint (e.g., `/servers`, `/capabilities`) returns a 401, the user's session has expired. The fetcher must clear the session and redirect to the login page.

**Severity:** Critical

**Preconditions:**
- `useAuthStore.getState()` has a valid token `'fcp_live_expired'`
- `useAuthStore.getState().logout` is spied on
- `fetch()` mock returns a Response with `status: 401` for path `/servers`

**Test Steps:**
1. Call the internal `fetcher` function (or `fetchServers()`) with path `/servers`
2. Catch the thrown error (the redirect may happen synchronously)

**Expected Results:**
- `useAuthStore.getState().logout()` was called exactly once
- `window.location.href` was set to `'/login'`
- An error is thrown with message `'Unauthorized'`

---

### TC-AUTH-020: 401 interceptor does not fire for network errors (no response)

**Description:** If `fetch()` itself throws (network failure, DNS error, CORS) before receiving any response, the 401 interceptor must not fire. No `logout()` should occur due to a network issue.

**Severity:** Important

**Preconditions:**
- `fetch()` mock rejects with a `TypeError('Failed to fetch')` (no response object)
- Spy on `logout()`

**Test Steps:**
1. Call the internal `fetcher` function with path `/servers`
2. Catch the propagated error

**Expected Results:**
- `logout()` was NOT called
- `window.location.href` was NOT changed
- The error propagates as-is (it's the caller's responsibility to handle it)

---

## 5. Layout — Route Guard

### TC-AUTH-021: Layout redirects to /login when no token is present

**Description:** The Layout component is the root wrapper for all authenticated pages. When no token exists (user is not logged in), it must render a `<Navigate to="/login" replace />` instead of the authenticated UI shell.

**Severity:** Critical

**Preconditions:**
- `useAuthStore.getState().token` is `null`
- MemoryRouter used (to avoid full page navigation)

**Test Steps:**
1. Render `<Layout />` inside a `<MemoryRouter>` (no routes needed, just the component)
2. Check rendered output

**Expected Results:**
- `<Navigate to="/login" replace />` renders (detectable by React Router's Navigate component behavior)
- The Sidebar is NOT rendered
- The TopBar is NOT rendered
- `<Outlet />` is NOT rendered
- If using test assertions: `screen.queryByText('MCP Fabric')` may exist (from LoginPage if that route is configured) or be absent; the key assertion is that the layout renders a Navigate component and NOT the authenticated layout

---

### TC-AUTH-022: Layout renders Sidebar, TopBar, and Outlet when token is present

**Description:** When the user has a valid token, the Layout must render the full admin shell: Sidebar, TopBar, and the `<Outlet />` for nested route content.

**Severity:** Critical

**Preconditions:**
- `useAuthStore.getState().token` is `'fcp_live_valid'`
- `useAuthStore.getState().user` is `{ id: 'usr-8', username: 'admin', role: 'admin', team_namespace: 'team:platform', mfa_enabled: false }`
- MemoryRouter with at least one route for Outlet to match (e.g., `<Route path="/" element={<Layout />}><Route index element={<div>Dashboard Content</div>} /></Route>`)

**Test Steps:**
1. Render the Layout with routing setup as above inside MemoryRouter
2. Check for authenticated elements

**Expected Results:**
- Sidebar is rendered: "MCP Fabric" sidebar heading is visible
- TopBar is rendered: "Welcome, admin" text is visible
- The `role` badge "admin" is visible in the TopBar
- Outlet content visible: "Dashboard Content" is rendered
- No redirect to `/login` occurs

---

## 6. TopBar — Logout

### TC-AUTH-023: Logout button in TopBar clears session and navigates to /login

**Description:** Clicking the "Logout" button in the TopBar must call `logout()` on the auth store (clearing store state and localStorage) and immediately navigate to the login page.

**Severity:** Critical

**Preconditions:**
- `useAuthStore` has an active session (token + user set)
- `useNavigate` mocked
- Layout (or TopBar alone) rendered

**Test Steps:**
1. Render the TopBar (or Layout that includes TopBar) with authenticated store state
2. Find the Logout button (text: "Logout")
3. Click the Logout button

**Expected Results:**
- `useAuthStore.getState().token` is `null`
- `useAuthStore.getState().user` is `null`
- `navigate` was called with `'/login'`

---

### TC-AUTH-024: TopBar displays current username and role

**Description:** The TopBar shows the logged-in user's username and role as a visual indicator of who is currently authenticated and their permission level.

**Severity:** Normal

**Preconditions:**
- Store has user: `{ id: 'usr-9', username: 'jdoe', role: 'editor', team_namespace: 'team:security', mfa_enabled: true }`

**Test Steps:**
1. Render `<TopBar />` (inside a MemoryRouter for the Navigate call)
2. Look for user information

**Expected Results:**
- Text "Welcome, jdoe" is visible
- A badge or tag with text "editor" is visible
- No text "Welcome, undefined" or "Welcome, null" is rendered

---

## Summary

| ID | Test | Source | Severity |
|---|---|---|---|
| TC-AUTH-001 | Store initializes token and user from localStorage | `authStore.ts:23-24` | Critical |
| TC-AUTH-002 | Store initializes with null when localStorage is empty | `authStore.ts:23-24` | Critical |
| TC-AUTH-003 | localStorage poison — invalid JSON in fabric_user | `authStore.ts:12-19` | Critical |
| TC-AUTH-004 | login() persists token and user to store and localStorage | `authStore.ts:26-29` | Critical |
| TC-AUTH-005 | logout() clears token and user from store and localStorage | `authStore.ts:32-36` | Critical |
| TC-AUTH-006 | isAuthenticated() returns true when token is present | `authStore.ts:38-40` | Critical |
| TC-AUTH-007 | isAuthenticated() returns false when token is null | `authStore.ts:38-40` | Critical |
| TC-AUTH-008 | LoginPage renders username and password form with disabled submit | `Login.tsx:79-106` | Critical |
| TC-AUTH-009 | Submit button enables when both fields have values | `Login.tsx:101` | Normal |
| TC-AUTH-010 | Submit calls login() API with correct credentials | `Login.tsx:16-32` | Critical |
| TC-AUTH-011 | Successful login persists token and navigates to dashboard | `Login.tsx:21-27` | Critical |
| TC-AUTH-012 | LoginPage shows error message on API failure | `Login.tsx:28-29` | Critical |
| TC-AUTH-013 | LoginPage shows generic error for non-Error throws | `Login.tsx:29` | Important |
| TC-AUTH-014 | MFA step 1 — login() returns mfa_required, shows code input | `Login.tsx:22-24` | Critical |
| TC-AUTH-015 | MFA verify button disabled when code < 6 characters | `Login.tsx:72` | Normal |
| TC-AUTH-016 | MFA step 2 — verifyMfa() succeeds, login(), navigate to / | `Login.tsx:35-47` | Critical |
| TC-AUTH-017 | MFA invalid code — error shown, stays on MFA page | `Login.tsx:43-44` | Critical |
| TC-AUTH-018 | 401 interceptor skips /auth/ endpoints | `client.ts:25` | Critical |
| TC-AUTH-019 | 401 interceptor fires logout + redirect for non-auth endpoints | `client.ts:25-28` | Critical |
| TC-AUTH-020 | 401 interceptor does not fire for network errors (no response) | `client.ts:25` | Important |
| TC-AUTH-021 | Layout redirects to /login when no token | `Layout.tsx:9-11` | Critical |
| TC-AUTH-022 | Layout renders Sidebar, TopBar, Outlet when token present | `Layout.tsx:13-23` | Critical |
| TC-AUTH-023 | Logout button in TopBar clears session and navigates to /login | `TopBar.tsx:9-12` | Critical |
| TC-AUTH-024 | TopBar displays current username and role | `TopBar.tsx:16-20` | Normal |

**Total test cases: 24**
