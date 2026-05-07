import type { AiModeRequest, AiModeResponse } from "@/types/aiMode";

export async function fetchAiMode(payload: AiModeRequest): Promise<AiModeResponse> {
  const res = await fetch("/api/ai-mode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = (await res.json()) as AiModeResponse | { success?: boolean; error?: string };

  if (!res.ok || ("success" in data && data.success === false)) {
    const message = (data as { error?: string }).error || `AI mode request failed (${res.status})`;
    throw new Error(message);
  }

  return data as AiModeResponse;
}
