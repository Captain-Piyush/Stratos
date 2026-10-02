import React, { useEffect, useState } from 'react';

export function Validation() {
    const [data, setData] = useState<any>(null);

    useEffect(() => {
        fetch('http://localhost:8000/api/validation')
            .then(res => res.json())
            .then(setData)
            .catch(console.error);
    }, []);

    if (!data) return <div style={{ padding: 24 }}>Loading validation data...</div>;

    return (
        <div style={{ maxWidth: 800, margin: '40px auto', padding: '0 24px', color: 'var(--text-main)' }}>
            <h1 style={{ fontSize: '2.5rem', color: 'var(--accent-blue)', marginBottom: 32 }}>Historical Validation</h1>
            
            <div className="panel" style={{ marginBottom: 24, backgroundColor: 'var(--bg-dark)', borderLeft: '4px solid var(--accent-yellow)' }}>
                <p style={{ margin: 0 }}>
                    <strong>IMPORTANT:</strong> Validation results are historical retrospective evaluations and not evidence of guaranteed real-world race performance.
                </p>
                <p style={{ margin: '8px 0 0 0' }}>
                    {data.interpretation}
                </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
                <div className="panel">
                    <h3 style={{ color: 'var(--accent-blue)', marginTop: 0 }}>Dataset</h3>
                    <ul style={{ paddingLeft: 20 }}>
                        <li>Total Races: {data.dataset.total_races}</li>
                        <li>Calibration Races: {data.dataset.calibration_races}</li>
                        <li>Holdout Races: {data.dataset.holdout_races}</li>
                    </ul>
                    <p style={{ color: 'var(--text-muted)' }}>Holdouts: {data.holdouts.join(', ')}</p>
                    <p style={{ color: 'var(--text-muted)' }}>Drivers: All drivers completing Lap 1 according to the deterministic holdout rule.</p>
                </div>
                
                <div className="panel">
                    <h3 style={{ color: 'var(--accent-blue)', marginTop: 0 }}>Final Validation Metrics</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                        <div>
                            <div style={{ fontSize: 24, color: 'var(--text-main)' }}>{data.metrics.corrected_mae}s</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Corrected MAE</div>
                        </div>
                        <div>
                            <div style={{ fontSize: 24, color: 'var(--text-main)' }}>{data.metrics.corrected_median_ae}s</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Corrected Median AE</div>
                        </div>
                        <div>
                            <div style={{ fontSize: 24, color: 'var(--text-main)' }}>{data.metrics.p10_p90_coverage_percent}%</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>P10-P90 Coverage</div>
                        </div>
                        <div>
                            <div style={{ fontSize: 24, color: 'var(--text-main)' }}>{data.metrics.p25_p75_coverage_percent}%</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>P25-P75 Coverage</div>
                        </div>
                    </div>
                    <div style={{ marginTop: 16, fontSize: 13, color: 'var(--text-muted)' }}>
                        Observations: {data.metrics.finish_comparable_observations} (DNF: {data.metrics.dnf}, Unknown: {data.metrics.unknown})
                    </div>
                </div>
            </div>
        </div>
    );
}
