import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import type { DriverState } from '../types/backend';

interface Props {
    driver: DriverState;
    smoothingWindow: number; // 1 = raw, 3 = 3-lap, etc.
}

export const PaceEvolutionPlot: React.FC<Props> = ({ driver, smoothingWindow }) => {
    // We expect driver.lap_history to contain the raw lap times
    // and driver.current_lap to know where we are.
    // If not provided from backend, we will just have an empty or mock representation.
    const { lap_history = [] } = driver;

    const xLaps = lap_history.map((_, i) => i + 1);
    
    // Simple rolling average
    const smoothedPace = useMemo(() => {
        if (smoothingWindow <= 1) return lap_history;
        return lap_history.map((_, idx) => {
            if (idx < smoothingWindow - 1) return null;
            const slice = lap_history.slice(idx - smoothingWindow + 1, idx + 1);
            const sum = slice.reduce((a, b) => a + b, 0);
            return sum / smoothingWindow;
        });
    }, [lap_history, smoothingWindow]);

    return (
        <Plot
            data={[
                {
                    type: 'scatter',
                    mode: 'lines+markers',
                    x: xLaps,
                    y: smoothedPace as any,
                    line: { color: '#38bdf8' },
                    marker: { size: 4 },
                    name: `Pace (${smoothingWindow}L Avg)`
                }
            ]}
            layout={{
                title: {
                    text: 'Pace Evolution',
                    font: { color: '#94a3b8', size: 12 }
                },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#f8fafc' },
                margin: { t: 30, l: 40, r: 20, b: 40 },
                xaxis: {
                    title: 'Lap',
                    gridcolor: '#334155',
                    zeroline: false
                },
                yaxis: {
                    title: 'Lap Time (s)',
                    gridcolor: '#334155',
                    zeroline: false,
                    autorange: 'reversed' // Lower lap time is better
                },
                height: 250,
            }}
            config={{ responsive: true, displayModeBar: false }}
        />
    );
};
