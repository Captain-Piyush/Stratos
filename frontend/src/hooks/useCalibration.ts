import { useState, useEffect } from 'react';
import type { CalibrationProfile } from '../types/backend';

export function useCalibration() {
    const [calibration, setCalibration] = useState<CalibrationProfile | null>(null);

    useEffect(() => {
        fetch('http://localhost:8000/api/calibration')
            .then(res => res.json())
            .then(data => setCalibration(data))
            .catch(e => console.error("Failed to load calibration", e));
    }, []);

    return calibration;
}
