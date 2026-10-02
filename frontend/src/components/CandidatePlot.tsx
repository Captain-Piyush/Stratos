import React from 'react';
import Plot from 'react-plotly.js';
import type { CandidateSummary } from '../types/backend';

interface Props {
    candidates: CandidateSummary[];
}

export const CandidatePlot: React.FC<Props> = ({ candidates }) => {
    // Sort by expected time (or median)
    const sorted = [...candidates].sort((a, b) => (a.expected_time || 0) - (b.expected_time || 0));

    const yVals = sorted.map(c => c.strategy_id);
    const xExpected = sorted.map(c => c.expected_time);
    const errorMinus = sorted.map(c => (c.expected_time && c.p10_time) ? c.expected_time - c.p10_time : 0);
    const errorPlus = sorted.map(c => (c.p90_time && c.expected_time) ? c.p90_time - c.expected_time : 0);
    const colors = sorted.map(c => c.is_selected ? '#4ade80' : '#38bdf8');

    return (
        <Plot
            data={[
                {
                    type: 'scatter',
                    mode: 'markers',
                    x: xExpected as any,
                    y: yVals,
                    error_x: {
                        type: 'data',
                        symmetric: false,
                        array: errorPlus,
                        arrayminus: errorMinus,
                        color: '#94a3b8',
                        thickness: 1.5,
                        width: 4
                    },
                    marker: {
                        color: colors,
                        size: 10
                    },
                    text: sorted.map(c => `Score: ${c.decision_score?.toFixed(1)}`),
                    hoverinfo: 'text'
                }
            ]}
            layout={{
                title: {
                    text: 'P10–P90 simulated range',
                    font: { color: '#94a3b8', size: 12 }
                },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#f8fafc' },
                margin: { t: 30, l: 150, r: 20, b: 40 },
                xaxis: {
                    title: 'Expected Time (s)',
                    gridcolor: '#334155',
                    zeroline: false
                },
                yaxis: {
                    gridcolor: '#334155',
                    zeroline: false
                },
                height: 300,
            }}
            config={{ responsive: true, displayModeBar: false }}
        />
    );
};
