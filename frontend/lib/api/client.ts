import type {
  ModelInputs,
  ModelResponse,
  PlayerDetail,
  PlayerPage,
  PlayerPrediction,
  PredictionResponse,
  RankingResponse,
  RegisteredModel,
  SimulationResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export function apiBaseUrl() {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!raw)
    throw new ApiError(
      0,
      "PlayerWorth is not connected yet. Please try again later.",
    );
  return raw.replace(/\/+$/, "");
}
const messages: Record<number, string> = {
  404: "That information isn't available yet.",
  422: "Please check your input and try again.",
  500: "Couldn't load this information. Please try again.",
  503: "PlayerWorth's data or model is temporarily unavailable.",
};
export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      cache: "no-store",
      signal: init.signal
        ? AbortSignal.any([init.signal, AbortSignal.timeout(8000)])
        : AbortSignal.timeout(8000),
      headers: {
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
    if (!response.ok)
      throw new ApiError(
        response.status,
        messages[response.status] ?? "Couldn't load this information.",
      );
    return (await response.json()) as T;
  } catch (error) {
    if (
      error instanceof ApiError ||
      (error instanceof Error && error.name === "AbortError")
    )
      throw error;
    throw new ApiError(0, "Couldn't connect to PlayerWorth. Please try again.");
  }
}
const seasonQuery = (season?: string) =>
  season ? `?${new URLSearchParams({ season })}` : "";
export const searchPlayers = (
  search: string,
  signal?: AbortSignal,
  limit = 8,
  offset = 0,
) =>
  request<PlayerPage>(
    `/players?${new URLSearchParams({ search, limit: String(limit), offset: String(offset) })}`,
    { signal },
  );
export const getPlayer = (id: number) =>
  request<PlayerDetail>(`/players/${id}`);
export const getPlayerPrediction = (
  id: number,
  season?: string,
  signal?: AbortSignal,
) =>
  request<PlayerPrediction>(`/players/${id}/prediction${seasonQuery(season)}`, {
    signal,
  });
export const predictValue = (input: ModelInputs) =>
  request<PredictionResponse>("/predictions", {
    method: "POST",
    body: JSON.stringify(input),
  });
export const simulatePlayer = (
  id: number,
  input: Partial<ModelInputs>,
  season?: string,
  signal?: AbortSignal,
) =>
  request<SimulationResponse>(`/players/${id}/simulate${seasonQuery(season)}`, {
    method: "POST",
    body: JSON.stringify(input),
    signal,
  });
export const getCurrentModel = () => request<ModelResponse>("/models/current");
export const getModels = () => request<RegisteredModel[]>("/models");
export const getUndervaluedRankings = (
  limit = 3,
  season?: string,
  signal?: AbortSignal,
) =>
  request<RankingResponse>(
    `/rankings/undervalued?${new URLSearchParams({ limit: String(limit), ...(season ? { season } : {}) })}`,
    { signal },
  );
export const getOvervaluedRankings = (
  limit = 3,
  season?: string,
  signal?: AbortSignal,
) =>
  request<RankingResponse>(
    `/rankings/overvalued?${new URLSearchParams({ limit: String(limit), ...(season ? { season } : {}) })}`,
    { signal },
  );
