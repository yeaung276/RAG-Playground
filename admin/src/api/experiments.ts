import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { requestAt } from './client';
import type { KnowledgeBaseConfig } from './config';
import type { DatasetStatus } from './datasets';

const BASE = '/api/admin/experiments';

export const METRICS = ['context_precision', 'context_recall', 'hit_rate', 'mrr'] as const;
export type Metric = (typeof METRICS)[number];

export interface RetrievalConfig {
  indexTypes: KnowledgeBaseConfig['indexTypes'];
  topK: number | null;
  rerankOn: 'parent' | 'child' | null;
  rerankPool: number | null;
  prefetchLimit: number | null;
}

export interface Experiment {
  id: string;
  datasetId: string;
  knowledgeId: string | null;
  indexingConfig: KnowledgeBaseConfig | null;
  knowledgeConfig: RetrievalConfig;
  metrics: Metric[];
  status: DatasetStatus;
  error: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ExperimentPage {
  items: Experiment[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ExperimentInput {
  datasetId: string;
  knowledgeId: string | null;
  indexingConfig: KnowledgeBaseConfig | null;
  knowledgeConfig: RetrievalConfig;
  metrics: Metric[];
}

/** Per-pair scores, as they sit in the stored result file (raw, not camelized). */
export interface ExperimentResult {
  metrics: Record<string, number>;
  pairs: {
    question: string;
    answer: string;
    category: string;
    labels: string[];
    scores: Record<string, number>;
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
      query.state.data?.items.some((e) => e.status === 'pending' || e.status === 'running')
        ? 15_000
        : false,
  });
}

export function useExperiment(id: string | null) {
  return useQuery({
    queryKey: keys.one(id ?? ''),
    queryFn: () => requestAt<Experiment>(`${BASE}/${id}`),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' || query.state.data?.status === 'running'
        ? 15_000
        : false,
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

/** The scored result file, fetched whole once the run is ready. */
export function useExperimentResult(id: string | null, ready: boolean) {
  return useQuery({
    queryKey: ['experiments', id, 'result'] as const,
    queryFn: () => requestAt<ExperimentResult>(`${BASE}/${id}/result`),
    enabled: !!id && ready,
  });
}
