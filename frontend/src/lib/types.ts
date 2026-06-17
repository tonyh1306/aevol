export interface Experiment {
  id: string;
  name: string;
  description: string | null;
  version: number;
  parent_id: string | null;
  config: Record<string, unknown>;
  model_name: string | null;
  prompt_template: string | null;
  tags: string[];
  status: "draft" | "running" | "completed" | "failed" | "cancelled";
  dataset_id: string | null;
  created_by: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
}

export interface ExperimentListResponse {
  items: Experiment[];
  total: number;
  page: number;
  limit: number;
}

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  format: "csv" | "jsonl";
  row_count: number | null;
  file_size: number | null;
  schema_info: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetListResponse {
  items: Dataset[];
  total: number;
  page: number;
  limit: number;
}

export interface DatasetRow {
  id: number;
  dataset_id: string;
  row_index: number;
  input_data: Record<string, unknown>;
  expected: Record<string, unknown> | null;
}

export interface Task {
  id: string;
  experiment_id: string;
  dataset_row_id: number | null;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "DEAD";
  priority: number;
  attempt_count: number;
  max_attempts: number;
  worker_id: string | null;
  enqueued_at: string;
  claimed_at: string | null;
  completed_at: string | null;
  output_data: Record<string, unknown> | null;
  error_message: string | null;
  error_type: string | null;
  latency_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cost_usd: string | null;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  page: number;
  limit: number;
}

export interface Worker {
  id: string;
  hostname: string;
  pid: number;
  version: string | null;
  status: "idle" | "busy" | "draining" | "dead";
  current_task_id: string | null;
  tasks_completed: number;
  tasks_failed: number;
  last_heartbeat: string;
  registered_at: string;
  cpu_percent: number | null;
  memory_mb: number | null;
  capabilities: string[];
}

export interface WorkerListResponse {
  items: Worker[];
  total: number;
}

export interface MetricAggregate {
  name: string;
  mean: number;
  p50: number;
  p95: number;
  p99: number;
  min: number;
  max: number;
  count: number;
  unit: string | null;
}

export interface MetricSummary {
  experiment_id: string;
  metrics: MetricAggregate[];
}

export interface RegressionFlag {
  metric: string;
  baseline_value: number;
  candidate_value: number;
  delta_pct: number;
  severity: "warning" | "critical";
}

export interface Report {
  id: string;
  title: string;
  baseline_id: string;
  candidate_id: string;
  summary: {
    deltas: Array<{ metric: string; baseline: number; candidate: number; delta_pct: number }>;
    improvements: string[];
    stable: string[];
    regression_count: number;
  };
  regression_flags: RegressionFlag[];
  generated_at: string;
}

export interface ComparisonResult {
  baseline_id: string;
  candidate_id: string;
  baseline_metrics: MetricAggregate[];
  candidate_metrics: MetricAggregate[];
  deltas: Array<{ metric: string; baseline: number; candidate: number; delta_pct: number }>;
  regressions: RegressionFlag[];
}

export interface FailureCluster {
  id: string;
  experiment_id: string;
  cluster_label: string;
  error_pattern: string;
  sample_errors: string[];
  task_count: number;
  suggestion: string | null;
  created_at: string;
}

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
  ts: string;
}
