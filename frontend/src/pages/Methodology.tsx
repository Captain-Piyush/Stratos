import React from 'react';

export function Methodology() {
    return (
        <div style={{ maxWidth: 800, margin: '40px auto', padding: '0 24px', color: 'var(--text-main)' }}>
            <h1 style={{ fontSize: '2.5rem', color: 'var(--accent-blue)', marginBottom: 32 }}>Methodology</h1>
            
            <div className="panel" style={{ marginBottom: 24 }}>
                <h3 style={{ color: 'var(--accent-blue)' }}>1. Data Ingestion & State Reconstruction</h3>
                <p>
                    STRATOS ingests raw telemetry, timing, and race control events via the OpenF1 API. This non-uniform event stream 
                    is logically reduced into a strict <code>CanonicalRaceState</code>.
                </p>
            </div>
            
            <div className="panel" style={{ marginBottom: 24 }}>
                <h3 style={{ color: 'var(--accent-blue)' }}>2. Feature Generation & Model Calibration</h3>
                <p>
                    Using the CanonicalRaceState, the pipeline extracts mathematical features (lap history, compound distribution, traffic intervals).
                    Pace offset and tyre degradation parameters are empirically calibrated using linear/robust regression over the historical trace. 
                    This ensures predictions are grounded in the specific circuit's reality.
                </p>
            </div>
            
            <div className="panel" style={{ marginBottom: 24 }}>
                <h3 style={{ color: 'var(--accent-blue)' }}>3. Forward Simulation & Monte Carlo</h3>
                <p>
                    The strategy engine simulates the remainder of the race using a physics-informed transition model. 
                    Uncertainty (traffic, driver variance, pit loss) is injected probabilistically via a Monte Carlo wrapper, generating an expected outcome distribution.
                </p>
            </div>
            
            <div className="panel" style={{ marginBottom: 24 }}>
                <h3 style={{ color: 'var(--accent-blue)' }}>4. Decision Engine</h3>
                <p>
                    Candidates are scored against a defined Decision Objective (e.g., Minimize Total Race Time) and filtered by Constraints (e.g., Mandatory compound usage).
                    The system assigns a categorical <strong>Decision Confidence</strong> metric based on the statistical robustness of the proposed strategy against the baseline.
                </p>
            </div>
        </div>
    );
}
