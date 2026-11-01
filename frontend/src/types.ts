export type RegressionDecision = 'IMPROVED' | 'REGRESSED' | 'INCONCLUSIVE' | 'INSUFFICIENT_DATA';

export interface ConfidenceInterval {
  lower: number;
  upper: number;
  level: number;
  method?: string;
}

export interface MetricComparison {
  metric_name: string;
  direction?: string;
  baseline_mean?: number | null;
  candidate_mean?: number | null;
  absolute_change?: number | null;
  relative_change_pct?: number | null;
  ci?: ConfidenceInterval | null;
  decision: RegressionDecision;
  n_paired: number;
  n_missing_baseline?: number;
  n_missing_candidate?: number;
  n_failed?: number;
  notes?: string[];
}

export interface ComparisonReport {
  comparison_id: string;
  baseline_id: string;
  candidate_id: string;
  created_at: string;
  metric_comparisons: MetricComparison[];
  overall_decision: RegressionDecision;
  cases_improved: string[];
  cases_regressed: string[];
  cases_missing_baseline?: string[];
  cases_missing_candidate?: string[];
  bootstrap_n: number;
  bootstrap_seed: number;
  confidence_level: number;
  notes?: string[];
}

export interface MetricResult {
  metric_name: string;
  score: number | null;
  passed?: boolean | null;
  details?: Record<string, any>;
  error?: string | null;
}

export interface CaseResult {
  case_id: string;
  input: string;
  reference?: string | null;
  output?: string | null;
  latency_ms?: number | null;
  metrics: MetricResult[];
  error?: string | null;
  is_simulated?: boolean;
}

export interface ExperimentSummary {
  total_cases: number;
  successful_cases: number;
  failed_cases: number;
  success_rate: number;
  mean_latency_ms?: number | null;
  median_latency_ms?: number | null;
  p90_latency_ms?: number | null;
  p95_latency_ms?: number | null;
  total_prompt_tokens?: number | null;
  total_completion_tokens?: number | null;
  total_tokens?: number | null;
  estimated_cost_usd?: number | null;
  aggregate_metrics: Record<string, number>;
}

export interface EvaluatorConfig {
  exact_match?: boolean;
  normalized_exact_match?: boolean;
  token_overlap_f1?: boolean;
  json_validity?: boolean;
  json_schema?: boolean;
  keyword_coverage?: boolean;
  semantic_similarity?: boolean;
  judge?: boolean;
}

export interface ExperimentConfig {
  experiment_id: string;
  name: string;
  dataset_path: string;
  provider: {
    name: string;
    model?: string;
  };
  prompt?: {
    system_prompt?: string;
    user_template?: string;
  };
  evaluators?: EvaluatorConfig;
}

export interface Experiment {
  id?: string;
  config: ExperimentConfig;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at?: string | null;
  completed_at?: string | null;
  results?: CaseResult[];
  summary?: ExperimentSummary;
  error?: string | null;
  is_demo?: boolean;
}

export interface ExperimentListItem {
  id: string;
  name: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  is_demo?: boolean;
}

export interface DatasetValidationResult {
  filename: string;
  valid_cases: number;
  invalid_cases: number;
  total_cases: number;
  categories: string[];
  errors: string[];
  is_valid: boolean;
}
