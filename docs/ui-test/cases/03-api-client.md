# UI Test Cases — API Client

> **Area:** API Client (`ui/src/api/client.ts`)  
> **Plan reference:** Layer 3 (18 tests)  
> **Test prefix:** `TC-API`  
> **Last updated:** 2026-07-24

---

## 1. fetcher — Auth & Headers

### TC-API-001: Fetcher attaches auth header when token exists

**Description:** When a valid token is present in the auth store, the fetcher must attach it as an `Authorization: Bearer <token>` header on every outgoing request. Without this, all authenticated API calls would receive 401 responses.

**Severity:** Critical

**Preconditions:**
- `useAuthStore.getState().token` returns a valid token string (e.g., `"fcp_abc123"`)
- Global `fetch` is mocked via `vi.fn()` to return a successful `Response` (status 200, JSON body `{}`)

**Test Steps:**
1. Mock `useAuthStore.getState` to return `{ token: "fcp_abc123" }`
2. Call `fetcher('/servers')` (imported internally; test via a public function like `fetchServers()` or mock at module boundaries)
3. Inspect the first argument of the mocked `fetch` call (the URL) and the second argument (the options object)

**Expected Results:**
- `fetch` is called with `'/v1/servers'` as the URL
- The `headers` property of the options object contains `Authorization: Bearer fcp_abc123`
- The request succeeds (no error thrown)

---

### TC-API-002: Fetcher omits auth header when no token

**Description:** When the auth store has no token (`null` or `undefined`), the fetcher must not set an `Authorization` header. This covers the unauthenticated state, relevant for pre-login pages that call `/auth/*` endpoints.

**Severity:** Critical

**Preconditions:**
- `useAuthStore.getState().token` returns `null`
- Global `fetch` mocked to return a successful 200 response

**Test Steps:**
1. Mock `useAuthStore.getState` to return `{ token: null }`
2. Call `fetcher('/auth/login', { method: 'POST', body: '{}' })`
3. Inspect the headers object of the fetch call

**Expected Results:**
- The `headers` object does NOT contain an `Authorization` key
- All default headers (`Content-Type`, `Accept`) are still present

---

### TC-API-003: Fetcher sets Content-Type and Accept headers

**Description:** Every request must include `Content-Type: application/json` and `Accept: application/vnd.fabric.v1+json` headers. The custom Accept MIME type is how the backend identifies the API version for the admin UI.

**Severity:** Important

**Preconditions:**
- `useAuthStore.getState().token` returns any value (null or a token; the auth header is not relevant here)
- Global `fetch` mocked to return a 200 response

**Test Steps:**
1. Call `fetcher('/health')` with no additional headers
2. Inspect the headers in the fetch options

**Expected Results:**
- `headers['Content-Type']` equals `'application/json'`
- `headers['Accept']` equals `'application/vnd.fabric.v1+json'`

---

### TC-API-004: Fetcher 401 on /auth/ path skips logout and redirect

**Description:** Auth endpoints (paths starting with `/auth/`) may legitimately return 401 during login with invalid credentials. The fetcher must NOT call `logout()` or redirect to `/login` in this case, as that would create a double-logout loop and prevent the login page from showing error messages.

**Severity:** Critical

**Preconditions:**
- Spy on `useAuthStore.getState().logout`
- Spy on `window.location.href` assignment
- Mock global `fetch` to return a `Response` with status 401 and body `{ "message": "Invalid credentials" }`

**Test Steps:**
1. Call `fetcher('/auth/login', { method: 'POST', body: '{"username":"admin","password":"wrong"}' })`

**Expected Results:**
- The promise rejects with an `Error`
- `useAuthStore.getState().logout` is NOT called
- `window.location.href` is NOT modified
- The error message equals `"Invalid credentials"` (parsed from the error body)

---

### TC-API-005: Fetcher 401 on non-auth calls logout and redirects

**Description:** When any non-auth API call (e.g., `/servers`, `/capabilities`) returns a 401 status, the user's session has expired or their token is invalid. The fetcher must immediately clear the auth state and redirect to the login page.

