import React, { useMemo } from 'react';
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
  BarChart,
  Bar,
  Cell
} from 'recharts';

const COLORS = ["#60a5fa", "#34d399", "#f59e0b", "#f87171", "#a78bfa"];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        backgroundColor: '#1f2937',
        border: '1px solid #374151',
        padding: '10px',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
        fontSize: '12px',
        color: '#fff'
      }}>
        <p style={{ fontWeight: 'bold', marginBottom: '8px' }}>{label} nm</p>
        {payload.map((entry, index) => (
          <p key={index} style={{ color: entry.color, margin: '4px 0' }}>
            {entry.name}: <span style={{ fontWeight: 'bold' }}>{entry.value.toFixed(4)}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const SpectrumChart = ({ userSpectrum = [], meanClassSpectrum = [], predictedClass = "Unknown", compositionBreakdown = [] }) => {
  // Merge datasets by wavelength
  const chartData = useMemo(() => {
    const map = new Map();
    userSpectrum.forEach(s => {
      map.set(s.wavelength, { wavelength: s.wavelength, user: s.reflectance });
    });
    meanClassSpectrum.forEach(s => {
      const existing = map.get(s.wavelength) || { wavelength: s.wavelength };
      map.set(s.wavelength, { ...existing, mean: s.reflectance });
    });
    return Array.from(map.values()).sort((a, b) => a.wavelength - b.wavelength);
  }, [userSpectrum, meanClassSpectrum]);

  // Format composition for stacked bar
  // Input: [{mineral, percent}, ...]
  // Output: [{ name: 'breakdown', mineral1: percent1, ... }]
  const barData = useMemo(() => {
    const dataRow = { name: 'Composition' };
    compositionBreakdown.forEach(c => {
      dataRow[c.mineral] = c.percent;
    });
    return [dataRow];
  }, [compositionBreakdown]);

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 1. Spectrum Chart */}
      <div style={{ background: '#111827', padding: '20px', borderRadius: '12px', border: '1px solid #1f2937' }}>
        <h3 style={{ color: '#fff', fontSize: '14px', marginBottom: '16px', fontWeight: '600' }}>
          Spectral Reflectance Comparison
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" vertical={false} />
            <XAxis 
              dataKey="wavelength" 
              domain={[450, 2200]} 
              type="number"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              axisLine={{ stroke: '#374151' }}
              label={{ value: 'Wavelength (nm)', position: 'insideBottom', offset: -5, fill: '#9ca3af', fontSize: 11 }}
            />
            <YAxis 
              domain={[0.5, 2.0]}
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              axisLine={{ stroke: '#374151' }}
              label={{ value: 'Reflectance (at 550nm=1)', angle: -90, position: 'insideLeft', fill: '#9ca3af', fontSize: 11 }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend verticalAlign="top" align="right" iconType="circle" wrapperStyle={{ paddingBottom: '20px', fontSize: '12px' }} />
            
            {/* Silicate Absorption Bands */}
            <ReferenceArea x1={900} x2={1000} fill="#ff000015" label={{ value: 'silicate band 1', position: 'top', fill: '#ef4444', fontSize: 10, offset: 10 }} />
            <ReferenceArea x1={1800} x2={2000} fill="#ff000015" label={{ value: 'silicate band 2', position: 'top', fill: '#ef4444', fontSize: 10, offset: 10 }} />

            <Line 
              type="monotone" 
              dataKey="user" 
              name="Your input" 
              stroke="#60a5fa" 
              strokeWidth={2} 
              dot={false}
              activeDot={{ r: 4, stroke: '#93c5fd', strokeWidth: 2 }}
            />
            <Line 
              type="monotone" 
              dataKey="mean" 
              name={`Mean ${predictedClass}-type`} 
              stroke="#f59e0b" 
              strokeWidth={1.5} 
              strokeDasharray="5 5" 
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* 2. Composition Breakdown Bar */}
      <div style={{ background: '#111827', padding: '16px', borderRadius: '12px', border: '1px solid #1f2937' }}>
        <h3 style={{ color: '#fff', fontSize: '14px', marginBottom: '12px', fontWeight: '600' }}>
            Mineralogical Composition Estimate
        </h3>
        <ResponsiveContainer width="100%" height={80}>
          <BarChart layout="vertical" data={barData} margin={{ top: 0, right: 30, left: 0, bottom: 0 }}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="name" hide />
            <Tooltip 
              cursor={{ fill: 'transparent' }} 
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', padding: '8px', fontSize: '12px', color: '#fff' }}
              itemStyle={{ color: '#fff' }}
            />
            <Legend verticalAlign="bottom" height={36} iconSize={10} wrapperStyle={{ fontSize: '11px', color: '#9ca3af', paddingTop: '10px' }} />
            
            {compositionBreakdown.map((item, index) => (
              <Bar 
                key={item.mineral} 
                dataKey={item.mineral} 
                stackId="composition" 
                fill={COLORS[index % COLORS.length]} 
                radius={index === 0 ? [4, 0, 0, 4] : index === compositionBreakdown.length - 1 ? [0, 4, 4, 0] : [0, 0, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default SpectrumChart;
