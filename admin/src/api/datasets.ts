import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { requestAt } from './client';

const BASE = '/api/admin/datasets';

export type Category = 'simple' | 'reasoning' | 'multi_context' | 'conditional';
export type DatasetStatus = 'pending' | 'running' | 'ready' | 'failed';

export interface Dataset {
  id: string;
  name: string;
  model: { id: string; provider: string; name: string } | null;
  samplePerFile: number;
  mix: Record<Category, number>;
  labels: string[];
  status: DatasetStatus;
  error: string | null;
  /** Files found in the archive, and how many the generator has parsed so far. */
  fileCount: number;
  parsedCount: number;
  pairCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface DatasetPage {
  items: Dataset[];
  total: number;
  page: number;
  pageSize: number;
}

export interface DatasetInput {
  name: string;
  archive: File;
  modelId: string;
  samplePerFile: number;
  mix: Record<string, number>;
  labels: string[];
}

/** One generated pair, as it sits in the stored result file (raw, not camelized). */
export interface DatasetPair {
  source_file: string;
  context: string;
  question: string;
  answer: string;
  category: Category;
  labels: string[];
}

const keys = {
  list: (page: number) => ['datasets', page] as const,
  one: (id: string) => ['datasets', id] as const,
};

export function useDatasets(page = 1, pageSize = 20) {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  return useQuery({
    queryKey: keys.list(page),
    queryFn: () => requestAt<DatasetPage>(`${BASE}?${params}`),
    // Generation runs in the background: poll while anything is still working,
    // and only while the tab is in front.
    refetchInterval: (query) =>
      query.state.data?.items.some((d) => d.status === 'pending' || d.status === 'running')
        ? 15_000
        : false,
  });
}

export function useDataset(id: string) {
  return useQuery({
    queryKey: keys.one(id),
    queryFn: () => requestAt<Dataset>(`${BASE}/${id}`),
  });
}

export function useCreateDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ archive, ...values }: DatasetInput) => {
      const body = new FormData();
      body.append('payload', JSON.stringify(values));
      body.append('archive', archive);
      return requestAt<Dataset>(BASE, { method: 'POST', body });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['datasets'] }),
  });
}

/** The generated pairs file, fetched whole for the client to render. */
export function useDatasetPairs(datasetId: string | null) {
  return useQuery({
    queryKey: ['datasets', datasetId, 'pairs'] as const,
    queryFn: () => requestAt<DatasetPair[]>(`${BASE}/${datasetId}/pairs`),
    enabled: !!datasetId,
  });
}