**Severity:** Critical

**Preconditions:**
- Spy on `useAuthStore.getState().logout`
- Spy on `window.location.href` (mocked via Object.defineProperty or vi.stubGlobal)
- Mock global `fetch` to return a `Response` with status 401 and body `{ "message": "Unauthorized" }`

**Test Steps:**
1. Call `fetcher('/servers')` (path does NOT start with `/auth/`)

**Expected Results:**
- The promise rejects with `Error("Unauthorized")`
- `useAuthStore.getState().logout()` is called exactly once
- `window.location.href` is set to `'/login'`

---

## 2. fetcher — Error Handling

### TC-API-006: Fetcher parses error body on non-OK response

**Description:** When the API returns a 4xx or 5xx status with a JSON error body containing a `message` field, the fetcher must parse that field and throw it as an `Error` with the API-provided message. This enables consumer code to display the server's error message directly.

**Severity:** Critical

**Preconditions:**
- Mock global `fetch` to return a `Response` with status 400 and JSON body `{ "message": "bad request" }`

**Test Steps:**
1. Call `fetcher('/servers')` wrapped in a try/catch or expect reject

**Expected Results:**
- The promise rejects
- The rejected error is an instance of `Error`
- `error.message` equals `"bad request"`

---

### TC-API-007: Fetcher handles empty error body

**Description:** Some server errors (especially 500s) may return no response body or an empty body. The fetcher must handle this gracefully by falling back to a generic error message using the HTTP status code.

**Severity:** Important

**Preconditions:**
- Mock global `fetch` to return a `Response` with status 500 and an empty body (or a body that, when read via `.json()`, results in an empty object `{}`)
- The body must be valid JSON (e.g., return a `Response` with body `''` and then ensure `.json()` resolves to `{}`; one approach is to return `new Response('', { status: 500 })` and let `.json()` reject, which triggers the `.catch(() => ({}))` fallback)

**Test Steps:**
1. Call `fetcher('/servers')`

**Expected Results:**
- The promise rejects
- `error.message` equals `"Request failed: 500"`

---

### TC-API-008: Fetcher handles network failure (fetch rejects)

**Description:** If the network is unreachable, DNS fails, or the request is aborted, the native `fetch()` function rejects with a `TypeError`. The fetcher has no try/catch around `fetch()` itself, so this error must propagate as an unhandled promise rejection. Crucially, the 401 interceptor must NOT fire because there is no response object.

**Severity:** Critical

**Preconditions:**
- Mock global `fetch` to reject with a `TypeError('Failed to fetch')` — NOT returning a Response object
- Spy on `useAuthStore.getState().logout`

**Test Steps:**
1. Call `fetcher('/servers')`

**Expected Results:**
- The promise rejects with a `TypeError('Failed to fetch')`
- `useAuthStore.getState().logout()` is NOT called (no response object, so status check never executes)
- `window.location.href` is NOT modified

---

### TC-API-009: Fetcher handles malformed JSON response on error

**Description:** If the server returns a 500 status with an invalid JSON body (e.g., truncated response `{invalid`), the call to `res.json()` will reject. The fetcher must catch this `.json()` failure and fall back to an empty object, then produce a generic error message using the status code.

**Severity:** Important

**Preconditions:**
- Mock global `fetch` to return a `Response` with status 500 and a body that produces invalid JSON when `res.json()` is called (e.g., return a `Response` with a stream that yields the string `"{invalid"`)

**Test Steps:**
1. Call `fetcher('/servers')`

**Expected Results:**
- The promise rejects
- `error.message` equals `"Request failed: 500"`
- No unhandled promise rejection or crash occurs

---

## 3. fetcher — Custom Options & Request Passthrough

### TC-API-010: Fetcher passes through custom options and merges headers

**Description:** The fetcher's second argument (`options?: RequestInit`) must be passed through to `fetch()` as the basis for the request. Custom headers in `options.headers` must be merged with (and override) the defaults. This allows callers to set extra headers like `X-Idempotency-Key` or override `Content-Type` for endpoints that need different behavior.

