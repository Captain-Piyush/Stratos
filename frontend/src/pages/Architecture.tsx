import React from 'react';

export function Architecture() {
    return (
        <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="panel">
                <div className="panel-header">TECHNICAL ARCHITECTURE</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    System boundaries, interfaces, and operational modes.
                </div>
            </div>
            
            <div className="panel">
                <div className="panel-header">DATA FLOW LOGIC</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1px', backgroundColor: 'var(--border-subtle)', border: '1px solid var(--border-subtle)', fontFamily: 'ui-monospace, monospace' }}>
                    <div style={{ backgroundColor: 'var(--bg-panel)', padding: '12px', fontSize: '10px' }}>
                        <div style={{ color: 'var(--accent-cyan)', marginBottom: '4px' }}>[EXTERNAL]</div>
                        OPENF1 API
                    </div>
                    <div style={{ backgroundColor: 'var(--bg-panel)', padding: '12px', fontSize: '10px' }}>
                        <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>[INGESTION]</div>
                        MONGO DB (RAW)
                    </div>
                    <div style={{ backgroundColor: 'var(--bg-panel)', padding: '12px', fontSize: '10px' }}>
                        <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>[ANALYTICS]</div>
                        CALIBRATION (PHASE 5B)
                    </div>
                    <div style={{ backgroundColor: 'var(--bg-panel)', padding: '12px', fontSize: '10px' }}>
                        <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>[SIMULATION]</div>
                        DECISION ENGINE
                    </div>
                    <div style={{ backgroundColor: 'var(--bg-panel)', padding: '12px', fontSize: '10px' }}>
                        <div style={{ color: 'var(--accent-green)', marginBottom: '4px' }}>[CLIENT]</div>
                        WEB CONSOLE
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">HISTORICAL REPLAY ADAPTER</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                        Powered by <code>ReplayStreamAdapter</code>. 
                        It chronologically queries MongoDB and strictly emits <code>CanonicalRaceState</code> blocks exactly as they would have occurred live,
                        with zero look-ahead bias (hindsight protected).
                    </div>
                </div>
                
                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">LIVE ADAPTER</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                        Powered by the <code>Live OpenF1 Adapter</code>. 
                        Maintains a live <code>CanonicalRaceState</code> in memory. Only finalized strategy decisions are asynchronously persisted to the database.
                    </div>
                </div>
            </div>
            
            <div className="panel">
                <div className="panel-header">CORE CONTRACTS</div>
                <div className="data-row" style={{ flexDirection: 'column', alignItems: 'flex-start', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                    <span className="data-label" style={{ color: 'var(--text-bright)' }}>CanonicalRaceState</span>
                    <span className="data-value" style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', fontWeight: 'normal' }}>The single source of truth for the circuit status at any instant. Sent via WebSocket.</span>
                </div>
                <div className="data-row" style={{ flexDirection: 'column', alignItems: 'flex-start', padding: '8px 0', borderBottom: 'none' }}>
                    <span className="data-label" style={{ color: 'var(--text-bright)' }}>StrategyDecisionEvent</span>
                    <span className="data-value" style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', fontWeight: 'normal' }}>The complete serialized evaluation of a decision point, including all candidates and Monte Carlo outcomes.</span>
                </div>
            </div>
        </div>
    );
}
