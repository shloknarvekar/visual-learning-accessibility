/** Public configuration. NEXT_PUBLIC_* values are inlined at build time and visible to users. */
export const config = {
  apiBaseUrl: (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, ""),
} as const;
