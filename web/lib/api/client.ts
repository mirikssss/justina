import createClient from "openapi-fetch";

import type { paths } from "./schema";

// Типы генерируются из contracts/openapi.yaml: `npm run gen:api`. Руками schema.d.ts не правим.
// NEXT_PUBLIC_API_URL: http://localhost:8000 — живой API, http://localhost:4010 — Prism-мок.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = createClient<paths>({ baseUrl: API_URL, credentials: "include" });

export type { components, paths } from "./schema";
