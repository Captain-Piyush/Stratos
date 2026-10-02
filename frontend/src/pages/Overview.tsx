import React from 'react';
import { Link } from 'react-router-dom';

export function Overview() {
    return (
        <div style={{ maxWidth: 800, margin: '40px auto', padding: '0 24px', color: 'var(--text-main)' }}>
            <h1 style={{ fontSize: '3rem', color: 'var(--accent-blue)', marginBottom: 8 }}>STRATOS</h1>
            <h2 style={{ fontSize: '1.5rem', color: 'var(--text-muted)', fontWeight: 400, marginBottom: 40 }}>
                Real-time race strategy simulation and decision intelligence.
            </h2>

            <div className="panel" style={{ marginBottom: 32 }}>
                <h3 style={{ color: 'var(--accent-blue)' }}>Problem</h3>
                <p>
                    Motorsport strategy decisions are historically reliant on rigid pre-race heuristics and manually parameterized 
                    lap-time models. STRATOS solves this by replacing manual priors with empirical calibration and evaluating 
                    thousands of probabilistic branches via Monte Carlo simulation in real-time.
                </p>
            </div>

            <div className="panel" style={{ marginBottom: 32 }}>
                <h3 style={{ color: 'var(--accent-blue)' }}>System Architecture</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 16 }}>
                    <div style={{ padding: 12, backgroundColor: 'var(--bg-dark)', borderLeft: '4px solid var(--border-color)' }}>1. OpenF1 Ingestion</div>
                    <div style={{ padding: 12, backgroundColor: 'var(--bg-dark)', borderLeft: '4px solid var(--border-color)' }}>2. Race State Reconstruction</div>
                    <div style={{ padding: 12, backgroundColor: 'var(--bg-dark)', borderLeft: '4px solid var(--border-color)' }}>3. Feature Engineering</div>
                    <div style={{ padding: 12, backgroundColor: 'var(--bg-dark)', borderLeft: '4px solid var(--border-color)' }}>4. Calibrated Pace / Tyre Models</div>
                    <div style={{ padding: 12, backgroundColor: 'var(--bg-dark)', borderLeft: '4px solid var(--border-color)' }}>5. Monte Carlo Simulation</div>
                    <div style={{ padding: 12, backgroundColor: 'var(--bg-dark)', borderLeft: '4px solid var(--border-color)' }}>6. Strategy Evaluation</div>
                    <div style={{ padding: 12, backgroundColor: 'var(--bg-dark)', borderLeft: '4px solid var(--border-color)' }}>7. Explainable Recommendation</div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                <div className="panel">
                    <h3 style={{ color: 'var(--accent-blue)' }}>Historical Validation</h3>
                    <p>
                        STRATOS models are validated retrospectively on holdout datasets. View the empirical metrics of the frozen Phase 5C model.
                    </p>
                    <Link to="/validation" style={{ color: 'var(--accent-green)', textDecoration: 'none' }}>View Validation Results →</Link>
                </div>
                <div className="panel">
                    <h3 style={{ color: 'var(--accent-blue)' }}>Live / Replay Engine</h3>
                    <p>
                        The core engine is identical whether fed by historical MongoDB stubs or live websockets. Launch the console to experience it.
                    </p>
                    <Link to="/demo" style={{ color: 'var(--accent-green)', textDecoration: 'none' }}>Launch Console →</Link>
                </div>
            </div>
        </div>
    );
}
