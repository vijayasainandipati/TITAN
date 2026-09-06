import React from 'react';

export default function StatusPill({ status = 'nominal', label, sublabel }) {
  const s = status ? status.toLowerCase() : 'nominal';
  let pillClass = 'nominal';
  let icon = (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <circle cx="12" cy="12" r="10" />
      <path d="M8 12l2.5 2.5L16 9" />
    </svg>
  );

  if (s.includes('critical') || s.includes('no-go') || s.includes('fail') || s.includes('error')) {
    pillClass = 'critical';
    icon = (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
    );
  } else if (s.includes('caution') || s.includes('warn') || s.includes('drift')) {
    pillClass = 'caution';
    icon = (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    );
  } else if (s.includes('envelope') || s.includes('twin') || s.includes('virtual')) {
    pillClass = 'envelope';
    icon = (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <circle cx="12" cy="12" r="10" />
        <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
      </svg>
    );
  }

  const displayText = label || status;

  return (
    <span className={`status-pill ${pillClass}`}>
      {icon}
      <span>{displayText}</span>
      {sublabel && <span style={{ opacity: 0.75, fontSize: '0.68rem', marginLeft: '0.2rem' }}>({sublabel})</span>}
    </span>
  );
}
