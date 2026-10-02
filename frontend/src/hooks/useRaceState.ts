import { useState, useEffect, useRef } from 'react';
import type { CanonicalRaceState, StrategyDecisionEvent } from '../types/backend';

export function useRaceState() {
    const [state, setState] = useState<CanonicalRaceState | null>(null);
    const [decisions, setDecisions] = useState<StrategyDecisionEvent[]>([]);
    const [connectionStatus, setConnectionStatus] = useState<"CONNECTING" | "LIVE_CONNECTED" | "REPLAY_MODE" | "DISCONNECTED">("CONNECTING");
    const [isStale, setIsStale] = useState<boolean>(false);
    
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Fetch initial state
        fetch('http://localhost:8000/api/state')
            .then(res => res.json())
            .then(data => {
                if (data.status === "REPLAY") {
                    setConnectionStatus("REPLAY_MODE");
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
            const ws = new WebSocket('ws://localhost:8000/api/decisions/stream');
            
            ws.onopen = () => {
                if (connectionStatus === "DISCONNECTED") {
                    setConnectionStatus("CONNECTING"); // Will be updated by state payload
                }
            };
            
            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === "STATE_UPDATE") {
                        const newState = msg.payload as CanonicalRaceState;
                        setState(newState);
                        
                        // Check stale globally
                        const someStale = Object.values(newState.driver_states).some(d => d.status_stale) || (newState.weather && newState.weather.status_stale);
                        setIsStale(someStale);
                        
                        // Default to replay mode for demo, but backend can signal LIVE
                        if (connectionStatus !== "REPLAY_MODE") {
                            setConnectionStatus("REPLAY_MODE"); 
                        }
                    } else if (msg.type === "DECISION_EVENT") {
                        setDecisions(prev => [...prev, msg.payload as StrategyDecisionEvent]);
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