**Severity:** Important

**Preconditions:**
- Mock global `fetch` to return a 200 response

**Test Steps:**
1. Call `fetcher('/servers', { method: 'POST', headers: { 'X-Custom': 'value', 'Content-Type': 'application/xml' } })`

**Expected Results:**
- `fetch` is called with method `'POST'`
- The merged headers contain:
  - `Content-Type`: `'application/xml'` (custom override wins over default `'application/json'`)
  - `Accept`: `'application/vnd.fabric.v1+json'` (default preserved)
  - `X-Custom`: `'value'` (custom header added)
- If a token exists, `Authorization` header is also present

---

## 4. buildQuery

### TC-API-011: buildQuery builds correct query string from params

**Description:** The `buildQuery` utility constructs a URL query string from a record of key-value pairs. Multiple params must produce a properly encoded `?key=value&key2=value2` string.

**Severity:** Critical

**Preconditions:**
- `buildQuery` function imported directly from `client.ts`

**Test Steps:**
1. Call `buildQuery('/servers', { a: '1', b: '2' })`

**Expected Results:**
- Returns `'/servers?a=1&b=2'`
- Query parameters are URL-encoded (e.g., if values contain special chars, they are encoded)

---

### TC-API-012: buildQuery skips undefined params

**Description:** When a params object contains keys with `undefined` values, those keys must be excluded from the resulting query string. This allows callers to pass dynamic filter objects where some filters are not set without producing `?key=undefined` in the URL.

**Severity:** Important

**Preconditions:**
- `buildQuery` function imported directly

**Test Steps:**
1. Call `buildQuery('/servers', { a: '1', b: undefined })`

**Expected Results:**
- Returns `'/servers?a=1'`
- The `b` parameter is not present in the output at all

---

### TC-API-013: buildQuery returns base unchanged when params is undefined

**Description:** When no params object is provided (the argument is `undefined`), `buildQuery` must return the base URL with no `?` suffix. This is the typical case for endpoints that have optional filtering.

**Severity:** Important

**Preconditions:**
- `buildQuery` function imported directly

**Test Steps:**
1. Call `buildQuery('/servers')` with no second argument

**Expected Results:**
- Returns `'/servers'`
- No `?` character appended

---

### TC-API-014: buildQuery returns base unchanged when params is empty object

**Description:** When an empty params object `{}` is provided, `buildQuery` must return the base URL unchanged. Although `if (params)` is truthy for `{}`, the for-of loop finds no entries, so the query string remains empty and the base is returned. This covers a subtly different code path than `params` being `undefined`.

**Severity:** Minor

**Preconditions:**
- `buildQuery` function imported directly

**Test Steps:**
1. Call `buildQuery('/servers', {})`

**Expected Results:**
- Returns `'/servers'`
- No `?` character appended

---

## 5. queryClient Default Configuration

### TC-API-015: queryClient uses correct default options

**Description:** The exported `queryClient` instance must be configured with `retry: 1`, `staleTime: 30000` (30 seconds), and `refetchOnWindowFocus: false`. These defaults control retry behavior, cache staleness, and background refetching across the entire application.

**Severity:** Important

**Preconditions:**
- `queryClient` imported directly from `client.ts`

**Test Steps:**
1. Access `queryClient.defaultQueryOptions()` (TanStack Query v5) or inspect the `queryClient` instance directly

**Expected Results:**
- The default retry value for queries is `1`
- The default staleTime for queries is `30000` (30,000 ms)
- The default `refetchOnWindowFocus` is `false`

---

## 6. API Function Shape & Behavior

### TC-API-016: login() returns the correct response shape

**Description:** The `login()` function must send a POST to `/auth/login` with JSON body containing `username` and `password`, and the resolved response must match the `LoginResponse` shape: `{ token: string, user: AuthUser, mfa_required: boolean }`.

**Severity:** Critical

