import { useState, useEffect } from 'react';
import type { CalibrationProfile } from '../types/backend';
import { getApiBaseUrl } from '../config';

export function useCalibration() {
    const [calibration, setCalibration] = useState<CalibrationProfile | null>(null);

    useEffect(() => {
        fetch(`${getApiBaseUrl()}/api/calibration`)
            .then(res => res.json())
            .then(data => setCalibration(data))
            .catch(e => console.error("Failed to load calibration", e));
    }, []);

    return calibration;
}
