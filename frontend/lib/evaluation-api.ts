import { getApiBase, readErrorMessage } from "@/lib/auth-api";

export type EvalTask = "chat" | "sentiment" | "buy_sell" | "fundamental";

export type JudgeScore = {
  relevance: number;
  clarity: number;
  safety: number;
  overall: number;
  reasoning: string;
};

export type ModelResult = {
  model: string;
  response: string;
  latency_ms: number;
  citation_count: number;
  safety_passed: boolean;
  error: string | null;
  judge_score: JudgeScore | null;
};

export type CompareRequest = {
  task: EvalTask;
  ticker: string;
  query: string;
};

export type CompareResponse = {
  task: string;
  ticker: string;
  query: string;
  results: ModelResult[];
  disclaimer: string;
};

export async function postCompareModels(body: CompareRequest): Promise<CompareResponse> {
  const res = await fetch(`${getApiBase()}/api/evaluation/compare-models`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<CompareResponse>;
}
