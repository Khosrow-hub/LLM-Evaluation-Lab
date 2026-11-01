import React, { useState } from 'react';
import {
  Activity,
  Eye,
  GitCompare,
  PlusCircle,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { deleteExperiment, getExperiment } from '../api';
import type { Experiment, ExperimentListItem } from '../types';
import { ExperimentDetailModal } from './ExperimentDetailModal';

interface ExperimentsListProps {
  experiments: ExperimentListItem[];
  error?: string | null;
  onRefresh: () => void;
  onNewRun: () => void;
  onCompareWith: (baselineId: string, candidateId: string) => void;
}

export const ExperimentsList: React.FC<ExperimentsListProps> = ({
  experiments,
  error,
  onRefresh,
  onNewRun,
  onCompareWith,
}) => {
  const [selectedExp, setSelectedExp] = useState<Experiment | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);

  const handleView = async (id: string) => {
    setLoadingId(id);
    try {
      const exp = await getExperiment(id);
      setSelectedExp(exp);
    } finally {
      setLoadingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`Delete experiment ${id}? This cannot be undone.`)) return;
    setIsDeleting(id);
    try {
      await deleteExperiment(id);
      onRefresh();
    } finally {
      setIsDeleting(null);
    }
  };

  const toggleSelectForCompare = (id: string) => {
    setSelectedForCompare((prev) => {
      if (prev.includes(id)) {
        return prev.filter((x) => x !== id);
      }
      if (prev.length >= 2) {
        return [prev[1], id];
      }
      return [...prev, id];
    });
  };

  return (
    <div style={{ padding: '0 24px 32px' }}>
      {/* Top Banner & Actions */}
      {error && (
        <div
          style={{
            padding: '12px 16px',
            marginBottom: 16,
            borderRadius: 'var(--radius-md)',
            background: 'rgba(244, 63, 94, 0.1)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            color: '#f43f5e',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>{error}</span>
          <button onClick={onRefresh} className="btn btn-secondary btn-sm">
            Retry
          </button>
        </div>
      )}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 20,
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#fff' }}>
            Evaluation Runs
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Track reproducible experiment runs, compare metrics, and audit model behavior.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {selectedForCompare.length === 2 && (
            <button
              onClick={() => onCompareWith(selectedForCompare[0], selectedForCompare[1])}
              className="btn btn-primary"
            >
              <GitCompare size={16} />
              Compare ({selectedForCompare[0].slice(0, 6)} vs {selectedForCompare[1].slice(0, 6)})
            </button>
          )}

          <button onClick={onRefresh} className="btn btn-secondary">
            <RefreshCw size={15} />
            Refresh
          </button>

          <button onClick={onNewRun} className="btn btn-primary">
            <PlusCircle size={16} />
            New Evaluation
          </button>
        </div>
      </div>

      {/* Experiments Table */}
      {experiments.length === 0 ? (
        <div
          className="glass-panel"
          style={{
            textAlign: 'center',
            padding: '60px 20px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <Activity size={36} color="var(--primary)" />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>No experiments recorded yet</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: 420 }}>
            Launch an evaluation against your dataset to calculate deterministic metrics, latencies, and regression baselines.
          </p>
          <button onClick={onNewRun} className="btn btn-primary" style={{ marginTop: 8 }}>
            <PlusCircle size={16} /> Run First Evaluation
          </button>
        </div>
      ) : (
        <div className="table-container glass-panel">
          <table className="eval-table">
            <thead>
              <tr>
                <th style={{ width: 44, textAlign: 'center' }}>Compare</th>
                <th>Experiment Name</th>
                <th>Status</th>
                <th>Started</th>
                <th>Completed</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {experiments.map((exp) => {
                const isSelected = selectedForCompare.includes(exp.id);
                const compareRole =
                  selectedForCompare[0] === exp.id
                    ? 'Baseline'
                    : selectedForCompare[1] === exp.id
                    ? 'Candidate'
                    : null;

                return (
                  <tr key={exp.id}>
                    <td style={{ textAlign: 'center' }}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectForCompare(exp.id)}
                        style={{ cursor: 'pointer', accentColor: '#06b6d4' }}
                        title="Select 2 experiments to run Paired Bootstrap comparison"
                      />
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 600, color: '#fff' }}>{exp.name}</span>
                        {(exp.is_demo || exp.id.startsWith('demo-')) && (
                          <span
                            className="badge"
                            style={{
                              background: 'rgba(234, 179, 8, 0.15)',
                              color: '#fbbf24',
                              border: '1px solid rgba(234, 179, 8, 0.35)',
                              fontSize: '0.675rem',
                              fontWeight: 600,
                            }}
                            title="Offline demonstration data"
                          >
                            DEMO DATA
                          </span>
                        )}
                        {compareRole && (
                          <span
                            className="badge"
                            style={{
                              background: compareRole === 'Baseline' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                              color: compareRole === 'Baseline' ? '#60a5fa' : '#34d399',
                              fontSize: '0.675rem',
                            }}
                          >
                            {compareRole}
                          </span>
                        )}
                      </div>
                      <div className="mono" style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                        {exp.id}
                      </div>
                    </td>
                    <td>
                      <span className={`badge badge-${exp.status}`}>
                        {exp.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {exp.started_at ? new Date(exp.started_at).toLocaleString() : '—'}
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {exp.completed_at ? new Date(exp.completed_at).toLocaleString() : '—'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: 6 }}>
                        <button
                          onClick={() => handleView(exp.id)}
                          className="btn btn-secondary btn-sm"
                          disabled={loadingId === exp.id}
                        >
                          <Eye size={14} />
                          {loadingId === exp.id ? 'Loading…' : 'Details'}
                        </button>
                        <button
                          onClick={() => handleDelete(exp.id)}
                          className="btn btn-danger btn-sm"
                          disabled={isDeleting === exp.id}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Modal */}
      {selectedExp && (
        <ExperimentDetailModal
          experiment={selectedExp}
          onClose={() => setSelectedExp(null)}
        />
      )}
    </div>
  );
};
