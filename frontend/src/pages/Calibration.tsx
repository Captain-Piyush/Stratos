import React from 'react';
import { useCalibration } from '../hooks/useCalibration';

export function Calibration() {
    const calibration = useCalibration();

    if (!calibration) return <div style={{ padding: 24 }}>Loading calibration profile...</div>;

    return (
        <div style={{ maxWidth: 800, margin: '40px auto', padding: '0 24px', color: 'var(--text-main)' }}>
            <h1 style={{ fontSize: '2.5rem', color: 'var(--accent-blue)', marginBottom: 32 }}>Calibration Transparency</h1>
            
            <p style={{ marginBottom: 32 }}>
                STRATOS uses a frozen Phase 5B calibration profile. The parameters below drive the forward simulation engine.
            </p>

            <div className="panel" style={{ marginBottom: 24 }}>
                <h3 style={{ color: 'var(--accent-blue)', marginTop: 0 }}>Tyre Degradation (s/lap)</h3>
                <span className="status-badge" style={{ backgroundColor: 'var(--accent-green)', color: '#000', marginBottom: 16, display: 'inline-block' }}>SOURCE: CALIBRATED</span>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>SOFT</div>
                        <div style={{ fontSize: 20 }}>{calibration.degradation_slopes?.SOFT?.toFixed(4) || "0.1006"} s/lap</div>
                    </div>
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>MEDIUM</div>
                        <div style={{ fontSize: 20 }}>{calibration.degradation_slopes?.MEDIUM?.toFixed(4) || "0.0452"} s/lap</div>
                    </div>
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>HARD</div>
                        <div style={{ fontSize: 20 }}>{calibration.degradation_slopes?.HARD?.toFixed(4) || "0.0462"} s/lap</div>
                    </div>
                </div>
            </div>

            <div className="panel" style={{ marginBottom: 24 }}>
                <h3 style={{ color: 'var(--accent-blue)', marginTop: 0 }}>Compound Deltas (vs Soft)</h3>
                <span className="status-badge" style={{ backgroundColor: 'var(--accent-green)', color: '#000', marginBottom: 16, display: 'inline-block' }}>SOURCE: CALIBRATED</span>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>MEDIUM Delta</div>
                        <div style={{ fontSize: 20 }}>0.7194 s</div>
                    </div>
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>HARD Delta</div>
                        <div style={{ fontSize: 20 }}>0.5695 s</div>
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                <div className="panel">
                    <h3 style={{ color: 'var(--accent-blue)', marginTop: 0 }}>Global Pit-Loss</h3>
                    <span className="status-badge" style={{ backgroundColor: 'var(--accent-green)', color: '#000', marginBottom: 16, display: 'inline-block' }}>SOURCE: CALIBRATED</span>
                    <div style={{ fontSize: 24 }}>{calibration.pit_loss?.toFixed(2) || "23.75"} s</div>
                </div>
                
                <div className="panel" style={{ borderLeft: '4px solid var(--accent-red)' }}>
                    <h3 style={{ color: 'var(--accent-blue)', marginTop: 0 }}>Fuel Burn</h3>
                    <span className="status-badge" style={{ backgroundColor: 'var(--accent-red)', color: '#fff', marginBottom: 16, display: 'inline-block' }}>SOURCE: PRIOR</span>
                    <div style={{ fontSize: 24 }}>{(calibration as any).fuel_effect?.toFixed(4) || "0.0600"} s/lap</div>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                        Fuel burn was not empirically identified from the available data and therefore remains a prior.
                    </p>
                </div>
            </div>
        </div>
    );
}
