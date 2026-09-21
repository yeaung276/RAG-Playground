import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, FlaskConical, Play, Plus } from 'lucide-react';
import Header from '../components/Header';
import DatasetList from '../components/DatasetList';
import GenerateDatasetModal, {
  type GenerateDatasetValues,
} from '../components/GenerateDatasetModal';
import ExperimentForm from '../components/ExperimentForm';
import ExperimentList from '../components/ExperimentList';
import ExperimentDetail from '../components/ExperimentDetail';
import { useCreateDataset } from '../api/datasets';

type View = 'datasets' | 'experiments' | 'experiment';

export default function Evaluation() {
  const navigate = useNavigate();
  const [view, setView] = useState<View>('datasets');
  const [newDataset, setNewDataset] = useState(false);
  const [newExperiment, setNewExperiment] = useState(false);
  const [experimentId, setExperimentId] = useState<string | null>(null);
  const createDataset = useCreateDataset();

  const tab = (active: boolean) =>
    `flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition ${
      active ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100'
    }`;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header>
        <FlaskConical size={18} className="text-indigo-600" />
        <h1 className="truncate text-base font-semibold">Evaluation</h1>
      </Header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {view === 'experiment' && experimentId ? (
          <ExperimentDetail onBack={() => setView('experiments')} />
        ) : (
          <>
            <div className="mb-5 flex items-center justify-between">
              <div className="flex gap-1">
                <button className={tab(view === 'datasets')} onClick={() => setView('datasets')}>
                  <Database size={14} /> Datasets
                </button>
                <button
                  className={tab(view === 'experiments')}
                  onClick={() => setView('experiments')}
                >
                  <FlaskConical size={14} /> Experiments
                </button>
              </div>
              <button
                onClick={() =>
                  view === 'datasets' ? setNewDataset(true) : setNewExperiment(true)
                }
                className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
              >
                {view === 'datasets' ? (
                  <>
                    <Plus size={16} /> New dataset
                  </>
                ) : (
                  <>
                    <Play size={16} /> New experiment
                  </>
                )}
              </button>
            </div>

            {view === 'datasets' && (
              <DatasetList onOpen={(id) => navigate(`/evaluation/datasets/${id}`)} />
            )}
            {view === 'experiments' && (
              <ExperimentList
                onOpen={(id) => {
                  setExperimentId(id);
                  setView('experiment');
                }}
              />
            )}
          </>
        )}
      </main>

      <GenerateDatasetModal
        open={newDataset}
        onClose={() => setNewDataset(false)}
        onSubmit={(values: GenerateDatasetValues) =>
          createDataset.mutateAsync(values).then(() => undefined)
        }
      />
      <ExperimentForm open={newExperiment} onOpenChange={setNewExperiment} />
    </div>
  );
}
