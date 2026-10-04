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
import { Play, Pause, StepForward, FastForward, Activity, MonitorPlay } from 'lucide-react';
import '../index.css';

const getCircuitName = (state: any) => {
    if (!state) return 'UNKNOWN CIRCUIT';
    return state.circuit_name || state.meeting_name || `SESSION ${state.session_key}`;
};

export function RaceConsole() {
    const { state, decisions, connectionStatus, isStale, sendCommand } = useRaceState();
    const calibration = useCalibration();
    const [selectedDecisionId, setSelectedDecisionId] = useState<string | null>(null);
    const [selectedDriverId, setSelectedDriverId] = useState<number | null>(null);
    const [analyticsTab, setAnalyticsTab] = useState<'PACE' | 'TYRE' | 'GAP'>('PACE');
    const [activeMode, setActiveMode] = useState<'LIVE' | 'REPLAY'>('REPLAY');

    const handleModeChange = (mode: 'LIVE' | 'REPLAY') => {
        setActiveMode(mode);
        if (mode === 'LIVE') {
            sendCommand('START_LIVE');
        } else {
            sendCommand('START_REPLAY');
        }
    };

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

    const sortedDrivers = state ? Object.values(state.driver_states).sort((a, b) => {
        if (a.position !== null && b.position !== null) return a.position - b.position;
        return a.driver_number - b.driver_number;
    }) : [];

    // Header Status string
    let headerStatusText = "UNKNOWN";
    if (activeMode === 'REPLAY') {
        headerStatusText = state && state.global_status ? state.global_status.replace('_', ' ') : "REPLAY MODE";
    } else {
        if (connectionStatus === 'CONNECTING') headerStatusText = "CONNECTING...";
        else if (connectionStatus === 'DISCONNECTED') headerStatusText = "DISCONNECTED";
        else if (connectionStatus === 'RECONNECTING') headerStatusText = "RECONNECTING...";
        else if (connectionStatus === 'ERROR') headerStatusText = "STREAM ERROR";
        else if (connectionStatus === 'NO_ACTIVE_SESSION') headerStatusText = "NO LIVE SESSION";
        else if (connectionStatus === 'LIVE_DATA_UNAVAILABLE') headerStatusText = "LIVE DATA UNAVAILABLE";
        else if (connectionStatus === 'BACKFILLING') headerStatusText = "BACKFILLING...";
        else if (connectionStatus === 'LIVE') headerStatusText = state && state.global_status ? state.global_status.replace('_', ' ') : "SIGNALR CONNECTED";
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 40px)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 16px', backgroundColor: 'var(--bg-panel)', borderBottom: '1px solid var(--border-color)', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', fontWeight: 600 }}>
                        {activeMode === 'LIVE' && connectionStatus === 'LIVE' && <span style={{ color: 'var(--accent-green)' }}>●</span>}
                        {activeMode === 'LIVE' && connectionStatus !== 'LIVE' && <span style={{ color: 'var(--accent-amber)' }}>●</span>}
                        <span style={{ color: activeMode === 'LIVE' ? 'var(--accent-cyan)' : 'var(--text-bright)' }}>{activeMode}</span>
                    </div>
                    {state ? (
                        <>
                            <div style={{ fontWeight: 600, color: 'var(--text-bright)' }}>{getCircuitName(state)}</div>
                            <div className="mono-num" style={{ fontWeight: 600, color: 'var(--text-bright)' }}>
                                L{state.current_leader_lap} / {state.race_distance || '?'}
                            </div>
                        </>
                    ) : (
                        <div style={{ fontWeight: 600, color: 'var(--text-muted)' }}>AWAITING SESSION DATA</div>
                    )}
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{headerStatusText}</div>
                </div>
                
                <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                    {state?.gps_available === true ? (
                        <span className="status-badge active" style={{ backgroundColor: 'transparent', border: '1px solid var(--accent-cyan)' }}>TRACK POSITION AVAILABLE</span>
                    ) : state ? (
                        <span className="status-badge fault" style={{ backgroundColor: 'transparent', border: '1px solid var(--accent-red)' }}>TRACK POSITION UNAVAILABLE</span>
                    ) : null}
                    {isStale && <span className="status-badge warning">DATA STALE</span>}
                    {state?.weather?.status_stale && <span className="status-badge fault">WEATHER STALE</span>}
                    
                    <div style={{ display: 'flex', backgroundColor: 'var(--bg-color)', borderRadius: '4px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
                        <button 
                            style={{ 
                                padding: '4px 12px', 
                                border: 'none',
                                cursor: 'pointer',
                                fontSize: '11px',
                                fontWeight: 600,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                backgroundColor: activeMode === 'LIVE' ? 'var(--accent-cyan)' : 'transparent',
                                color: activeMode === 'LIVE' ? 'var(--bg-color)' : 'var(--text-muted)'
                            }}
                            onClick={() => handleModeChange('LIVE')}
                        >
                            <Activity size={12} /> LIVE
                        </button>
                        <button 
                            style={{ 
                                padding: '4px 12px', 
                                border: 'none',
                                cursor: 'pointer',
                                fontSize: '11px',
                                fontWeight: 600,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                backgroundColor: activeMode === 'REPLAY' ? 'var(--text-bright)' : 'transparent',
                                color: activeMode === 'REPLAY' ? 'var(--bg-color)' : 'var(--text-muted)'
                            }}
                            onClick={() => handleModeChange('REPLAY')}
                        >
                            <MonitorPlay size={12} /> REPLAY
                        </button>
                    </div>
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
                            {sortedDrivers.length === 0 && (
                                <span style={{ color: 'var(--text-muted)', fontSize: '11px', padding: '8px' }}>AWAITING LIVE RACE STATE</span>
                            )}
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
                        {activeDriver && analyticsTab === 'GAP' && state && <GapPlot state={state} driverId={activeDriver.driver_number} />}
                        {!activeDriver && (
                            <div style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '11px' }}>AWAITING LIVE RACE STATE</div>
                        )}
                    </div>

                    <div className="panel">
                        <div className="panel-header">COUNTERFACTUAL ANALYSIS</div>
                        {state?.current_leader_lap === 0 ? (
                            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>WAITING FOR LIVE RACE STATE</span>
                        ) : activeDecision?.candidate_summary.length ? (
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
                        {state?.current_leader_lap === 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-bright)' }}>
                                    PRE-RACE
                                </div>
                                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                                    WAITING FOR LIVE RACE STATE
                                </div>
                                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', lineHeight: 1.5 }}>
                                    Strategy evaluation will begin when live race telemetry is available.
                                </div>
                            </div>
                        ) : activeDecision ? (
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
                            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>AWAITING LIVE RACE STATE</span>
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

            {activeMode === 'REPLAY' && (
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
