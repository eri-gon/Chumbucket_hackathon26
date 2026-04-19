import { useState } from "react";
import { queryData, runAthenaBottlePreview } from "../services/api";

export default function Home() {
    const [helloData, setHelloData] = useState<unknown>(null);
    const [athenaData, setAthenaData] = useState<unknown>(null);

    const handleHello = async () => {
        try {
            const result = await queryData({ metric: "temperature", depth: 10 });
            setHelloData(result);
        } catch (e) {
            console.error("[hello]", e);
            setHelloData({ error: String(e) });
        }
    };

    const handleAthenaScript = async () => {
        console.log("[Athena] POST /query — first 10 rows from bottle_table (same as athena_minimal_query.py)…");
        try {
            const res = await runAthenaBottlePreview();
            console.log("[Athena] HTTP", res.status, res.ok ? "OK" : "error");
            console.log("[Athena] payload:", res.data);
            if (!res.ok) {
                console.error("[Athena] request failed — check VITE_API_URL points to the stack with POST /query");
            }
            setAthenaData(res.data);
        } catch (e) {
            console.error("[Athena] network or parse error:", e);
            setAthenaData({ error: String(e) });
        }
    };

    return (
        <div style={{ padding: "1rem", maxWidth: 720 }}>
            <h1>CalCOFI Data Viewer</h1>
            <p style={{ color: "#555", fontSize: 14 }}>
                <strong>Athena</strong> uses the deployed API (<code>POST /query</code>), not the local Python file.
                Set <code>VITE_API_URL</code> to the API base that includes <code>/query</code> (SAM infrastructure stack).
            </p>
            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
                <button type="button" onClick={handleHello}>
                    GET /hello
                </button>
                <button type="button" onClick={handleAthenaScript}>
                    Run Athena (10 rows) → console
                </button>
            </div>
            {helloData != null && (
                <section style={{ marginBottom: "1.5rem" }}>
                    <h2 style={{ fontSize: "1rem" }}>/hello</h2>
                    <pre style={{ background: "#f4f4f4", padding: 12, overflow: "auto" }}>
                        {JSON.stringify(helloData, null, 2)}
                    </pre>
                </section>
            )}
            {athenaData != null && (
                <section>
                    <h2 style={{ fontSize: "1rem" }}>/query (Athena)</h2>
                    <pre style={{ background: "#f4f4f4", padding: 12, overflow: "auto" }}>
                        {JSON.stringify(athenaData, null, 2)}
                    </pre>
                </section>
            )}
        </div>
    );
}
