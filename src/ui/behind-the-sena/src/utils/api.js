export class ApiError extends Error {
    constructor(message, status, payload) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.payload = payload;
    }
}
let cachedBaseUrl = null;
let baseUrlPromise = null;
export async function getApiBaseUrl() {
    if (cachedBaseUrl) {
        return cachedBaseUrl;
    }
    if (!baseUrlPromise) {
        baseUrlPromise = (async () => {
            if (window?.sena?.getApiBaseUrl) {
                try {
                    const baseUrl = await window.sena.getApiBaseUrl();
                    cachedBaseUrl = baseUrl;
                    return baseUrl;
                }
                catch {
                    // Fall through to default
                }
            }
            cachedBaseUrl = "http://127.0.0.1:8000";
            return cachedBaseUrl;
        })();
    }
    return baseUrlPromise;
}
export function clearApiBaseUrlCache() {
    cachedBaseUrl = null;
    baseUrlPromise = null;
}
export function buildApiUrl(baseUrl, path, query) {
    const normalizedBase = baseUrl.replace(/\/+$/, "");
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    const url = new URL(`${normalizedBase}${normalizedPath}`);
    if (query) {
        for (const [key, value] of Object.entries(query)) {
            if (value === undefined || value === null)
                continue;
            url.searchParams.set(key, String(value));
        }
    }
    return url.toString();
}
export async function fetchJson(path, options = {}) {
    const baseUrl = await getApiBaseUrl();
    const url = buildApiUrl(baseUrl, path, options.query);
    const headers = new Headers(options.headers);
    if (!headers.has("Content-Type") && options.body !== undefined) {
        headers.set("Content-Type", "application/json");
    }
    const response = await fetch(url, {
        ...options,
        method: options.method ?? "GET",
        headers,
        body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
    const text = await response.text();
    const payload = text ? safeJsonParse(text) : null;
    if (!response.ok) {
        const message = typeof payload === "object" && payload && "detail" in payload
            ? String(payload.detail)
            : response.statusText || "Request failed";
        throw new ApiError(message, response.status, payload);
    }
    return payload;
}
function safeJsonParse(value) {
    try {
        return JSON.parse(value);
    }
    catch {
        return value;
    }
}
