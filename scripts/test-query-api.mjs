#!/usr/bin/env node
/**
 * POST /query against the deployed API (Lambda → Athena).
 *
 *   set API_BASE_URL=https://xxxx.execute-api.region.amazonaws.com/Prod
 *   node scripts/test-query-api.mjs
 *
 * Or set VITE_API_URL the same way (read from frontend/.env if present).
 */
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

function loadFrontendEnv() {
  const p = join(root, "frontend", ".env");
  if (!existsSync(p)) return;
  const text = readFileSync(p, "utf8");
  for (const line of text.split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#") || !t.includes("=")) continue;
    const [k, ...rest] = t.split("=");
    const key = k?.trim();
    const val = rest.join("=").trim().replace(/^["']|["']$/g, "");
    if (key && val && process.env[key] === undefined) process.env[key] = val;
  }
}

function baseUrlFromArgs() {
  const i = process.argv.indexOf("--url");
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1].replace(/\/$/, "");
  loadFrontendEnv();
  const b = (process.env.API_BASE_URL || process.env.VITE_API_URL || "").trim().replace(/\/$/, "");
  return b;
}

function arg(name, def) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1] != null) return process.argv[i + 1];
  return def;
}

const base = baseUrlFromArgs();
if (!base) {
  console.error(
    "Set API_BASE_URL or VITE_API_URL, or: node scripts/test-query-api.mjs --url https://.../Prod"
  );
  process.exit(1);
}

const payload = {
  metric: arg("--metric", "temperature"),
  depth: Number(arg("--depth", "10")),
};
const sd = arg("--start-date", "");
const ed = arg("--end-date", "");
if (sd) payload.startDate = sd;
if (ed) payload.endDate = ed;

const url = `${base}/query`;
console.log("POST", url);
console.log("Body:", JSON.stringify(payload));

const res = await fetch(url, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});

const text = await res.text();
let data;
try {
  data = JSON.parse(text);
} catch {
  console.log(text);
  process.exit(1);
}

const maxRows = Number(arg("--max-rows", "20"));
if (Array.isArray(data.data) && data.data.length > maxRows) {
  const { data: rows, ...rest } = data;
  console.log(
    JSON.stringify(
      {
        ...rest,
        data: rows.slice(0, maxRows),
        _truncated: `${rows.length - maxRows} more row(s); pass --max-rows N`,
      },
      null,
      2
    )
  );
} else {
  console.log(JSON.stringify(data, null, 2));
}

if (!res.ok || data.success === false) process.exit(1);
