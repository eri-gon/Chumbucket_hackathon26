// VITE_API_URL = API Gateway stage base (…/Prod), no path suffix.
// Use the stack that exposes POST /query for Athena; GET /hello is optional.
const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

function assertBaseUrl(): string {
    if (!BASE_URL) {
        throw new Error("VITE_API_URL is not set in frontend/.env");
    }
    return BASE_URL;
}

export async function queryData(payload: { metric: string; depth: number }) {
    const base = assertBaseUrl();
    const params = new URLSearchParams({
        metric: payload.metric,
        depth: String(payload.depth),
    });
    const response = await fetch(`${base}/hello?${params.toString()}`, {
        method: "GET",
    });
    return response.json();
}

/** Same as scripts/athena_minimal_query.py: first 10 rows from bottle_table via Lambda → Athena. */
export async function runAthenaBottlePreview() {
    const base = assertBaseUrl();
    const response = await fetch(`${base}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ metric: "temperature", depth: 10 }),
    });
    const data = await response.json().catch(() => ({ parseError: true, raw: null }));
    return { ok: response.ok, status: response.status, data };
}
