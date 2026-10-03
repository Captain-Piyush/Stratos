import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import type { DriverState, CalibrationProfile } from '../types/backend';

interface Props {
    driver: DriverState;
    calibration: CalibrationProfile | null;
}

import { getCalibratedValue } from '../utils/calibration';

export const TyreDegradationPlot: React.FC<Props> = ({ driver, calibration }) => {
    // Show actual lap times vs tyre age, and a calibrated slope line
    const { lap_history = [], current_compound, tyre_age } = driver;
    
    // In a real scenario, we'd know which laps correspond to the current stint.
    // For now, assume the last `tyre_age` laps are on this tyre.
    const stintLaps = lap_history.slice(-Math.max(tyre_age, 1));
    const ages = stintLaps.map((_, i) => i + 1);

    const slope = getCalibratedValue(calibration?.degradation_slopes?.[current_compound], 0.05);
    const baseTime = 90.0; // Base lap times are dynamic based on session phase, using constant for visualization

    // Calibrated model line
    const calibratedLine = ages.map(age => baseTime + (age * slope));

    return (
        <Plot
            data={[
                {
                    type: 'scatter',
                    mode: 'markers',
                    x: ages,
                    y: stintLaps,
                    name: 'OBSERVED',
                    marker: { color: '#f8fafc', size: 6 }
                },
                {
                    type: 'scatter',
                    mode: 'lines',
                    x: ages,
                    y: calibratedLine,
                    name: 'CALIBRATED MODEL',
                    line: { color: '#facc15', dash: 'dash' }
                }
            ]}
            layout={{
                title: {
                    text: 'Tyre Degradation',
                    font: { color: '#94a3b8', size: 12 }
                },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#f8fafc' },
                margin: { t: 30, l: 40, r: 20, b: 40 },
                xaxis: {
                    title: 'Tyre Age (Laps)',
                    gridcolor: '#334155',
                    zeroline: false
                },
                yaxis: {
                    title: 'Lap Time (s)',
                    gridcolor: '#334155',
                    zeroline: false,
                },
                height: 250,
                legend: { orientation: 'h', y: -0.2 }
            }}
            config={{ responsive: true, displayModeBar: false }}
        />
    );
};
