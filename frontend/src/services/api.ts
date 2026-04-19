/**
 * VITE_API_URL may be the stage base (…/Prod) or the full GET /hello URL from
 * CloudFormation; we normalize to …/Prod so `/hello` and `/query` resolve correctly.
 */
import type { AthenaFilterOp } from "../config/athenaAllowlist";

function apiStageBase(raw: string | undefined): string {
    if (!raw?.trim()) return "";
    let s = raw.trim().replace(/\/$/, "");
    if (s.endsWith("/hello")) {
        s = s.slice(0, -"/hello".length).replace(/\/$/, "");
    }
    return s;
}

const BASE_URL = apiStageBase(import.meta.env.VITE_API_URL as string | undefined);

function assertBaseUrl(): string {
    if (!BASE_URL) {
        throw new Error("VITE_API_URL is not set in frontend/.env");
    }
    return BASE_URL;
}

/** Full GET /hello URL: use VITE_API_URL as-is when it already ends with /hello, else …/Prod/hello. */
function resolveHelloUrl(raw: string | undefined): string {
    const trimmed = raw?.trim() ?? "";
    if (!trimmed) {
        throw new Error("VITE_API_URL is not set in frontend/.env");
    }
    const noTrailingSlash = trimmed.replace(/\/$/, "");
    if (noTrailingSlash.endsWith("/hello")) {
        return noTrailingSlash;
    }
    const base = apiStageBase(raw);
    if (!base) {
        throw new Error("VITE_API_URL is not set in frontend/.env");
    }
    return `${base}/hello`;
}

export type HelloQueryPayload = {
    metric?: string;
    depth?: number;
};

export type AthenaOrderBy = {
    column: string;
    direction?: "ASC" | "DESC";
};

export type FilterClause = {
    column: string;
    op: AthenaFilterOp;
    value: number | string | [number | string, number | string];
};

export type AthenaQueryPayload = {
    metric?: string;
    depth?: number;
    startDate?: string;
    endDate?: string;
    columns?: string[];
    filters?: FilterClause[];
    limit?: number;
    orderBy?: AthenaOrderBy;
};

export type AthenaQueryResult = {
    ok: boolean;
    status: number;
    ms: number;
    data: unknown;
};

/** GET /hello with query params — uses full hello URL from resolveHelloUrl(VITE_API_URL). */
export async function runHelloApiQuery(payload: HelloQueryPayload = {}): Promise<AthenaQueryResult> {
    const helloUrl = resolveHelloUrl(import.meta.env.VITE_API_URL as string | undefined);
    const params = new URLSearchParams({
        metric: payload.metric ?? "temperature",
        depth: String(payload.depth ?? 10),
    });
    const t0 = performance.now();
    const response = await fetch(`${helloUrl}?${params.toString()}`, {
        method: "GET",
    });
    const data = await response.json().catch(() => ({ parseError: true as const }));
    const ms = Math.round(performance.now() - t0);
    return { ok: response.ok, status: response.status, data, ms };
}

export async function queryData(payload: { metric: string; depth: number }) {
    const res = await runHelloApiQuery(payload);
    return res.data;
}

/** POST /query — Lambda builds SQL from allowlisted columns, filters, limit, and optional ORDER BY. */
export async function runAthenaQuery(payload: AthenaQueryPayload = {}): Promise<AthenaQueryResult> {
    const base = assertBaseUrl();
    const body: Record<string, unknown> = {};
    if (payload.metric != null && String(payload.metric).trim() !== "") {
        body.metric = payload.metric;
    }
    if (payload.depth !== undefined && payload.depth !== null) {
        body.depth = payload.depth;
    }
    if (payload.startDate?.trim()) body.startDate = payload.startDate.trim();
    if (payload.endDate?.trim()) body.endDate = payload.endDate.trim();
    if (payload.columns?.length) body.columns = payload.columns;
    if (payload.filters?.length) body.filters = payload.filters;
    if (payload.limit !== undefined) body.limit = payload.limit;
    if (payload.orderBy?.column) {
        body.orderBy = {
            column: payload.orderBy.column,
            ...(payload.orderBy.direction ? { direction: payload.orderBy.direction } : {}),
        };
    }

    const t0 = performance.now();
    const response = await fetch(`${base}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({ parseError: true as const }));
    const ms = Math.round(performance.now() - t0);
    return { ok: response.ok, status: response.status, data, ms };
}

/** Smoke preset — POST /query (default LIMIT 10, no extra filters). */
export async function runAthenaBottlePreview() {
    return runAthenaQuery({ limit: 10 });
}
