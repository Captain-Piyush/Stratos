import React, { useState } from 'react';
import { useRaceState } from '../hooks/useRaceState';
import { PaceEvolutionPlot } from '../components/PaceEvolutionPlot';
import { TyreDegradationPlot } from '../components/TyreDegradationPlot';
import { GapPlot } from '../components/GapPlot';
import { PitWindowPlot } from '../components/PitWindowPlot';
import { CounterfactualTable } from '../components/CounterfactualTable';
import { ActualOutcomePanel } from '../components/ActualOutcomePanel';
import { useCalibration } from '../hooks/useCalibration';
import { useHistoricalOutcome } from '../hooks/useHistoricalOutcome';
import { Play, Pause, StepForward, FastForward } from 'lucide-react';
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
        return <div style={{ padding: 16 }}>CONNECTING TO TELEMETRY STREAM...</div>;
    }

    if (connectionStatus === "DISCONNECTED") {
        return <div style={{ padding: 16, color: 'var(--accent-red)' }}>STREAM DISCONNECTED. RECONNECTING...</div>;
    }

    if (!state) {
        return <div style={{ padding: 16 }}>INITIALIZING RACE STATE...</div>;
    }

    const sortedDrivers = Object.values(state.driver_states).sort((a, b) => {
        if (a.position !== null && b.position !== null) return a.position - b.position;
        return a.driver_number - b.driver_number;
    });

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 40px)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 16px', backgroundColor: 'var(--bg-panel)', borderBottom: '1px solid var(--border-color)', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                    <div className="mono-num" style={{ fontWeight: 600, color: 'var(--text-bright)' }}>L{state.current_leader_lap} / {state.race_distance || '?'}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>SESSION: {state.session_key}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>STATUS: {state.global_status}</div>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {isStale && <span className="status-badge warning">DATA STALE</span>}
                    {state.weather && state.weather.status_stale && <span className="status-badge fault">WEATHER STALE</span>}
                    {connectionStatus === "REPLAY_MODE" ? (
                        <span className="status-badge warning">REPLAY</span>
                    ) : (
                        <span className="status-badge active">LIVE</span>
                    )}
                </div>
            </div>

            <div className="console-grid">
                {/* LEFT: RACE STATE */}
                <div className="col-left">
                    <div className="panel" style={{ flex: 1, overflowY: 'auto' }}>
                        <div className="panel-header">RACE STATE</div>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <div className="data-row" style={{ borderBottom: '1px solid var(--border-subtle)', padding: '0 8px 4px 8px' }}>
                                <span className="data-label" style={{ width: '20px' }}>P</span>
                                <span className="data-label" style={{ width: '24px' }}>NO</span>
                                <span className="data-label" style={{ flex: 1 }}>TYRE</span>
                                <span className="data-label" style={{ width: '40px', textAlign: 'right' }}>GAP</span>
                            </div>
                            {sortedDrivers.map(d => (
                                <div 
                                    key={d.driver_number} 
                                    className="data-row" 
                                    style={{ cursor: 'pointer', backgroundColor: selectedDriverId === d.driver_number ? 'var(--bg-panel-hover)' : 'transparent' }}
                                    onClick={() => setSelectedDriverId(d.driver_number)}
                                >
                                    <span className="data-value mono-num" style={{ width: '20px', color: 'var(--text-muted)' }}>{d.position || '-'}</span>
                                    <span className="data-value mono-num" style={{ width: '24px' }}>{d.driver_number}</span>
                                    <span className="data-value mono-num" style={{ flex: 1 }}>
                                        <span style={{ color: d.current_compound === 'SOFT' ? 'var(--accent-red)' : d.current_compound === 'MEDIUM' ? 'var(--accent-amber)' : d.current_compound === 'HARD' ? 'var(--text-bright)' : 'var(--accent-green)' }}>
                                            {d.current_compound ? d.current_compound[0] : '?'}
                                        </span>
                                        <span style={{ color: 'var(--text-muted)', marginLeft: 4 }}>{d.tyre_age}L</span>
                                    </span>
                                    <span className="data-value mono-num" style={{ width: '40px', textAlign: 'right' }}>
                                        {d.gap_to_leader !== null ? `+${d.gap_to_leader.toFixed(1)}` : ''}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* CENTER: STRATEGY ANALYSIS */}
                <div className="col-center">
                    <div className="panel" style={{ display: 'flex', gap: '8px', padding: '8px 16px' }}>
                        <button className={analyticsTab === 'PACE' ? 'primary' : ''} onClick={() => setAnalyticsTab('PACE')}>PACE EVOLUTION</button>
                        <button className={analyticsTab === 'TYRE' ? 'primary' : ''} onClick={() => setAnalyticsTab('TYRE')}>TYRE DEGRADATION</button>
                        <button className={analyticsTab === 'GAP' ? 'primary' : ''} onClick={() => setAnalyticsTab('GAP')}>TRAFFIC / GAPS</button>
                    </div>
                    
                    <div className="panel" style={{ flex: 1, minHeight: '300px', padding: 0 }}>
                        {activeDriver && analyticsTab === 'PACE' && <PaceEvolutionPlot driver={activeDriver} smoothingWindow={3} />}
                        {activeDriver && analyticsTab === 'TYRE' && <TyreDegradationPlot driver={activeDriver} calibration={calibration} />}
                        {activeDriver && analyticsTab === 'GAP' && <GapPlot state={state} driverId={activeDriver.driver_number} />}
                    </div>

                    <div className="panel">
                        <div className="panel-header">COUNTERFACTUAL ANALYSIS</div>
                        {activeDecision?.candidate_summary.length ? (
                            <CounterfactualTable candidates={activeDecision.candidate_summary} />
                        ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>AWAITING DECISION EVALUATION</span>
                        )}
                    </div>
                </div>

                {/* RIGHT: DECISION & TIMELINE */}
                <div className="col-right">
                    <div className="panel">
                        <div className="panel-header">STRATOS DECISION</div>
                        {activeDecision ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-bright)', borderLeft: '2px solid var(--accent-cyan)', paddingLeft: '8px' }}>
                                    {activeDecision.selected_strategy}
                                </div>
                                <div className="data-row" style={{ padding: '4px 0' }}>
                                    <span className="data-label">TRIGGER</span>
                                    <span className="data-value">{activeDecision.trigger}</span>
                                </div>
                                <div className="data-row" style={{ padding: '4px 0' }}>
                                    <span className="data-label">CONFIDENCE</span>
                                    <span className="data-value" style={{ color: activeDecision.decision_confidence === 'HIGH' ? 'var(--accent-green)' : 'var(--accent-amber)' }}>{activeDecision.decision_confidence}</span>
                                </div>
                                {activeDecision.probability_selected_beats_baseline !== null && (
                                    <div className="data-row" style={{ padding: '4px 0' }}>
                                        <span className="data-label">P(BEATS BASELINE)</span>
                                        <span className="data-value mono-num">{(activeDecision.probability_selected_beats_baseline * 100).toFixed(1)}%</span>
                                    </div>
                                )}
                                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', lineHeight: 1.5 }}>
                                    {activeDecision.explanation}
                                </div>
                            </div>
                        ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>AWAITING DISPATCH</span>
                        )}
                    </div>
                    
                    {isFutureRevealed && outcome && (
                        <ActualOutcomePanel outcome={outcome} modelStrategy={activeDecision!.selected_strategy} />
                    )}

                    <div className="panel" style={{ flex: 1, overflowY: 'auto' }}>
                        <div className="panel-header">EVENT TIMELINE</div>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            {decisions.map((dec) => (
                                <div 
                                    key={dec.decision_id} 
                                    className="data-row"
                                    onClick={() => setSelectedDecisionId(dec.decision_id)}
                                    style={{ cursor: 'pointer', borderLeft: selectedDecisionId === dec.decision_id ? '2px solid var(--accent-cyan)' : '2px solid transparent', backgroundColor: selectedDecisionId === dec.decision_id ? 'var(--bg-panel-hover)' : 'transparent' }}
                                >
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                        <span className="data-value mono-num" style={{ fontSize: '11px' }}>L{dec.decision_lap}</span>
                                        <span className="data-label" style={{ fontSize: '9px' }}>{dec.trigger}</span>
                                    </div>
                                    <span className="data-value" style={{ fontSize: '11px', textAlign: 'right' }}>{dec.selected_strategy}</span>
                                </div>
                            ))}
                            {decisions.length === 0 && (
                                <span style={{ color: 'var(--text-muted)', fontSize: '11px', padding: '8px' }}>WAITING FOR TRIGGERS...</span>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {connectionStatus === "REPLAY_MODE" && (
                <div style={{ display: 'flex', gap: '8px', padding: '8px 16px', backgroundColor: 'var(--bg-panel)', borderTop: '1px solid var(--border-color)', justifyContent: 'center' }}>
                    <button onClick={() => sendCommand("START_REPLAY")}><Play size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} /> PLAY</button>
                    <button onClick={() => sendCommand("PAUSE_REPLAY")}><Pause size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} /> PAUSE</button>
                    <button onClick={() => sendCommand("STEP_REPLAY")}><StepForward size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} /> STEP</button>
                    <button onClick={() => sendCommand("JUMP_TO_LAP")}><FastForward size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} /> JUMP</button>
                </div>
            )}
        </div>
    );
}
