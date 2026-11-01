import React, { useEffect, useState } from 'react';
import { checkHealth, listExperiments } from './api';
import { ComparisonView } from './components/ComparisonView';
import { DatasetView } from './components/DatasetView';
import { ExperimentsList } from './components/ExperimentsList';
import { Header } from './components/Header';
import { NewEvaluation } from './components/NewEvaluation';
import { ReportsView } from './components/ReportsView';
import type { ExperimentListItem } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'experiments' | 'new-eval' | 'compare' | 'datasets' | 'reports'>('experiments');
  const [apiConnected, setApiConnected] = useState(false);
  const [experiments, setExperiments] = useState<ExperimentListItem[]>([]);
  const [compareBaseline, setCompareBaseline] = useState<string>('');
  const [compareCandidate, setCompareCandidate] = useState<string>('');
  const [listError, setListError] = useState<string | null>(null);

  const refreshAll = async () => {
    const health = await checkHealth();
    setApiConnected(health.isConnected);

    try {
      const list = await listExperiments();
      setExperiments(list);
      setListError(null);
    } catch (err: any) {
      setListError(err.message || 'Failed to load experiments');
    }
  };

  useEffect(() => {
    refreshAll();
    const interval = setInterval(refreshAll, 12000);
    return () => clearInterval(interval);
  }, []);

  const handleCompareWith = (baselineId: string, candidateId: string) => {
    setCompareBaseline(baselineId);
    setCompareCandidate(candidateId);
    setActiveTab('compare');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        apiConnected={apiConnected}
      />

      <main style={{ flex: 1 }}>
        {activeTab === 'experiments' && (
          <ExperimentsList
            experiments={experiments}
            error={listError}
            onRefresh={refreshAll}
            onNewRun={() => setActiveTab('new-eval')}
            onCompareWith={handleCompareWith}
          />
        )}

        {activeTab === 'new-eval' && (
          <NewEvaluation
            onEvaluationCompleted={() => {
              refreshAll();
              setActiveTab('experiments');
            }}
            onCancel={() => setActiveTab('experiments')}
          />
        )}

        {activeTab === 'compare' && (
          <ComparisonView
            experiments={experiments}
            initialBaselineId={compareBaseline}
            initialCandidateId={compareCandidate}
          />
        )}

        {activeTab === 'datasets' && <DatasetView />}

        {activeTab === 'reports' && <ReportsView experiments={experiments} />}
      </main>

      <footer
        style={{
          borderTop: '1px solid var(--border)',
          padding: '16px 24px',
          textAlign: 'center',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 8,
          background: 'rgba(0, 0, 0, 0.4)',
        }}
      >
        <div>
          LLM Evaluation Lab &copy; 2026 Pratham Gupta &middot; Licensed under MIT
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <a
            href="https://github.com/prathamforgelab/LLM-Evaluation-Lab"
            target="_blank"
            rel="noreferrer"
            style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}
          >
            GitHub Repository
          </a>
          <a
            href="/api/docs"
            target="_blank"
            rel="noreferrer"
            style={{ color: 'var(--primary)', textDecoration: 'none' }}
          >
            FastAPI OpenAPI Docs
          </a>
        </div>
      </footer>
    </div>
  );
};

export default App;
