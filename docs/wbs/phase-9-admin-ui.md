# Phase 9: Admin UI

> **Tasks:** 85 · **Effort:** 64h (8 days)  
> **Dependencies:** Phase 5 (API routes must be functional)

## 9.1 UI Scaffolding (8 tasks)

### P9-01: Project Initialization
**Effort:** 1.5h | **Deps:** None
**Checklist:** `npm create vite@latest ui -- --template react-ts` → install: react-router-dom, @tanstack/react-query, tailwindcss, @headlessui/react, @heroicons/react → configure tailwind → configure vite proxy (/v1 → http://localhost:8000) → verify `npm run dev` starts on :3000.
**Success Criteria:** Dev server runs. Proxy works (GET /v1/health returns from API).

### P9-02: API Client
**Effort:** 1.5h | **Deps:** P9-01
**Checklist:** `ui/src/api/client.ts` — create TanStack QueryClient → base fetcher function: attaches Authorization header from auth store → parses Fabric-API-Version → handles 401 → redirects to /login → types for all API responses.
**Success Criteria:** Query hooks return typed data. 401 → redirect to login.

### P9-03: App Router + Layout
**Effort:** 1.5h | **Deps:** P9-01
**Checklist:** `ui/src/App.tsx` — React Router routes: /, /login, /servers, /servers/:id, /capabilities, /agent-classes, /policies, /audit, /approvals, /packs, /alerts, /admin/users, /trust → protected routes redirect to /login without token → role-based route visibility → Layout with sidebar + top bar.
**Success Criteria:** All routes render. Protected routes redirect unauthenticated. Sidebar links filtered by role.

### P9-04: Auth Store
**Effort:** 1h | **Deps:** P9-01
**Checklist:** Zustand store: token, user (username, role, team_namespace), login(), logout(), isAuthenticated → token persisted to localStorage → logout clears token + redirects.
**Success Criteria:** Login sets token. Logout clears. Token attached to API requests.

### P9-05: Shared Components — Page States
**Effort:** 1.5h | **Deps:** P9-01
**Checklist:** LoadingState component: skeleton loaders (pulsing gray blocks) → ErrorState: message + retry button → EmptyState: message + optional CTA button → usePageState hook: returns {status, data, error, retry}. Skeleton matches page layout.
**Success Criteria:** All pages use consistent states. Loading → populated transition smooth. Error shows retry.

### P9-06: Shared Components — Table + Filter
**Effort:** 2h | **Deps:** P9-01
**Checklist:** PaginatedTable: cursor/offset pagination controls, sortable headers (click → toggle asc/desc), row click handler → FilterBar: dropdown filters (multi-select support), search input with debounce (300ms), clear all button → both accept generic types.
**Success Criteria:** Table pagination works for both cursor + offset. Filters update query params. Sort toggles.

### P9-07: Shared Components — Modal + Toast + Badge
**Effort:** 1.5h | **Deps:** P9-01
**Checklist:** Modal: overlay, close on Esc/outside click, form submission with loading state → ConfirmDialog: destructive action warning → Toast: success/error/info, auto-dismiss 5s, stackable → Badge: color variants (green/yellow/orange/red/blue/gray) with label → ErrorBoundary: catches React errors, shows fallback.
**Success Criteria:** Modals accessible (keyboard, focus trap). Toasts auto-dismiss. Error boundary catches crashes.

### P9-08: UI Linting + TypeScript Config
**Effort:** 1h | **Deps:** P9-01
**Checklist:** ESLint config: extends react, typescript, prettier → Prettier config: singleQuote, semi, trailingComma → tsconfig strict mode: strictNullChecks, noUncheckedIndexedAccess → typecheck script: `tsc --noEmit`.
**Success Criteria:** `npm run lint` passes. `npm run typecheck` passes. CI catches violations.

## 9.2 Pages (77 tasks — 12 page groups)

_Each page follows same pattern: list view + create modal + detail view + filters + pagination + loading/error/empty states. 5-8 tasks per page group._

### P9-09 to P9-14: Login Page (6 tasks)
Login form → MFA code input → MFA recovery flow → password reset flow → session management → role-based redirect.

### P9-15 to P9-20: Dashboard (6 tasks)
Widgets: server count+health, trust posture, recent audit, pending approvals, degraded servers → auto-refresh 30s → empty state.

### P9-21 to P9-28: Servers (8 tasks)
List table + filters → register modal → detail view → tools table → inspect diff modal → decommission modal → trust assignments panel → routing rules panel.

### P9-29 to P9-35: Capability Catalog (7 tasks)
List + filters → create modal → detail view → map tool modal → conflict warning → deprecate modal → alias management.

### P9-36 to P9-42: Agent Classes (7 tasks)
List → create modal → detail view → trust assignments table → create token modal (show once) → rotate token → revoke token.

### P9-43 to P9-47: Policy Editor (5 tasks)
Monaco/CodeMirror Rego editor → deploy button + version info → test button → policy history → read-only for non-admin.

### P9-48 to P9-55: Audit Log (8 tasks)
Table + filters → expandable row → date range picker → cursor pagination → export modal → export status polling → download → read-only for viewer.

### P9-56 to P9-61: Approvals (6 tasks)
Table + filters → review side panel → approve with note → deny with reason → bulk actions → empty state.

### P9-62 to P9-68: Capability Packs (7 tasks)
Cards → create modal → detail (capabilities+classes) → add capability picker → assign class modal → clone → usage stats.

### P9-69 to P9-73: Alerts (5 tasks)
Table + filters → acknowledge → expandable details → time range filter → empty state.

### P9-74 to P9-80: Admin Users (7 tasks)
Table → invite modal → edit role/scope → deactivate → unlock → reset MFA → admin audit view.

### P9-81 to P9-85: Trust Posture (5 tasks)
Grid cards colored by trust → unreviewed banner → quick trust change → click to detail → team filter.

**Common pattern per page task:** 1h each → Checklist: component structure, API integration (TanStack Query), loading/error/empty/populated states, TypeScript types, accessibility (labels, focus). Success Criteria: renders correctly, API calls work, all states handled, keyboard navigable.
