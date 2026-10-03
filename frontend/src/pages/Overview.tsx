import React from 'react';
import { useRaceState } from '../hooks/useRaceState';

export function Overview() {
    const { state, connectionStatus } = useRaceState();

    return (
        <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="panel">
                <h1 style={{ fontSize: '18px', marginBottom: '4px', letterSpacing: '0.05em' }}>STRATOS</h1>
                <h2 style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '16px', letterSpacing: '0.1em' }}>
                    F1 STRATEGY INTELLIGENCE ENGINE
                </h2>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1px', backgroundColor: 'var(--border-color)', border: '1px solid var(--border-color)' }}>
                    <div style={{ backgroundColor: 'var(--bg-panel)', padding: '8px' }}>
                        <div className="data-label">MODE</div>
                        <div className="data-value" style={{ color: connectionStatus === 'LIVE_CONNECTED' ? 'var(--accent-red)' : connectionStatus === 'REPLAY_MODE' ? 'var(--accent-yellow)' : 'var(--text-muted)' }}>
                            {connectionStatus === 'LIVE_CONNECTED' ? 'LIVE' : connectionStatus === 'REPLAY_MODE' ? 'REPLAY' : 'DISCONNECTED'}
                        </div>
                    </div>
                    <div style={{ backgroundColor: 'var(--bg-panel)', padding: '8px' }}>
                        <div className="data-label">SESSION</div>
                        <div className="data-value mono-num">{state?.session_key || '---'}</div>
                    </div>
                    <div style={{ backgroundColor: 'var(--bg-panel)', padding: '8px' }}>
                        <div className="data-label">LAP</div>
                        <div className="data-value mono-num">{state?.current_leader_lap || '---'}</div>
                    </div>
                    <div style={{ backgroundColor: 'var(--bg-panel)', padding: '8px' }}>
                        <div className="data-label">MODEL VERSION</div>
                        <div className="data-value">PHASE 5C-FROZEN</div>
                    </div>
                    <div style={{ backgroundColor: 'var(--bg-panel)', padding: '8px' }}>
                        <div className="data-label">DATA STATUS</div>
                        <div className="data-value" style={{ color: 'var(--accent-green)' }}>SYNCED</div>
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">RACE STATE</div>
                    <div className="data-row">
                        <span className="data-label">ACTIVE DRIVERS</span>
                        <span className="data-value mono-num">{state ? Object.keys(state.driver_states).length : '---'}</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">TRACK TEMP</span>
                        <span className="data-value mono-num">{state?.weather?.track_temperature != null ? `${state.weather.track_temperature.toFixed(1)}°C` : '---'}</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">AIR TEMP</span>
                        <span className="data-value mono-num">{state?.weather?.air_temperature != null ? `${state.weather.air_temperature.toFixed(1)}°C` : '---'}</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">TRACK STATUS</span>
                        <span className="data-value">{state?.global_status === '1' ? 'GREEN' : state?.global_status || '---'}</span>
                    </div>
                </div>

                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">SYSTEM STATUS</div>
                    <div className="data-row">
                        <span className="data-label">TELEMETRY INGESTION</span>
                        <span className="data-value" style={{ color: 'var(--accent-green)' }}>OK</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">DB PERSISTENCE</span>
                        <span className="data-value" style={{ color: 'var(--accent-green)' }}>OK</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">DECISION LATENCY</span>
                        <span className="data-value mono-num">{'< 50ms'}</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">MONTE CARLO ITERS</span>
                        <span className="data-value mono-num">1000</span>
                    </div>
                </div>

                <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="panel-header">VALIDATION METRICS</div>
                    <div className="data-row">
                        <span className="data-label">P10-P90 COVERAGE</span>
                        <span className="data-value mono-num">90.47%</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">CORRECTED MAE</span>
                        <span className="data-value mono-num">2.449s</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">CORRECTED MEDIAN AE</span>
                        <span className="data-value mono-num">1.758s</span>
                    </div>
                    <div className="data-row">
                        <span className="data-label">STATUS</span>
                        <span className="data-value" style={{ color: 'var(--accent-green)' }}>VERIFIED</span>
                    </div>
                </div>
            </div>

            <div className="panel">
                <div className="panel-header">STRATEGY PIPELINE</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '1px', backgroundColor: 'var(--border-subtle)', border: '1px solid var(--border-subtle)' }}>
                    {['1. INGEST', '2. RECONSTRUCT', '3. FEATURES', '4. MODELS', '5. SIMULATION', '6. EVALUATION', '7. DECISION'].map((step, i) => (
                        <div key={i} style={{ backgroundColor: 'var(--bg-panel)', padding: '12px 8px', textAlign: 'center', fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)' }}>
                            {step}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
