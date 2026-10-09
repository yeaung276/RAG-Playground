import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import RequireAuth from './components/RequireAuth';
import Login from './pages/Login';
import KnowledgeList from './pages/KnowledgeList';
import ControlPanel from './pages/ControlPanel';
import ControlChat from './pages/ControlChat';
import FileBrowser from './pages/FileBrowser';
import Agents from './pages/Agents';
import Docs from './docs/Docs';
import Landing from './docs/Landing';
import Models from './pages/Models';
import Evaluation from './pages/Evaluation';
import DatasetDetail from './pages/DatasetDetail';
import ExperimentDetail from './pages/ExperimentDetail';
import { Toaster, pushToast } from './components/Toast';
import { errorMessage } from './api/client';
import './index.css';

// Surface every query/mutation failure as a toast, from one place.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false },
  },
  queryCache: new QueryCache({
    onError: (err, query) => {
      if (query.queryKey[0] === 'me') return;
      pushToast(errorMessage(err));
    },
  }),
  mutationCache: new MutationCache({
    onError: (err) => pushToast(errorMessage(err)),
  }),
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route element={<RequireAuth />}>
            <Route path="/docs" element={<Navigate to="/docs/widget" replace />} />
            <Route path="/docs/:section" element={<Docs />} />
            <Route element={<Layout />}>
              <Route path="/knowledge" element={<KnowledgeList />} />
              <Route path="/knowledge/:id" element={<FileBrowser />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/models" element={<Models />} />
              <Route path="/evaluation" element={<Evaluation />} />
              <Route path="/evaluation/datasets/:id" element={<DatasetDetail />} />
              <Route path="/evaluation/experiments/:id" element={<ExperimentDetail />} />
              <Route path="/control" element={<ControlPanel />} />
              <Route path="/control/:id" element={<ControlChat />} />
              <Route path="*" element={<Navigate to="/control" replace />} />
            </Route>
          </Route>
        </Routes>
      </HashRouter>
      <Toaster />
    </QueryClientProvider>
  </StrictMode>,
);
