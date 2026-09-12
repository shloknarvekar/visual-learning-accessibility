"use client";

import { useEffect, useState } from "react";

import { apiClient, type HealthResponse } from "@/lib/api-client";

type Status =
  | { kind: "checking" }
  | { kind: "offline" }
  | { kind: "online"; aiMode: HealthResponse["ai_mode"] };

function describe(status: Status): string {
  switch (status.kind) {
    case "checking":
      return "Checking API connection…";
    case "offline":
      return "API not reachable";
    case "online":
      return status.aiMode === "mock"
        ? "API connected · demo mode (example lessons, no AI key)"
        : "API connected · AI generation enabled";
  }
}

/** Shows whether the browser can reach the FastAPI service and whether AI is enabled. */
export function ApiStatus() {
  const [status, setStatus] = useState<Status>({ kind: "checking" });

  useEffect(() => {
    let cancelled = false;
    apiClient
      .getHealth()
      .then((health) => {
        if (!cancelled) setStatus({ kind: "online", aiMode: health.ai_mode });
      })
      .catch(() => {
        if (!cancelled) setStatus({ kind: "offline" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return <p role="status">{describe(status)}</p>;
}
