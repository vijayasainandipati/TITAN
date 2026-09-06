import React from 'react';

export default function Gauge({
  value = 0,
  min = 0,
  max = 100,
  label = 'Metric',
  unit = '',
  cautionThreshold = 75,
  criticalThreshold = 90,
  isLowCritical = false, // E.g., for oil pressure where low is critical
  size = 140
}) {
  // Normalize value within [min, max]
  const clampedVal = Math.min(Math.max(value, min), max);
  const ratio = (clampedVal - min) / Math.max(max - min, 1);
  
  // Angle: from -135 deg to +135 deg (270 deg total sweep)
  const angle = -135 + ratio * 270;

  // Determine color state using CSS variable names
  let color = 'var(--status-nominal)';
  if (isLowCritical) {
    if (value <= criticalThreshold) color = 'var(--status-critical)';
    else if (value <= cautionThreshold) color = 'var(--status-caution)';
  } else {
    if (value >= criticalThreshold) color = 'var(--status-critical)';
    else if (value >= cautionThreshold) color = 'var(--status-caution)';
  }

  const radius = 52;
  const cx = size / 2;
  const cy = size / 2 + 5;
  const strokeWidth = 8;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * (270 / 360);
  const strokeDashoffset = arcLength * (1 - ratio);

  return (
    <div className="gauge-container" style={{ width: size, textAlign: 'center' }}>
      <svg width={size} height={size - 15} viewBox={`0 0 ${size} ${size}`}>
        {/* Background Arc */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke="var(--border-color)"
          strokeWidth={strokeWidth}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={0}
          strokeLinecap="round"
          transform={`rotate(135 ${cx} ${cy})`}
        />
        {/* Active Colored Arc */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          transform={`rotate(135 ${cx} ${cy})`}
          style={{ transition: 'stroke-dashoffset 0.35s ease, stroke 0.35s ease' }}
        />
        {/* Needle Tick */}
        <g transform={`rotate(${angle} ${cx} ${cy})`}>
          <line
            x1={cx}
            y1={cy - radius + 4}
            x2={cx}
            y2={cy - radius - 6}
            stroke="var(--text-primary)"
            strokeWidth={3}
            strokeLinecap="round"
          />
        </g>
      </svg>
      <div className="gauge-value telemetry-val" style={{ color, fontFamily: 'var(--font-mono)', fontSize: '1.2rem' }}>
        {typeof value === 'number' ? value.toFixed(1) : value}
        <span style={{ fontSize: '0.72rem', marginLeft: '3px', color: 'var(--text-muted)', fontWeight: 500 }}>{unit}</span>
      </div>
      <div className="gauge-label" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500, marginTop: '0.15rem' }}>{label}</div>
    </div>
  );
}
