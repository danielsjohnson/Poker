import type { GameSnapshot } from "../types/game";

const defaultApiBaseUrl = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl).replace(/\/$/, "");

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function startGame(stackSize = 1000): Promise<GameSnapshot> {
  return requestJson<GameSnapshot>("/game/start", {
    method: "POST",
    body: JSON.stringify({ stack_size: stackSize }),
  });
}

export function fetchGame(sessionId: string): Promise<GameSnapshot> {
  return requestJson<GameSnapshot>(`/game/${sessionId}`);
}

export function submitAction(sessionId: string, actionIndex: number, betAmount?: number): Promise<GameSnapshot> {
  return requestJson<GameSnapshot>(`/game/${sessionId}/action`, {
    method: "POST",
    body: JSON.stringify({ action_index: actionIndex, bet_amount: betAmount }),
  });
}

export function retryBotTurn(sessionId: string): Promise<GameSnapshot> {
  return requestJson<GameSnapshot>(`/game/${sessionId}/bot-turn`, {
    method: "POST",
  });
}

export function dealNextHand(sessionId: string): Promise<GameSnapshot> {
  return requestJson<GameSnapshot>(`/game/${sessionId}/new-hand`, {
    method: "POST",
  });
}
