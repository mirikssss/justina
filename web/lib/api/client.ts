import createClient from "openapi-fetch";

import type { paths } from "./schema";

// Типы генерируются из contracts/openapi.yaml: `make gen-api`. Руками schema.d.ts не правим.
// Браузер ходит в /api на своём домене, Next проксирует на бэкенд (next.config.mjs, API_PROXY_URL):
// так работает cookie __Host-session и не нужен CORS. Prism-мок: API_PROXY_URL=http://localhost:4010.
export const API_BASE = "/api";

export const api = createClient<paths>({ baseUrl: API_BASE, credentials: "include" });

export type { components, paths } from "./schema";
export type Schemas = import("./schema").components["schemas"];
