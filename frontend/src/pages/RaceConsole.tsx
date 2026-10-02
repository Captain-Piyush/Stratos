import React, { useState } from 'react';
import { useRaceState } from '../hooks/useRaceState';
import { CandidatePlot } from '../components/CandidatePlot';
import { PaceEvolutionPlot } from '../components/PaceEvolutionPlot';
import { TyreDegradationPlot } from '../components/TyreDegradationPlot';
import { GapPlot } from '../components/GapPlot';
import { PitWindowPlot } from '../components/PitWindowPlot';
import { CounterfactualTable } from '../components/CounterfactualTable';
import { ActualOutcomePanel } from '../components/ActualOutcomePanel';
import { useCalibration } from '../hooks/useCalibration';
import { useHistoricalOutcome } from '../hooks/useHistoricalOutcome';
import { Play, Pause, StepForward, FastForward, Activity } from 'lucide-react';
import '../index.css';

export function RaceConsole() {
    const { state, decisions, connectionStatus, isStale, sendCommand } = useRaceState();
    const calibration = useCalibration();
    const [selectedDecisionId, setSelectedDecisionId] = useState<string | null>(null);
    const [selectedDriverId, setSelectedDriverId] = useState<number | null>(null);
    const [analyticsTab, setAnalyticsTab] = useState<'PACE' | 'TYRE' | 'GAP'>('PACE');

    const activeDecision = selectedDecisionId 
        ? decisions.find(d => d.decision_id === selectedDecisionId)
        : decisions[decisions.length - 1];
        
    const activeDriver = selectedDriverId && state ? state.driver_states[selectedDriverId] : (state ? Object.values(state.driver_states)[0] : null);

    const isFutureRevealed = state && activeDecision && state.current_leader_lap > activeDecision.decision_lap;
    
    const { outcome } = useHistoricalOutcome(
        activeDecision?.session_key || 0,
        activeDecision?.driver_number || 0,
        activeDecision?.decision_lap || 0,
        !!isFutureRevealed
    );

    if (connectionStatus === "CONNECTING") {
        return <div style={{ padding: 24 }}>Connecting to STRATOS...</div>;
    }

    if (connectionStatus === "DISCONNECTED") {
        return <div style={{ padding: 24, color: 'var(--accent-red)' }}>DISCONNECTED. Attempting to reconnect...</div>;
    }

    if (!state) {
        return <div style={{ padding: 24 }}>Initializing state...</div>;
    }

    const sortedDrivers = Object.values(state.driver_states).sort((a, b) => {
        if (a.position !== null && b.position !== null) return a.position - b.position;
        return a.driver_number - b.driver_number;
    });

    return (
        <div className="console-container">
            <header className="console-header">
                <div className="race-info">
                    <h1>STRATOS Race Engineer</h1>
                    <span style={{ color: 'var(--text-muted)' }}>Session {state.session_key}</span>
                    <span>Lap {state.current_leader_lap} / {state.race_distance || '?'}</span>
                    <span>{state.global_status}</span>
                </div>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    {isStale && <span className="status-badge status-stale">DATA STALE</span>}
                    {state.weather && state.weather.status_stale && <span className="status-badge status-stale" style={{ backgroundColor: '#f87171' }}>PARTIAL DATA: WEATHER</span>}
                    {connectionStatus === "REPLAY_MODE" ? (
                        <span className="status-badge status-replay">REPLAY MODE</span>
                    ) : (
                        <span className="status-badge status-live">LIVE</span>
                    )}
                </div>
            </header>

            <main className="panel race-order">
                <h3 className="panel-title">Race Order</h3>
                {sortedDrivers.map(d => (
                    <div key={d.driver_number} className="driver-row">
                        <div style={{ display: 'flex', gap: '16px' }}>
                            <span className="driver-pos">{d.position || '-'}</span>
                            <span className="driver-num">{d.driver_number}</span>
                        </div>
                        <div style={{ display: 'flex', gap: '16px', color: 'var(--text-muted)' }}>
                            <span>{d.current_compound} {d.tyre_age}L</span>
                            <span style={{ width: 60, textAlign: 'right' }}>
                                {d.gap_to_leader !== null ? `+${d.gap_to_leader.toFixed(1)}s` : ''}
                            </span>
                        </div>
                    </div>
                ))}
            </main>

            <section className="strategy-card" style={{ gridColumn: '2 / 3' }}>
                <div style={{ display: 'flex', gap: '16px', marginBottom: '8px' }}>
                    <button onClick={() => setAnalyticsTab('PACE')} style={{ opacity: analyticsTab === 'PACE' ? 1 : 0.6 }}>Pace Evolution</button>
                    <button onClick={() => setAnalyticsTab('TYRE')} style={{ opacity: analyticsTab === 'TYRE' ? 1 : 0.6 }}>Tyre Degradation</button>
                    <button onClick={() => setAnalyticsTab('GAP')} style={{ opacity: analyticsTab === 'GAP' ? 1 : 0.6 }}>Traffic / Gaps</button>
                </div>
                
                {activeDriver && analyticsTab === 'PACE' && (
                    <div className="panel">
                        <PaceEvolutionPlot driver={activeDriver} smoothingWindow={3} />
                    </div>
                )}
                
                {activeDriver && analyticsTab === 'TYRE' && (
                    <div className="panel">
                        <TyreDegradationPlot driver={activeDriver} calibration={calibration} />
                    </div>
                )}
                
                {activeDriver && analyticsTab === 'GAP' && (
                    <div className="panel">
                        <GapPlot state={state} driverId={activeDriver.driver_number} />
                    </div>
                )}

                {activeDecision ? (
                    <>
                        <div className="decision-hero">
                            <div style={{ color: 'var(--accent-blue)', fontWeight: 600, marginBottom: 4 }}>
                                STRATOS DECISION
                            </div>
                            <h2>{activeDecision.selected_strategy}</h2>
                            <div className="decision-meta">
                                <span>Trigger: {activeDecision.trigger}</span>
                                <span>Objective: <strong style={{color: 'var(--text-main)'}}>{activeDecision.objective}</strong></span>
                                <span>Confidence: <strong style={{color: activeDecision.decision_confidence === 'HIGH' ? 'var(--accent-green)' : 'var(--accent-yellow)'}}>{activeDecision.decision_confidence}</strong></span>
                                {activeDecision.probability_selected_beats_baseline !== null && (
                                    <span>P(Beats Baseline): {(activeDecision.probability_selected_beats_baseline * 100).toFixed(0)}%</span>
                                )}
                            </div>
                            <div className="decision-meta" style={{ marginTop: 8 }}>
                                <span>Model: {activeDecision.calibration_version}</span>
                                <span>MC Seed: {activeDecision.monte_carlo_seed}</span>
                                <span>Timestamp: {activeDecision.timestamp}</span>
                            </div>
                        </div>

                        <div className="panel">
                            <h3 className="panel-title">WHY</h3>
                            <p>{activeDecision.explanation}</p>
                        </div>
                        
                        <div className="panel">
                            <h3 className="panel-title">CONSTRAINTS</h3>
                            <p style={{ color: 'var(--text-muted)' }}>
                                All candidates filtered against mandatory compound usage and maximum pit window parameters.
                            </p>
                        </div>
                        
                        {isFutureRevealed && outcome && (
                            <ActualOutcomePanel outcome={outcome} modelStrategy={activeDecision.selected_strategy} />
                        )}
                        
                        <div className="panel">
                            <h3 className="panel-title">Pit Window Timeline</h3>
                            <PitWindowPlot decision={activeDecision} />
                        </div>

                        <div className="panel">
                            <h3 className="panel-title">Counterfactual Strategy Analysis</h3>
                            {activeDecision.candidate_summary.length > 0 ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                                    <CounterfactualTable candidates={activeDecision.candidate_summary} />
                                    <CandidatePlot candidates={activeDecision.candidate_summary} />
                                </div>
                            ) : (
                                <p style={{ color: 'var(--text-muted)' }}>No candidates evaluated.</p>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                        <span style={{ color: 'var(--text-muted)' }}>No material decision events yet.</span>
                    </div>
                )}
            </section>

            <aside className="panel timeline">
                <h3 className="panel-title">Decision Timeline</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {decisions.map((dec, i) => (
                        <div 
                            key={i} 
                            className="timeline-event"
                            onClick={() => setSelectedDecisionId(dec.decision_id)}
                            style={{ opacity: selectedDecisionId === dec.decision_id ? 1 : 0.6 }}
                        >
                            <div style={{ fontWeight: 600 }}>Lap {dec.decision_lap}</div>
                            <div style={{ color: 'var(--accent-blue)' }}>{dec.selected_strategy}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{dec.trigger}</div>
                        </div>
                    ))}
                    {decisions.length === 0 && (
                        <span style={{ color: 'var(--text-muted)' }}>Waiting for triggers...</span>
                    )}
                </div>
            </aside>

            {connectionStatus === "REPLAY_MODE" && (
                <footer className="controls">
                    <button onClick={() => sendCommand("START_REPLAY")}><Play size={16} style={{ verticalAlign: 'middle', marginRight: 8 }} /> Play Replay</button>
                    <button onClick={() => sendCommand("PAUSE_REPLAY")}><Pause size={16} style={{ verticalAlign: 'middle', marginRight: 8 }} /> Pause</button>
                    <button onClick={() => sendCommand("STEP_REPLAY")}><StepForward size={16} style={{ verticalAlign: 'middle', marginRight: 8 }} /> Step</button>
                    <button onClick={() => sendCommand("JUMP_TO_LAP")}><FastForward size={16} style={{ verticalAlign: 'middle', marginRight: 8 }} /> Jump to Lap</button>
                </footer>
            )}
        </div>
    );
}
