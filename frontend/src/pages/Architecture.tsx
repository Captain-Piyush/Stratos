import React from 'react';

export function Architecture() {
    return (
        <div style={{ maxWidth: 800, margin: '40px auto', padding: '0 24px', color: 'var(--text-main)' }}>
            <h1 style={{ fontSize: '2.5rem', color: 'var(--accent-blue)', marginBottom: 32 }}>Technical Architecture</h1>
            
            <div className="panel" style={{ marginBottom: 32 }}>
                <h3 style={{ color: 'var(--accent-blue)', marginTop: 0 }}>Data Flow</h3>
                
                <div style={{ padding: 24, backgroundColor: 'var(--bg-dark)', borderRadius: 8, fontFamily: 'monospace', fontSize: 14 }}>
                    <div style={{ color: 'var(--accent-green)' }}>OpenF1 API</div>
                    <div>&nbsp;&nbsp;↓ (Ingestion)</div>
                    <div style={{ color: 'var(--accent-blue)' }}>MongoDB (Raw Events)</div>
                    <div>&nbsp;&nbsp;↓ (Feature Engine)</div>
                    <div style={{ color: 'var(--accent-yellow)' }}>Calibrated Model (Phase 5B)</div>
                    <div>&nbsp;&nbsp;↓ (Simulation Engine + Monte Carlo)</div>
                    <div style={{ color: 'var(--text-main)' }}>Decision Engine (Phase 3C)</div>
                    <div>&nbsp;&nbsp;↓ (FastAPI WebSocket)</div>
                    <div style={{ color: 'var(--accent-green)' }}>React / Plotly Console</div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                <div className="panel">
                    <h3 style={{ color: 'var(--accent-blue)', marginTop: 0 }}>Historical Replay</h3>
                    <p>
                        Powered by <code>ReplayStreamAdapter</code>. 
                        It chronologically queries MongoDB and strictly emits <code>CanonicalRaceState</code> blocks exactly as they would have occurred live,
                        with zero look-ahead bias (hindsight protected).
                    </p>
                </div>
                
                <div className="panel">
                    <h3 style={{ color: 'var(--accent-blue)', marginTop: 0 }}>Live Mode</h3>
                    <p>
                        Powered by the <code>Live OpenF1 Adapter</code>. 
                        Maintains a live `CanonicalRaceState`. Currently <code>LIVE_ADAPTER_IMPLEMENTED</code> but <code>CREDENTIALS_NOT_AVAILABLE</code> for real-time race sessions outside of the testing lab.
                    </p>
                </div>
            </div>

            <div className="panel" style={{ marginTop: 24 }}>
                <h3 style={{ color: 'var(--accent-blue)', marginTop: 0 }}>Core Contracts</h3>
                <ul style={{ lineHeight: 1.6 }}>
                    <li><strong>CanonicalRaceState:</strong> The single source of truth for the circuit status at any instant.</li>
                    <li><strong>StrategyDecisionEvent:</strong> The complete serialized evaluation of a decision point, including all candidates and the Monte Carlo outcome distributions.</li>
                </ul>
            </div>
        </div>
    );
}
