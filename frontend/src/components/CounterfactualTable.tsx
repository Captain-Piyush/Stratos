import React, { useState } from 'react';
import type { CandidateSummary } from '../types/backend';

interface Props {
    candidates: CandidateSummary[];
}

export const CounterfactualTable: React.FC<Props> = ({ candidates }) => {
    const [selectedId, setSelectedId] = useState<string | null>(null);

    const sorted = [...candidates].sort((a, b) => (a.expected_time || 0) - (b.expected_time || 0));
    
    const selectedCandidate = candidates.find(c => c.is_selected);
    const alternateCandidate = candidates.find(c => c.strategy_id === selectedId);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, textAlign: 'left' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                            <th style={{ padding: 8 }}>Strategy</th>
                            <th style={{ padding: 8 }}>Expected Time</th>
                            <th style={{ padding: 8 }}>Median Time</th>
                            <th style={{ padding: 8 }}>P10–P90 Range</th>
                            <th style={{ padding: 8 }}>Score</th>
                            <th style={{ padding: 8 }}>Validation</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sorted.map(c => (
                            <tr 
                                key={c.strategy_id} 
                                onClick={() => setSelectedId(c.strategy_id)}
                                style={{ 
                                    borderBottom: '1px solid var(--border-color)', 
                                    cursor: 'pointer',
                                    backgroundColor: selectedId === c.strategy_id ? 'var(--bg-panel-hover)' : 'transparent',
                                    color: c.is_selected ? 'var(--accent-green)' : 'inherit'
                                }}
                            >
                                <td style={{ padding: 8, fontWeight: c.is_selected ? 600 : 'normal' }}>
                                    {c.description} {c.is_selected && "(SELECTED)"}
                                </td>
                                <td style={{ padding: 8 }}>{c.expected_time?.toFixed(1)}s</td>
                                <td style={{ padding: 8 }}>{c.median_time?.toFixed(1)}s</td>
                                <td style={{ padding: 8 }}>{c.p10_time?.toFixed(1)} – {c.p90_time?.toFixed(1)}s</td>
                                <td style={{ padding: 8 }}>{c.decision_score?.toFixed(1)}</td>
                                <td style={{ padding: 8 }}>{c.constraint_status}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {selectedId && selectedCandidate && alternateCandidate && selectedId !== selectedCandidate.strategy_id && (
                <div style={{ padding: 12, backgroundColor: 'var(--bg-panel-hover)', borderRadius: 6, fontSize: 13 }}>
                    <div style={{ color: 'var(--text-muted)', marginBottom: 8 }}>WHAT WOULD HAVE CHANGED?</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                        <div>
                            <div style={{ color: 'var(--accent-green)' }}>SELECTED: {selectedCandidate.description}</div>
                            <div>Expected: {selectedCandidate.expected_time?.toFixed(1)}s</div>
                        </div>
                        <div>
                            <div style={{ color: 'var(--accent-blue)' }}>ALTERNATIVE: {alternateCandidate.description}</div>
                            <div>Expected: {alternateCandidate.expected_time?.toFixed(1)}s</div>
                            <div style={{ color: 'var(--accent-yellow)', marginTop: 4 }}>
                                Delta: {((alternateCandidate.expected_time || 0) - (selectedCandidate.expected_time || 0)).toFixed(1)}s
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
