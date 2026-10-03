import { useState, useEffect } from 'react';
import type { HistoricalOutcome } from '../types/backend';
import { getApiBaseUrl } from '../config';

export function useHistoricalOutcome(sessionKey: number, driverNumber: number, decisionLap: number, isRevealed: boolean) {
    const [outcome, setOutcome] = useState<HistoricalOutcome | null>(null);
    const [loading, setLoading] = useState<boolean>(false);

    useEffect(() => {
        if (!isRevealed) {
            setOutcome(null);
            return;
        }
        
        setLoading(true);
        fetch(`${getApiBaseUrl()}/api/outcomes/${sessionKey}/${driverNumber}/${decisionLap}`)
            .then(res => res.json())
            .then(data => {
                setOutcome(data as HistoricalOutcome);
            })
            .catch(e => console.error("Failed to load historical outcome", e))
            .finally(() => setLoading(false));
    }, [sessionKey, driverNumber, decisionLap, isRevealed]);

    return { outcome, loading };
}
