import React from 'react';
import type { StrategyDecisionEvent, CandidateSummary } from '../types/backend';

interface Props {
    decision: StrategyDecisionEvent;
}

export const PitWindowPlot: React.FC<Props> = ({ decision }) => {
    // This timeline visually displays Pit T+1, T+2, T+3
    // It's a simple CSS-based timeline using the candidate_summary

    // Example mapping of expected strategies:
    const pitCandidates = decision.candidate_summary.filter(c => c.strategy_id.includes('PIT') || c.strategy_id.includes('STAY_OUT'));

    return (
        <div style={{ padding: '16px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid var(--border-color)', paddingBottom: '16px', position: 'relative' }}>
                <div style={{ position: 'absolute', top: -5, left: '0%', width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--text-muted)' }} />
                <div style={{ position: 'absolute', top: -5, left: '25%', width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--text-muted)' }} />
                <div style={{ position: 'absolute', top: -5, left: '50%', width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--text-muted)' }} />
                <div style={{ position: 'absolute', top: -5, left: '75%', width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--text-muted)' }} />
                <div style={{ position: 'absolute', top: -5, left: '100%', width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--text-muted)' }} />
                
                {['Current', 'T+1', 'T+2', 'T+3'].map((label, idx) => (
                    <div key={label} style={{ flex: 1, textAlign: idx === 0 ? 'left' : 'center', color: 'var(--text-muted)', fontSize: 12 }}>
                        {label}
                    </div>
                ))}
            </div>
            
            <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {pitCandidates.map(c => (
                    <div key={c.strategy_id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: c.is_selected ? 'var(--accent-green)' : 'var(--border-color)' }} />
                        <span style={{ color: c.is_selected ? 'var(--text-main)' : 'var(--text-muted)' }}>{c.description}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};
