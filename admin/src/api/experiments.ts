import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { requestAt } from './client';
import type { KnowledgeBaseConfig } from './config';
const BASE = '/api/admin/experiments';

export type ExperimentStatus = 'pending' | 'importing' | 'running' | 'success' | 'failed';

const isActive = (status: ExperimentStatus) => status !== 'success' && status !== 'failed';

export const METRICS = ['context_precision', 'context_recall', 'hit_rate', 'mrr'] as const;
export type Metric = (typeof METRICS)[number];

export const METRIC_LABELS: Record<Metric, string> = {
  context_precision: 'Context precision',
  context_recall: 'Context recall',
  hit_rate: 'Hit rate',
  mrr: 'MRR',
};

export interface RetrievalConfig {
  indexTypes: KnowledgeBaseConfig['indexTypes'];
  topK: number | null;
  rerankOn: 'parent' | 'child' | null;
  rerankPool: number | null;
  prefetchLimit: number | null;
}

export interface Experiment {
  id: string;
  name: string;
  datasetId: string;
  knowledgeId: string | null;
  kbConfig: KnowledgeBaseConfig | null;
  retrievalConfig: RetrievalConfig;
  metrics: Metric[];
  scores: Partial<Record<Metric, number>> | null;
  status: ExperimentStatus;
  error: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ExperimentSummary {
  id: string;
  name: string;
  indexTypes: RetrievalConfig['indexTypes'];
  topK: number | null;
  rerankOn: RetrievalConfig['rerankOn'];
  metricCount: number;
  status: ExperimentStatus;
  error: string | null;
  createdAt: string;
}

export interface ExperimentPage {
  items: ExperimentSummary[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ExperimentScores {
  id: string;
  name: string;
  createdAt: string;
  scores: Partial<Record<Metric, number>>;
}

export interface ExperimentInput {
  datasetId: string;
  knowledgeId: string | null;
  kbConfig: KnowledgeBaseConfig | null;
  retrievalConfig: RetrievalConfig;
  metrics: Metric[];
}

/** How much of a pair's golden text the retrieved chunks hold. */
export type PairStatus = 'full' | 'partial' | 'miss';

/** A chunk retrieved for a pair; `highlights` are [start, end) ranges of golden text in `content`. */
export interface RetrievedChunk {
  rank: number;
  chunk_id: string;
  source: string | null;
  score: number;
  content: string;
  highlights: [number, number][];
}

/** Per-pair scores, as they sit in the stored result file (raw, not camelized). */
export interface ExperimentResult {
  metrics: Record<string, number>;
  pairs: {
    question: string;
    answer: string;
    category: string;
    labels: string[];
    context: string;
    source_file: string;
    generated_answer: string | null;
    retrieved: RetrievedChunk[];
    scores: Record<string, number>;
    status: PairStatus;
  }[];
}

const keys = {
  list: (page: number, datasetId: string | null) =>
    ['experiments', page, datasetId ?? 'all'] as const,
  one: (id: string) => ['experiments', id] as const,
};

export function useExperiments(page = 1, pageSize = 20, datasetId: string | null = null) {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  if (datasetId) params.set('datasetId', datasetId);
  return useQuery({
    queryKey: keys.list(page, datasetId),
    queryFn: () => requestAt<ExperimentPage>(`${BASE}?${params}`),
    // Runs are scored in the background: poll while anything is still working.
    refetchInterval: (query) =>
      query.state.data?.items.some((e) => isActive(e.status)) ? 15_000 : false,
  });
}

/** Scores of every successful run on a dataset, oldest first. */
export function useScoreBoard(datasetId: string) {
  const params = new URLSearchParams({ datasetId });
  return useQuery({
    queryKey: ['experiments', 'score_board', datasetId] as const,
    queryFn: () => requestAt<ExperimentScores[]>(`${BASE}/score_board?${params}`),
  });
}

export function useExperiment(id: string | null) {
  return useQuery({
    queryKey: keys.one(id ?? ''),
    queryFn: () => requestAt<Experiment>(`${BASE}/${id}`),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data && isActive(query.state.data.status) ? 15_000 : false,
  });
}

export function useCreateExperiment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: ExperimentInput) =>
      requestAt<Experiment>(BASE, { method: 'POST', json: values }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['experiments'] }),
  });
}

export function useRerunExperiment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => requestAt<Experiment>(`${BASE}/${id}/rerun`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['experiments'] }),
  });
}

/** The scored result file, fetched whole once the run is ready. */
export function useExperimentResult(id: string | null, ready: boolean) {
  return useQuery({
    queryKey: ['experiments', id, 'result'] as const,
    queryFn: () => requestAt<ExperimentResult>(`${BASE}/${id}/result`),
    enabled: !!id && ready,
  });
}

/** Best score per metric among earlier successful runs on the same dataset. */
export function useBestScores(id: string | null) {
  return useQuery({
    queryKey: ['experiments', id, 'best'] as const,
    queryFn: () => requestAt<Partial<Record<Metric, number>>>(`${BASE}/${id}/best`),
    enabled: !!id,
  });
}