**Preconditions:**
- Mock global `fetch` to return status 200 with body:
  ```json
  {
    "token": "fcp_abc123",
    "user": { "id": "u1", "username": "admin", "role": "admin", "team_namespace": "root", "mfa_enabled": false },
    "mfa_required": false
  }
  ```

**Test Steps:**
1. Call `login('admin', 'secret')`
2. Inspect the resolved value

**Expected Results:**
- `fetch` is called with URL `'/v1/auth/login'`, method `'POST'`, and body containing `{"username":"admin","password":"secret"}`
- The resolved value has:
  - `token` equal to `"fcp_abc123"`
  - `user.username` equal to `"admin"`
  - `user.role` equal to `"admin"`
  - `user.mfa_enabled` equal to `false`
  - `mfa_required` equal to `false`

---

### TC-API-017: fetchServers passes per_page param via buildQuery

**Description:** `fetchServers` accepts an optional params object that is forwarded directly to `buildQuery`. This test verifies that query parameters like `per_page` are correctly appended to the URL, enabling pagination control.

**Severity:** Important

**Preconditions:**
- Mock global `fetch` to return a `PaginatedResponse<MCPServer>` with status 200
- `useAuthStore` token mocked (optional)

**Test Steps:**
1. Call `fetchServers({ per_page: '10', health_status: 'healthy' })`
2. Inspect the URL argument passed to `fetch`

**Expected Results:**
- `fetch` is called with URL `'/v1/servers?per_page=10&health_status=healthy'`
- The response resolves to a `PaginatedResponse` object with `items` and `pagination` properties

---

### TC-API-018: exportAudit POSTs filter params in the request body

**Description:** The `exportAudit` function must send a POST request to `/audit/export` with filter parameters serialized in the request body as JSON. Unlike `fetchAuditEvents` which uses query parameters, export sends filters in the body because the action creates a server-side resource (an export job).

**Severity:** Important

**Preconditions:**
- Mock global `fetch` to return status 200 with body `{ "export_id": "exp-123" }`

**Test Steps:**
1. Call `exportAudit({ event_type: 'capability.requested', since: '2026-07-01T00:00:00Z' })`

**Expected Results:**
- `fetch` is called with URL `'/v1/audit/export'`
- The request method is `'POST'`
- The request body (parsed as JSON) equals `{ "event_type": "capability.requested", "since": "2026-07-01T00:00:00Z" }`
- The resolved value has `export_id` equal to `"exp-123"`

---

## Summary

| # | Test | Area | Severity |
|---|---|---|---|
| TC-API-001 | Fetcher attaches auth header | Auth & Headers | Critical |
| TC-API-002 | Fetcher omits auth header when no token | Auth & Headers | Critical |
| TC-API-003 | Fetcher sets Content-Type and Accept headers | Auth & Headers | Important |
| TC-API-004 | Fetcher 401 on /auth/ skips logout and redirect | Auth & Headers | Critical |
| TC-API-005 | Fetcher 401 on non-auth calls logout and redirects | Auth & Headers | Critical |
| TC-API-006 | Fetcher parses error body on non-OK response | Error Handling | Critical |
| TC-API-007 | Fetcher handles empty error body | Error Handling | Important |
| TC-API-008 | Fetcher handles network failure (fetch rejects) | Error Handling | Critical |
| TC-API-009 | Fetcher handles malformed JSON response on error | Error Handling | Important |
| TC-API-010 | Fetcher passes through custom options and merges headers | Custom Options | Important |
| TC-API-011 | buildQuery builds correct query string from params | buildQuery | Critical |
| TC-API-012 | buildQuery skips undefined params | buildQuery | Important |
| TC-API-013 | buildQuery returns base unchanged when params is undefined | buildQuery | Important |
| TC-API-014 | buildQuery returns base unchanged when params is empty object | buildQuery | Minor |
| TC-API-015 | queryClient uses correct default options | queryClient | Important |
| TC-API-016 | login() returns the correct response shape | API Functions | Critical |
| TC-API-017 | fetchServers passes per_page param via buildQuery | API Functions | Important |
| TC-API-018 | exportAudit POSTs filter params in the request body | API Functions | Important |
