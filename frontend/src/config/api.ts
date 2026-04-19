// src/config/api.ts
const API_BASE_URL: string = import.meta.env.VITE_API_URL;

if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_URL in environment variables");
}

export default API_BASE_URL;

export interface QueryRequest {
    metric: string;
    depth?: number;
    startDate?: string;
    endDate?: string;
}

export interface QueryResponse {
    success: boolean;
    data: any; // you can refine later
    error?: string;
}

