const BASE_URL = import.meta.env.VITE_API_URL as string;

export async function queryData(payload: { metric: string; depth: number }) {
    const params = new URLSearchParams({
        metric: payload.metric,
        depth: String(payload.depth),
    });
    const response = await fetch(`${BASE_URL}/hello?${params.toString()}`, {
        method: "GET",
    });

    return response.json();
}
