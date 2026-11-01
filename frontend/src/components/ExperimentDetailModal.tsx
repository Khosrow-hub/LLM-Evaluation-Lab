import React, { useState } from 'react';
import {
  CheckCircle2,
  Clock,
  Search,
  X,
  XCircle,
} from 'lucide-react';
import type { CaseResult, Experiment } from '../types';

interface ExperimentDetailModalProps {
  experiment: Experiment;
  onClose: () => void;
}

export const ExperimentDetailModal: React.FC<ExperimentDetailModalProps> = ({
  experiment,
  onClose,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCase, setSelectedCase] = useState<CaseResult | null>(
    experiment.results && experiment.results.length > 0 ? experiment.results[0] : null
  );

  const results = experiment.results || [];
  const filteredCases = results.filter(
    (c) =>
      c.case_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.input.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const summary = experiment.summary;
  const cfg = experiment.config;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
      onClick={onClose}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: 1100,
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          backgroundColor: '#0c101c',
          borderColor: 'rgba(6, 182, 212, 0.2)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '16px 24px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(0, 0, 0, 0.2)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff' }}>
                {cfg.name}
              </h2>
              <span className={`badge badge-${experiment.status}`}>
                {experiment.status}
              </span>
              {(experiment.is_demo || experiment.id?.startsWith('demo-') || cfg.experiment_id.startsWith('demo-')) && (
                <span
                  className="badge"
                  style={{
                    background: 'rgba(234, 179, 8, 0.15)',
                    color: '#fbbf24',
                    border: '1px solid rgba(234, 179, 8, 0.35)',
                    fontSize: '0.675rem',
                    fontWeight: 600,
                  }}
                >
                  DEMO DATA
                </span>
              )}
            </div>
            <div style={{ display: 'flex', gap: 16, marginTop: 4, fontSize: '0.775rem', color: 'var(--text-muted)' }}>
              <span>ID: <code className="mono">{cfg.experiment_id.slice(0, 8)}</code></span>
              <span>Provider: <strong style={{ color: 'var(--text-secondary)' }}>{cfg.provider?.name}</strong></span>
              <span>Model: <strong style={{ color: 'var(--text-secondary)' }}>{cfg.provider?.model || '(default)'}</strong></span>
              <span>Dataset: <span style={{ color: 'var(--text-secondary)' }}>{cfg.dataset_path}</span></span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-secondary btn-sm"
            style={{ padding: 6, borderRadius: 'var(--radius-full)' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Summary Metric Ribbon */}
        {summary && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: 12,
              padding: '16px 24px',
              borderBottom: '1px solid var(--border)',
              background: 'rgba(255, 255, 255, 0.01)',
            }}
          >
            <div className="stat-card" style={{ padding: '10px 14px' }}>
              <span className="stat-label">Total Cases</span>
              <span className="stat-value" style={{ fontSize: '1.3rem' }}>{summary.total_cases}</span>
            </div>
            <div className="stat-card" style={{ padding: '10px 14px' }}>
              <span className="stat-label">Success Rate</span>
              <span className="stat-value" style={{ fontSize: '1.3rem', color: summary.success_rate >= 0.9 ? '#34d399' : '#fbbf24' }}>
                {(summary.success_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="stat-card" style={{ padding: '10px 14px' }}>
              <span className="stat-label">Mean Latency</span>
              <span className="stat-value" style={{ fontSize: '1.3rem' }}>
                {summary.mean_latency_ms ? `${summary.mean_latency_ms.toFixed(1)}ms` : 'N/A'}
              </span>
            </div>
            {Object.entries(summary.aggregate_metrics || {}).map(([metric, score]) => (
              <div key={metric} className="stat-card" style={{ padding: '10px 14px' }}>
                <span className="stat-label">{metric.replace(/_/g, ' ')}</span>
                <span className="stat-value" style={{ fontSize: '1.3rem', color: '#22d3ee' }}>
                  {metric.includes('latency') ? `${score.toFixed(1)}ms` : (score * 100).toFixed(1) + '%'}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Modal Body: Left Case List, Right Case Detail */}
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', flex: 1, minHeight: 0 }}>
          {/* Case list sidebar */}
          <div
            style={{
              borderRight: '1px solid var(--border)',
              display: 'flex',
              flexDirection: 'column',
              background: 'rgba(0, 0, 0, 0.15)',
            }}
          >
            <div style={{ padding: 12, borderBottom: '1px solid var(--border)' }}>
              <div style={{ position: 'relative' }}>
                <Search
                  size={14}
                  style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
                />
                <input
                  type="text"
                  placeholder="Filter cases…"
                  className="form-control"
                  style={{ paddingLeft: 30, fontSize: '0.8rem', padding: '6px 10px 6px 30px' }}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
              {filteredCases.map((c) => {
                const isSelected = selectedCase?.case_id === c.case_id;
                const hasError = !!c.error;
                return (
                  <div
                    key={c.case_id}
                    onClick={() => setSelectedCase(c)}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md)',
                      marginBottom: 4,
                      cursor: 'pointer',
                      background: isSelected ? 'rgba(6, 182, 212, 0.12)' : 'transparent',
                      border: `1px solid ${isSelected ? 'rgba(6, 182, 212, 0.3)' : 'transparent'}`,
                      transition: 'all 0.15s',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 600, color: isSelected ? '#22d3ee' : '#cbd5e1' }}>
                        {c.case_id}
                      </span>
                      {hasError ? (
                        <XCircle size={14} color="#f43f5e" />
                      ) : (
                        <CheckCircle2 size={14} color="#10b981" />
                      )}
                    </div>
                    <div
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-muted)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        marginTop: 4,
                      }}
                    >
                      {c.input}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Case Detail View */}
          <div style={{ padding: 20, overflowY: 'auto' }}>
            {selectedCase ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#fff' }}>
                    Case: <span className="mono" style={{ color: '#22d3ee' }}>{selectedCase.case_id}</span>
                  </h3>
                  {selectedCase.latency_ms && (
                    <span style={{ fontSize: '0.775rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Clock size={13} /> {selectedCase.latency_ms.toFixed(1)} ms
                    </span>
                  )}
                </div>

                {/* Input Prompt Box */}
                <div style={{ background: '#090d16', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 14 }}>
                  <div style={{ fontSize: '0.725rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>
                    Input Prompt
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#e2e8f0', whiteSpace: 'pre-wrap' }}>
                    {selectedCase.input}
                  </div>
                </div>

                {/* Model Output */}
                <div style={{ background: '#090d16', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: '0.725rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--primary)' }}>
                      Model Output
                    </span>
                    {(selectedCase.is_simulated || cfg.provider?.name === 'mock') && (
                      <span
                        className="badge"
                        style={{
                          background: 'rgba(168, 85, 247, 0.15)',
                          color: '#c084fc',
                          border: '1px solid rgba(168, 85, 247, 0.35)',
                          fontSize: '0.65rem',
                          fontWeight: 600,
                        }}
                      >
                        SIMULATED OUTPUT
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#f8fafc', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                    {selectedCase.output || (
                      <span style={{ color: '#f43f5e', fontStyle: 'italic' }}>
                        Error: {selectedCase.error || 'No output recorded'}
                      </span>
                    )}
                  </div>
                </div>

                {/* Reference Ground Truth */}
                {selectedCase.reference && (
                  <div style={{ background: '#090d16', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 14 }}>
                    <div style={{ fontSize: '0.725rem', fontWeight: 600, textTransform: 'uppercase', color: '#10b981', marginBottom: 6 }}>
                      Expected Reference
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#94a3b8', whiteSpace: 'pre-wrap' }}>
                      {selectedCase.reference}
                    </div>
                  </div>
                )}

                {/* Metric Scores */}
                <div>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>
                    Evaluator Scores
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
                    {selectedCase.metrics.map((m) => (
                      <div
                        key={m.metric_name}
                        style={{
                          background: 'rgba(255, 255, 255, 0.02)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--radius-md)',
                          padding: 10,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                        }}
                      >
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          {m.metric_name}
                        </span>
                        <span
                          className="mono"
                          style={{
                            fontSize: '0.9rem',
                            fontWeight: 700,
                            color: m.score !== null ? (m.score > 0 ? '#34d399' : '#f87171') : 'var(--text-muted)',
                          }}
                        >
                          {m.score !== null ? m.score.toFixed(3) : 'null'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                Select a test case on the left to inspect its outputs.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
