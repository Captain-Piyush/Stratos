import React from 'react';
import type { HistoricalOutcome } from '../types/backend';

interface Props {
    outcome: HistoricalOutcome | null;
    modelStrategy: string;
}

export const ActualOutcomePanel: React.FC<Props> = ({ outcome, modelStrategy }) => {
    if (!outcome) return null;

    const isMatch = outcome.actual_strategy === modelStrategy;

    return (
        <div className="panel" style={{ borderLeft: '4px solid #facc15', backgroundColor: 'var(--bg-dark)' }}>
            <h3 className="panel-title" style={{ color: '#facc15' }}>ACTUAL HISTORICAL OUTCOME</h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>STRATOS MODEL DECISION</div>
                    <div style={{ fontWeight: 600 }}>{modelStrategy}</div>
                </div>
                
                <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>ACTUAL STRATEGY</div>
                    <div style={{ fontWeight: 600, color: isMatch ? 'var(--accent-green)' : 'var(--accent-yellow)' }}>
                        {outcome.actual_strategy || "UNKNOWN"}
                    </div>
                </div>
                
                <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>ACTUAL FINISH POSITION</div>
                    <div>{outcome.actual_finish_position ? `P${outcome.actual_finish_position}` : (outcome.outcome_status === 'RETIRED' ? 'DNF' : 'UNKNOWN')}</div>
                </div>
                
                <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>PROVENANCE</div>
                    <div style={{ fontSize: 12 }}>{outcome.strategy_source}</div>
                </div>
            </div>
            
            {outcome.outcome_status === 'RETIRED' && (
                <div style={{ marginTop: 16, color: 'var(--accent-red)' }}>
                    Driver retired on Lap {outcome.retirement_lap} ({outcome.retirement_reason || "Unknown reason"})
                </div>
            )}
        </div>
    );
};
