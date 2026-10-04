import { useState, useEffect, useRef } from 'react';
import type { CanonicalRaceState, StrategyDecisionEvent } from '../types/backend';
import { getApiBaseUrl, getWsUrl } from '../config';

export type ConnectionStatus = "DISCONNECTED" | "CONNECTING" | "LIVE" | "BACKFILLING" | "RECONNECTING" | "ERROR" | "REPLAY" | "NO_ACTIVE_SESSION" | "LIVE_DATA_UNAVAILABLE" | "LIVE_TIMING" | "LIVE_DATA_STALE" | "PRE_RACE";

export function useRaceState() {
    const [state, setState] = useState<CanonicalRaceState | null>(null);
    const [decisions, setDecisions] = useState<StrategyDecisionEvent[]>([]);
    const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("CONNECTING");
    const [isStale, setIsStale] = useState<boolean>(false);
    
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Fetch initial state
        fetch(`${getApiBaseUrl()}/api/state`)
            .then(res => res.json())
            .then(data => {
                if (data.status === "REPLAY") {
                    setConnectionStatus("REPLAY");
                } else if (data.status === "LIVE") {
                    setConnectionStatus("LIVE");
                }
                if (data.state) {
                    setState(data.state as CanonicalRaceState);
                }
            })
            .catch(() => {
                setConnectionStatus("DISCONNECTED");
            });

        // Connect to WebSocket
        const connectWs = () => {
            const ws = new WebSocket(`${getWsUrl()}/api/decisions/stream`);
            
            ws.onopen = () => {
                if (connectionStatus === "DISCONNECTED" || connectionStatus === "RECONNECTING") {
                    setConnectionStatus("CONNECTING"); 
                }
            };
            
            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === "STATUS_UPDATE") {
                        const status = msg.status;
                        if (status === "BACKFILL_RUNNING") setConnectionStatus("BACKFILLING");
                        else if (status === "BACKFILL_COMPLETE" || status === "BACKFILL_FAILED") setConnectionStatus("LIVE");
                        else if (status === "NO_ACTIVE_SESSION") setConnectionStatus("NO_ACTIVE_SESSION");
                        else if (status === "LIVE_DATA_UNAVAILABLE") setConnectionStatus("LIVE_DATA_UNAVAILABLE");
                        else if (status === "LIVE_DATA_STALE") setConnectionStatus("LIVE_DATA_STALE");
                        else if (status === "LIVE_TIMING") setConnectionStatus("LIVE_TIMING");
                        else if (status === "LIVE") setConnectionStatus("LIVE");
                        else if (status === "CONNECTING") setConnectionStatus("CONNECTING");
                    } else if (msg.type === "STATE_UPDATE") {
                        const newState = msg.payload as CanonicalRaceState;
                        setState(newState);
                        
                        // Check stale globally
                        const someStale = Object.values(newState.driver_states).some(d => d.status_stale) || (newState.weather && newState.weather.status_stale);
                        setIsStale(someStale);
                        
                        setConnectionStatus(prev => {
                            if (prev === "CONNECTING" || prev === "DISCONNECTED") return "LIVE";
                            return prev;
                        });
                    } else if (msg.type === "DECISION_EVENT") {
                        setDecisions(prev => {
                            const newDec = msg.payload as StrategyDecisionEvent;
                            if (prev.some(d => d.decision_id === newDec.decision_id)) {
                                return prev;
                            }
                            return [...prev, newDec];
                        });
                    }
                } catch (e) {
                    console.error("Failed to parse WS message", e);
                }
            };
            
            ws.onclose = () => {
                setConnectionStatus("DISCONNECTED");
                setTimeout(connectWs, 2000); // Reconnect
            };
            
            wsRef.current = ws;
        };
        
        connectWs();
        
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, []);

    const sendCommand = (cmd: string) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(cmd);
        }
    };

    return { state, decisions, connectionStatus, isStale, sendCommand };
}
