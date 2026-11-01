import type {
  ComparisonReport,
  DatasetValidationResult,
  Experiment,
  ExperimentListItem,
} from './types';

const API_BASE = '/api';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

function isNetworkError(err: unknown): boolean {
  if (err instanceof ApiError) return false;
  // Browser fetch throws TypeError on DNS/connection failure or AbortError on timeout
  if (err instanceof TypeError) return true;
  if (err && typeof err === 'object' && 'name' in err && (err as any).name === 'AbortError') return true;
  return false;
}

export async function checkHealth(): Promise<{ status: string; version: string; isConnected: boolean }> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      const data = await res.json();
      return { ...data, isConnected: true };
    }
    return { status: 'error', version: '0.1.0', isConnected: false };
  } catch {
    return { status: 'offline', version: '0.1.0', isConnected: false };
  }
}

export async function listExperiments(): Promise<ExperimentListItem[]> {
  try {
    const res = await fetch(`${API_BASE}/experiments/`);
    if (!res.ok) {
      throw new ApiError(res.status, `Server error ${res.status}: ${res.statusText}`);
    }
    const data = await res.json();
    return data.experiments || [];
  } catch (err) {
    if (isNetworkError(err)) {
      console.warn('API network connection offline, returning offline demo fallback:', err);
      return getFallbackExperimentsList();
    }
    throw err;
  }
}

export async function getExperiment(id: string): Promise<Experiment> {
  if (id.startsWith('demo-')) {
    return getFallbackExperiment(id);
  }
  try {
    const res = await fetch(`${API_BASE}/experiments/${id}`);
    if (!res.ok) {
      throw new ApiError(res.status, `Failed to load experiment ${id} (HTTP ${res.status})`);
    }
    return await res.json();
  } catch (err) {
    if (isNetworkError(err)) {
      console.warn('API network connection offline, returning offline demo fallback:', err);
      return getFallbackExperiment(id);
    }
    throw err;
  }
}

export async function runExperiment(payload: {
  name: string;
  dataset_path: string;
  provider_name: string;
  model: string;
  system_prompt: string;
  user_template: string;
  exact_match: boolean;
  token_f1: boolean;
  json_validity: boolean;
}): Promise<{ experiment_id: string; status: string; summary: any }> {
  const res = await fetch(`${API_BASE}/experiments/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Experiment failed to run' }));
    throw new Error(err.detail || `Server error ${res.status}`);
  }
  return await res.json();
}

export async function compareExperiments(
  baselineId: string,
  candidateId: string
): Promise<ComparisonReport> {
  const res = await fetch(`${API_BASE}/comparisons/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ baseline_id: baselineId, candidate_id: candidateId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Comparison failed' }));
    throw new Error(err.detail || `Comparison error ${res.status}`);
  }
  return await res.json();
}

export async function validateDatasetFile(file: File): Promise<DatasetValidationResult> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/datasets/validate`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Validation failed' }));
    throw new Error(err.detail || `Validation error ${res.status}`);
  }
  return await res.json();
}

export async function getExperimentReport(
  experimentId: string,
  format: 'markdown' | 'json' | 'csv'
): Promise<string> {
  const res = await fetch(`${API_BASE}/reports/experiments/${experimentId}/${format}`);
  if (!res.ok) throw new Error(`Report fetch failed (${res.status})`);
  return await res.text();
}

export async function deleteExperiment(id: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/experiments/${id}`, { method: 'DELETE' });
  return res.ok;
}

// ── Demo / Offline fallbacks ─────────────────────────────────────────────────

function getFallbackExperimentsList(): ExperimentListItem[] {
  return [
    {
      id: 'demo-exp-002-candidate',
      name: '[DEMO DATA] GPT-4o-mini Prompt v2 (Candidate)',
      status: 'completed',
      is_demo: true,
      started_at: new Date(Date.now() - 3600000).toISOString(),
      completed_at: new Date(Date.now() - 3590000).toISOString(),
    },
    {
      id: 'demo-exp-001-baseline',
      name: '[DEMO DATA] GPT-3.5 Legacy Baseline',
      status: 'completed',
      is_demo: true,
      started_at: new Date(Date.now() - 7200000).toISOString(),
      completed_at: new Date(Date.now() - 7180000).toISOString(),
    },
  ];
}

function getFallbackExperiment(id: string): Experiment {
  const isCand = id.includes('candidate');
  return {
    id,
    is_demo: true,
    config: {
      experiment_id: id,
      name: isCand ? '[DEMO DATA] GPT-4o-mini Prompt v2 (Candidate)' : '[DEMO DATA] GPT-3.5 Legacy Baseline',
      dataset_path: 'examples/sample_dataset.jsonl',
      provider: {
        name: isCand ? 'mock' : 'mock',
        model: isCand ? 'mock-gpt-4o-mini-simulated' : 'mock-gpt-3.5-simulated',
      },
      prompt: {
        system_prompt: 'You are a concise, factual technical assistant. Answer directly.',
        user_template: '{input}',
      },
      evaluators: {
        exact_match: true,
        token_overlap_f1: true,
        json_validity: true,
      },
    },
    status: 'completed',
    started_at: new Date(Date.now() - 3600000).toISOString(),
    completed_at: new Date(Date.now() - 3590000).toISOString(),
    summary: {
      total_cases: 12,
      successful_cases: 12,
      failed_cases: 0,
      success_rate: 1.0,
      mean_latency_ms: isCand ? 142.5 : 210.0,
      aggregate_metrics: {
        exact_match: isCand ? 0.75 : 0.50,
        token_overlap_f1: isCand ? 0.88 : 0.71,
        latency_ms: isCand ? 142.5 : 210.0,
      },
    },
    results: [
      {
        case_id: 'support-001',
        input: 'How can I reset my account password?',
        reference: "To reset your password, visit the sign-in page and click 'Forgot password'. Follow the email instructions to create a new password.",
        output: "Visit the sign-in page, click 'Forgot password', and follow the email instructions to choose a new password.",
        latency_ms: isCand ? 130.0 : 190.0,
        is_simulated: true,
        metrics: [
          { metric_name: 'exact_match', score: 0.0, passed: false },
          { metric_name: 'token_overlap_f1', score: 0.85, passed: true },
          { metric_name: 'latency_ms', score: isCand ? 130.0 : 190.0 },
        ],
      },
      {
        case_id: 'qa-002',
        input: 'What is the capital of France?',
        reference: 'Paris',
        output: 'Paris',
        latency_ms: isCand ? 85.0 : 120.0,
        is_simulated: true,
        metrics: [
          { metric_name: 'exact_match', score: 1.0, passed: true },
          { metric_name: 'token_overlap_f1', score: 1.0, passed: true },
          { metric_name: 'latency_ms', score: isCand ? 85.0 : 120.0 },
        ],
      },
    ],
  };
}
