import React from 'react';

export function Methodology() {
    return (
        <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="panel">
                <div className="panel-header">METHODOLOGY MODULE</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Theoretical framework of the STRATOS logic pipeline.
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">1. INGESTION & STATE RECONSTRUCTION</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                        STRATOS ingests raw telemetry, timing, and race control events via the OpenF1 API. This non-uniform event stream 
                        is logically reduced into a strict canonical <code>CanonicalRaceState</code>.
                    </div>
                </div>
                
                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">2. FEATURE GENERATION & CALIBRATION</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                        Using the CanonicalRaceState, the pipeline extracts mathematical features (lap history, compound distribution, traffic intervals).
                        Pace offset and tyre degradation parameters are empirically calibrated using linear/robust regression over the historical trace.
                    </div>
                </div>

                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">3. FORWARD SIMULATION & MONTE CARLO</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                        The strategy engine simulates the remainder of the race using a physics-informed transition model. 
                        Uncertainty (traffic, driver variance, pit loss) is injected probabilistically via a Monte Carlo wrapper.
                    </div>
                </div>
                
                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">4. DECISION ENGINE</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                        Candidates are scored against a defined Decision Objective (e.g., Minimize Total Race Time) and filtered by Constraints (e.g., Mandatory compound usage).
                        The system assigns a categorical <strong>Confidence</strong> metric based on statistical robustness against the baseline.
                    </div>
                </div>
            </div>
        </div>
    );
}
