# Prompt Workbench — Frontend

A React + TypeScript + Vite single-page app for the **Prompt Workbench** developer
tool. It provides a prompt registry with versioned drafts, evaluation runs, an
observability inbox, and settings, all talking to the backend REST API under
`/api/v1`.

## Stack

- **Vite 5** + **React 18** + **TypeScript** (strict mode)
- **@tanstack/react-query** for data fetching, caching, and run polling
- **react-router-dom v6** for routing
- **axios** wrapper with bearer-token auth and a normalized error envelope
- Plain modern CSS (single `src/styles.css`, CSS variables, dark developer-tool aesthetic).
  No component library, no Tailwind.

## Requirements

- **Node 24** and **npm** (project developed and built against Node 24).

## Development

```bash
npm install
npm run dev
```

- Dev server runs on <http://localhost:5173>.
- The app expects the backend to be running on **`http://127.0.0.1:8765`**.
  Vite proxies all `/api` requests to that address (see `vite.config.ts`), so the
  frontend always uses the relative base URL `/api/v1`.

### Demo login

The login screen has a **Fill demo login** button that populates:

- username: `demo@promptworkbench.dev`
- password: `workbench`

## Build

```bash
npm run build      # type-checks (tsc --noEmit) then builds to dist/
npm run preview    # serve the production build locally
npm run typecheck  # type-check only
```

Production assets are emitted to `dist/`.

## Project layout

```
src/
  api/            Typed API layer (types.ts + client.ts)
  auth/           Auth context + token storage (sessionStorage key `pw_token`)
  context/        Toast + current-project contexts
  components/     Reusable UI (Header, JsonEditor, drawers, toasts, ...)
  pages/          Route screens (login, registry, evaluations, observability, settings)
  main.tsx        App bootstrap (providers + router)
  App.tsx         Route table
  styles.css      Single global stylesheet
```

## Auth & errors

- The access token is stored in `sessionStorage` under the key **`pw_token`**.
- Every request except `login` and `health` sends `Authorization: Bearer <token>`.
- Any `401` response clears the token and redirects to `/login`.
- Backend errors use the envelope `{ error: { code, message, details, retryable } }`;
  `error.message` is surfaced in toasts and inline messages.
