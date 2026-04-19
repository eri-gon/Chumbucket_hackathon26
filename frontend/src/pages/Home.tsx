import { useCallback, useState } from "react";
import {
    runAthenaQuery,
    type AthenaQueryPayload,
    type AthenaQueryResult,
    type FilterClause,
} from "../services/api";
import {
    ATHENA_ALLOWED_COLUMNS,
    ATHENA_ALLOWED_OPS,
    type AthenaAllowlistedColumn,
    type AthenaFilterOp,
} from "../config/athenaAllowlist";
import "./Home.css";

function isRowArray(v: unknown): v is Record<string, unknown>[] {
    if (!Array.isArray(v) || v.length === 0) return false;
    const first = v[0];
    return typeof first === "object" && first !== null && !Array.isArray(first);
}

function DataPreviewTable({ rows }: { rows: Record<string, unknown>[] }) {
    if (rows.length === 0) {
        return <p className="status-line">No rows returned.</p>;
    }
    const keys = Object.keys(rows[0]);
    const displayKeys = keys.slice(0, 12);

    return (
        <div className="table-wrap">
            <table className="data-table">
                <thead>
                    <tr>
                        {displayKeys.map((k) => (
                            <th key={k}>{k}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row, i) => (
                        <tr key={i}>
                            {displayKeys.map((k) => (
                                <td key={k}>{formatCell(row[k])}</td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function formatCell(v: unknown): string {
    if (v === null || v === undefined) return "";
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
}

function newFilterKey(): string {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

type LocalFilterRow = {
    key: string;
    column: AthenaAllowlistedColumn | "";
    op: AthenaFilterOp;
    value: string;
    valueHi: string;
};

function parseFilterScalar(raw: string, label: string): number | string {
    const s = raw.trim();
    if (!s) throw new Error(`${label}: value is required`);
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    if (/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(s)) {
        const n = Number(s);
        if (!Number.isFinite(n)) throw new Error(`${label}: invalid number`);
        return n;
    }
    return s;
}

function buildFilterClauses(rows: LocalFilterRow[]): FilterClause[] {
    const out: FilterClause[] = [];
    for (const r of rows) {
        if (!r.column) continue;
        if (r.op === "BETWEEN") {
            const lo = parseFilterScalar(r.value, r.column);
            const hi = parseFilterScalar(r.valueHi, r.column);
            out.push({ column: r.column, op: "BETWEEN", value: [lo, hi] });
        } else {
            out.push({
                column: r.column,
                op: r.op,
                value: parseFilterScalar(r.value, r.column),
            });
        }
    }
    return out;
}

export default function Home() {
    const [metric, setMetric] = useState("");
    const [useDepthShortcut, setUseDepthShortcut] = useState(false);
    const [depth, setDepth] = useState(10);
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");

    const [pickedColumns, setPickedColumns] = useState<AthenaAllowlistedColumn[]>([]);
    const [filterRows, setFilterRows] = useState<LocalFilterRow[]>([]);
    const [limit, setLimit] = useState(10);
    const [useOrderBy, setUseOrderBy] = useState(false);
    const [orderColumn, setOrderColumn] = useState<AthenaAllowlistedColumn | "">("depthm");
    const [orderDirection, setOrderDirection] = useState<"ASC" | "DESC">("ASC");

    const [loading, setLoading] = useState(false);
    const [liveResult, setLiveResult] = useState<AthenaQueryResult | null>(null);
    const [liveError, setLiveError] = useState<string | null>(null);

    const toggleColumn = useCallback((c: AthenaAllowlistedColumn) => {
        setPickedColumns((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]));
    }, []);

    const selectAllColumns = useCallback(() => {
        setPickedColumns([...ATHENA_ALLOWED_COLUMNS]);
    }, []);

    const clearColumns = useCallback(() => {
        setPickedColumns([]);
    }, []);

    const addFilterRow = useCallback(() => {
        setFilterRows((prev) => [
            ...prev,
            {
                key: newFilterKey(),
                column: "depthm",
                op: "=",
                value: "",
                valueHi: "",
            },
        ]);
    }, []);

    const removeFilterRow = useCallback((key: string) => {
        setFilterRows((prev) => prev.filter((r) => r.key !== key));
    }, []);

    const updateFilterRow = useCallback((key: string, patch: Partial<LocalFilterRow>) => {
        setFilterRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
    }, []);

    const runQuery = async () => {
        setLoading(true);
        setLiveError(null);
        setLiveResult(null);
        try {
            let filters: FilterClause[] | undefined;
            try {
                filters = buildFilterClauses(filterRows);
            } catch (e) {
                throw new Error(e instanceof Error ? e.message : String(e));
            }
            if (filters.length === 0) filters = undefined;

            const payload: AthenaQueryPayload = {};
            if (metric.trim()) payload.metric = metric.trim();
            if (useDepthShortcut) payload.depth = Number(depth) || 0;
            if (startDate.trim()) payload.startDate = startDate.trim();
            if (endDate.trim()) payload.endDate = endDate.trim();
            if (pickedColumns.length > 0) payload.columns = [...pickedColumns];
            if (filters) payload.filters = filters;
            payload.limit = Math.min(500, Math.max(1, Math.floor(Number(limit)) || 10));
            if (useOrderBy && orderColumn) {
                payload.orderBy = { column: orderColumn, direction: orderDirection };
            }

            const res = await runAthenaQuery(payload);
            setLiveResult(res);
        } catch (e) {
            setLiveError(e instanceof Error ? e.message : String(e));
        } finally {
            setLoading(false);
        }
    };

    const payloadRows =
        liveResult &&
        typeof liveResult.data === "object" &&
        liveResult.data !== null &&
        "data" in liveResult.data &&
        isRowArray((liveResult.data as { data: unknown }).data)
            ? (liveResult.data as { data: Record<string, unknown>[] }).data
            : null;

    const executedSql =
        liveResult &&
        typeof liveResult.data === "object" &&
        liveResult.data !== null &&
        "query" in liveResult.data &&
        typeof (liveResult.data as { query: unknown }).query === "string"
            ? (liveResult.data as { query: string }).query
            : null;

    const apiErrorMessage =
        liveResult &&
        typeof liveResult.data === "object" &&
        liveResult.data !== null &&
        "error" in liveResult.data &&
        typeof (liveResult.data as { error: unknown }).error === "string"
            ? (liveResult.data as { error: string }).error
            : null;

    return (
        <div className="dashboard-app">
            <aside className="dashboard-sidebar" aria-label="About this demo">
                <div className="sidebar-brand">
                    <span className="sidebar-logo" aria-hidden>
                        ≋
                    </span>
                    <div>
                        <div className="sidebar-title">CalCOFI Query</div>
                        <div className="sidebar-meta">Athena API · Bottle schema</div>
                    </div>
                </div>
                <p className="sidebar-blurb">
                    Structured JSON only — the Lambda builds SQL from an allowlisted column set. No raw SQL from the
                    browser.
                </p>
            </aside>
            <main className="dashboard-main">
                <div className="home">
            <h1>CalCOFI infrastructure demo</h1>
            <p className="lead">
                The <strong>Query</strong> button calls <code>POST …/query</code> on your API stage. The Lambda builds SQL
                from an allowlisted column set (no raw SQL from the browser): optional column list, filters, capped{" "}
                <code>LIMIT</code>, and optional <code>ORDER BY</code>. Set <code>VITE_API_URL</code> to the stage base (
                <code>…/Prod</code>) or a full <code>…/Prod/hello</code> URL; the app strips <code>/hello</code> when
                building the <code>/query</code> URL.
            </p>

            <section className="pipeline" aria-labelledby="stack-heading">
                <h2 id="stack-heading">Our stack</h2>
                <ol className="pipeline-steps">
                    <li>
                        <strong>S3</strong> — CalCOFI-style CSVs live in the data lake; Glue external tables point at
                        prefixes (e.g. <code>bottle/</code>, <code>cast/</code>).
                    </li>
                    <li>
                        <strong>Athena</strong> — SQL runs against those tables over data in S3.
                    </li>
                    <li>
                        <strong>Lambda</strong> — <code>POST /query</code> runs Athena and returns JSON rows.
                    </li>
                    <li>
                        <strong>API Gateway</strong> — Public HTTPS; the demo below uses <code>POST …/query</code>.
                    </li>
                </ol>
                <p className="viz-note">
                    A <strong>Streamlit</strong> or BI dashboard could sit on top of the same API.
                </p>
            </section>

            <section className="athena-demo" aria-labelledby="live-api-heading">
                <h2 id="live-api-heading">Athena preview (POST /query)</h2>
                <p className="lead">
                    Request body is structured JSON only. Column names must match the server allowlist (see{" "}
                    <code>frontend/src/config/athenaAllowlist.ts</code>, matching{" "}
                    <code>data/schemas/calcofi_schema.sql</code> <code>bottle_table</code>). Omitting{" "}
                    <code>columns</code> means <code>SELECT *</code>. The <code>metric</code> field is optional metadata
                    for clients and does not change SQL. Use <strong>Filter by depth</strong> to send <code>depth</code>{" "}
                    and add <code>depthm = …</code>.
                </p>

                <div className="preview-grid">
                    <div className="card">
                        <h3>POST /query</h3>
                        <p className="hint hint--tight">
                            Primary action: <strong>Query</strong> — builds SQL on the server with a max{" "}
                            <code>LIMIT</code> of 500.
                        </p>

                        <div className="form-grid">
                            <label>
                                metric (optional, not used in SQL)
                                <input
                                    value={metric}
                                    onChange={(e) => setMetric(e.target.value)}
                                    placeholder="e.g. temperature"
                                />
                            </label>
                            <label className="checkbox-row">
                                <input
                                    type="checkbox"
                                    checked={useDepthShortcut}
                                    onChange={(e) => setUseDepthShortcut(e.target.checked)}
                                />
                                Filter by depth (<code>depthm</code>)
                            </label>
                            {useDepthShortcut && (
                                <label>
                                    depth (maps to <code>depthm</code>)
                                    <input
                                        type="number"
                                        value={depth}
                                        onChange={(e) => setDepth(Number(e.target.value))}
                                    />
                                </label>
                            )}
                            <label>
                                startDate (optional; only used if allowlisted <code>date</code> exists — not on default{" "}
                                <code>bottle_table</code>)
                                <input
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    placeholder="2019-01-01"
                                />
                            </label>
                            <label>
                                endDate (optional)
                                <input
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    placeholder="2019-12-31"
                                />
                            </label>
                            <label>
                                limit (1–500, default 10 on server if omitted)
                                <input
                                    type="number"
                                    min={1}
                                    max={500}
                                    value={limit}
                                    onChange={(e) => setLimit(Number(e.target.value))}
                                />
                            </label>
                        </div>

                        <fieldset className="column-fieldset">
                            <legend>Columns (none selected → SELECT *)</legend>
                            <div className="column-actions">
                                <button type="button" className="secondary" onClick={selectAllColumns}>
                                    Select all
                                </button>
                                <button type="button" className="secondary" onClick={clearColumns}>
                                    Clear
                                </button>
                            </div>
                            <div className="column-grid">
                                {ATHENA_ALLOWED_COLUMNS.map((c) => (
                                    <label key={c} className="column-chip">
                                        <input
                                            type="checkbox"
                                            checked={pickedColumns.includes(c)}
                                            onChange={() => toggleColumn(c)}
                                        />
                                        {c}
                                    </label>
                                ))}
                            </div>
                        </fieldset>

                        <div className="filter-section">
                            <div className="filter-head">
                                <span>Filters</span>
                                <button type="button" className="secondary" onClick={addFilterRow}>
                                    Add filter
                                </button>
                            </div>
                            {filterRows.length === 0 && (
                                <p className="hint hint--filter-empty">
                                    No extra <code>WHERE</code> clauses beyond depth/date shortcuts.
                                </p>
                            )}
                            {filterRows.map((row) => (
                                <div key={row.key} className="filter-row">
                                    <select
                                        value={row.column}
                                        onChange={(e) =>
                                            updateFilterRow(row.key, {
                                                column: e.target.value as AthenaAllowlistedColumn | "",
                                            })
                                        }
                                    >
                                        <option value="">Column…</option>
                                        {ATHENA_ALLOWED_COLUMNS.map((c) => (
                                            <option key={c} value={c}>
                                                {c}
                                            </option>
                                        ))}
                                    </select>
                                    <select
                                        value={row.op}
                                        onChange={(e) =>
                                            updateFilterRow(row.key, { op: e.target.value as AthenaFilterOp })
                                        }
                                    >
                                        {ATHENA_ALLOWED_OPS.map((op) => (
                                            <option key={op} value={op}>
                                                {op}
                                            </option>
                                        ))}
                                    </select>
                                    {row.op === "BETWEEN" ? (
                                        <>
                                            <input
                                                className="grow"
                                                placeholder="low"
                                                value={row.value}
                                                onChange={(e) => updateFilterRow(row.key, { value: e.target.value })}
                                            />
                                            <input
                                                className="grow"
                                                placeholder="high"
                                                value={row.valueHi}
                                                onChange={(e) => updateFilterRow(row.key, { valueHi: e.target.value })}
                                            />
                                        </>
                                    ) : (
                                        <input
                                            className="grow"
                                            placeholder="value"
                                            value={row.value}
                                            onChange={(e) => updateFilterRow(row.key, { value: e.target.value })}
                                        />
                                    )}
                                    <button type="button" className="secondary" onClick={() => removeFilterRow(row.key)}>
                                        Remove
                                    </button>
                                </div>
                            ))}
                        </div>

                        <div className="form-grid" style={{ marginTop: "0.75rem" }}>
                            <label className="checkbox-row">
                                <input
                                    type="checkbox"
                                    checked={useOrderBy}
                                    onChange={(e) => setUseOrderBy(e.target.checked)}
                                />
                                Order by
                            </label>
                            {useOrderBy && (
                                <>
                                    <label>
                                        column
                                        <select
                                            value={orderColumn}
                                            onChange={(e) =>
                                                setOrderColumn(e.target.value as AthenaAllowlistedColumn | "")
                                            }
                                        >
                                            <option value="">Choose…</option>
                                            {ATHENA_ALLOWED_COLUMNS.map((c) => (
                                                <option key={c} value={c}>
                                                    {c}
                                                </option>
                                            ))}
                                        </select>
                                    </label>
                                    <label>
                                        direction
                                        <select
                                            value={orderDirection}
                                            onChange={(e) => setOrderDirection(e.target.value as "ASC" | "DESC")}
                                        >
                                            <option value="ASC">ASC</option>
                                            <option value="DESC">DESC</option>
                                        </select>
                                    </label>
                                </>
                            )}
                        </div>

                        <div className="actions">
                            <button type="button" disabled={loading} onClick={runQuery}>
                                {loading ? "Running…" : "Query"}
                            </button>
                        </div>

                        {liveError != null && <div className="error-box">{liveError}</div>}

                        {liveResult != null && (
                            <>
                                <p className="status-line">
                                    <span className={liveResult.ok ? "status-ok" : "status-bad"}>
                                        HTTP {liveResult.status}
                                    </span>
                                    {" · "}
                                    {liveResult.ms} ms
                                </p>
                                {!liveResult.ok && apiErrorMessage && (
                                    <div className="error-box error-box--spaced">
                                        {apiErrorMessage}
                                    </div>
                                )}
                                {executedSql != null && (
                                    <p className="hint hint--sql">
                                        <strong>SQL</strong> <code className="sql-inline">{executedSql}</code>
                                    </p>
                                )}
                                {payloadRows && <DataPreviewTable rows={payloadRows} />}
                                <details className="json-details">
                                    <summary>Raw JSON</summary>
                                    <pre>{JSON.stringify(liveResult.data, null, 2)}</pre>
                                </details>
                            </>
                        )}
                    </div>
                </div>
            </section>
                </div>
            </main>
        </div>
    );
}
