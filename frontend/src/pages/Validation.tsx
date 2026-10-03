import React, { useEffect, useState } from 'react';
import { getApiBaseUrl } from '../config';

export function Validation() {
    const [data, setData] = useState<any>(null);

    useEffect(() => {
        fetch(`${getApiBaseUrl()}/api/validation`)
            .then(res => res.json())
            .then(setData)
            .catch(console.error);
    }, []);

    if (!data) return <div style={{ padding: 16 }}>INITIALIZING VALIDATION MODULE...</div>;

    return (
        <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="panel" style={{ borderLeft: '2px solid var(--accent-amber)' }}>
                <div className="panel-header">WARNING: RETROSPECTIVE EVALUATION</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{data.interpretation}</div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '16px' }}>
                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">DATASET TOPOLOGY</div>
                    <div className="data-row">
                        <span className="data-label">TOTAL SESSIONS</span>
                        <span className="data-value mono-num">{data.dataset.total_races}</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">CALIBRATION SESSIONS</span>
                        <span className="data-value mono-num">{data.dataset.calibration_races}</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">HOLDOUT SESSIONS</span>
                        <span className="data-value mono-num">{data.dataset.holdout_races}</span>
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '8px' }}>
                        HOLDOUTS: {data.holdouts.join(', ')}<br/>
                        FILTER: DRIVERS COMPLETING L1
                    </div>
                </div>
                
                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">VALIDATION METRICS (PHASE 5C)</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <div style={{ backgroundColor: 'var(--bg-dark)', padding: '12px', border: '1px solid var(--border-subtle)' }}>
                            <div className="data-label">CORRECTED MAE</div>
                            <div className="data-value mono-num" style={{ fontSize: '18px', marginTop: '4px' }}>{data.metrics.corrected_mae}s</div>
                        </div>
                        <div style={{ backgroundColor: 'var(--bg-dark)', padding: '12px', border: '1px solid var(--border-subtle)' }}>
                            <div className="data-label">CORRECTED MEDIAN AE</div>
                            <div className="data-value mono-num" style={{ fontSize: '18px', marginTop: '4px' }}>{data.metrics.corrected_median_ae}s</div>
                        </div>
                        <div style={{ backgroundColor: 'var(--bg-dark)', padding: '12px', border: '1px solid var(--border-subtle)' }}>
                            <div className="data-label">P10-P90 COVERAGE</div>
                            <div className="data-value mono-num" style={{ fontSize: '18px', marginTop: '4px' }}>{data.metrics.p10_p90_coverage_percent}%</div>
                        </div>
                        <div style={{ backgroundColor: 'var(--bg-dark)', padding: '12px', border: '1px solid var(--border-subtle)' }}>
                            <div className="data-label">P25-P75 COVERAGE</div>
                            <div className="data-value mono-num" style={{ fontSize: '18px', marginTop: '4px' }}>{data.metrics.p25_p75_coverage_percent}%</div>
                        </div>
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '8px' }}>
                        OBSERVATIONS: {data.metrics.finish_comparable_observations} | DNF: {data.metrics.dnf} | UNKNOWN: {data.metrics.unknown}
                    </div>
                </div>
            </div>
        </div>
    );
}
