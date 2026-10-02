import React from 'react';
import Plot from 'react-plotly.js';
import type { CanonicalRaceState } from '../types/backend';

interface Props {
    state: CanonicalRaceState;
    driverId: number;
}

export const GapPlot: React.FC<Props> = ({ state, driverId }) => {
    // We visualize gaps to cars immediately ahead and behind
    // Find the driver's position
    const sortedDrivers = Object.values(state.driver_states).sort((a, b) => {
        if (a.position !== null && b.position !== null) return a.position - b.position;
        return a.driver_number - b.driver_number;
    });

    const driverIndex = sortedDrivers.findIndex(d => d.driver_number === driverId);
    
    if (driverIndex === -1) return null;

    const driver = sortedDrivers[driverIndex];
    const ahead = driverIndex > 0 ? sortedDrivers[driverIndex - 1] : null;
    const behind = driverIndex < sortedDrivers.length - 1 ? sortedDrivers[driverIndex + 1] : null;

    const data = [
        { name: ahead ? `P${ahead.position} (Ahead)` : 'Leader', val: ahead ? (ahead.interval_to_ahead || 0) : 0, color: '#f87171' },
        { name: `P${driver.position} (You)`, val: 0, color: '#38bdf8' },
        { name: behind ? `P${behind.position} (Behind)` : 'Tail', val: behind ? -(behind.interval_to_ahead || 0) : 0, color: '#facc15' }
    ];

    return (
        <Plot
            data={[
                {
                    type: 'bar',
                    x: data.map(d => d.val),
                    y: data.map(d => d.name),
                    orientation: 'h',
                    marker: { color: data.map(d => d.color) }
                }
            ]}
            layout={{
                title: {
                    text: 'Traffic Gaps',
                    font: { color: '#94a3b8', size: 12 }
                },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#f8fafc' },
                margin: { t: 30, l: 100, r: 20, b: 40 },
                xaxis: {
                    title: 'Relative Interval (s)',
                    gridcolor: '#334155',
                    zeroline: true,
                    zerolinecolor: '#475569'
                },
                yaxis: {
                    gridcolor: '#334155'
                },
                height: 250,
            }}
            config={{ responsive: true, displayModeBar: false }}
        />
    );
};
