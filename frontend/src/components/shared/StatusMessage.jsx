import React from 'react';

/**
 * StatusMessage — colors carry the meaning (green/orange/red), matching the
 * StageTracker palette. 'info' (an action in progress) uses orange rather
 * than blue so the whole app reads off one consistent 3-color system.
 */
const StatusMessage = ({ type, message, details }) => {
  if (!message) return null;

  const styles = {
    success: 'bg-green-50 border-green-500 text-green-800',
    error: 'bg-red-50 border-red-500 text-red-800',
    info: 'bg-orange-50 border-orange-500 text-orange-800',
  };

  const icons = {
    success: (
      <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5 text-orange-500 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="9" strokeWidth={2} />
      </svg>
    ),
  };

  return (
    <div className={`border-l-4 p-4 rounded-r-lg ${styles[type] ?? styles.info}`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">{icons[type] ?? icons.info}</div>
        <div className="ml-3">
          <p className="text-sm font-medium">{message}</p>
          {details && <p className="text-sm mt-1 opacity-80">{details}</p>}
        </div>
      </div>
    </div>
  );
};

export default StatusMessage;
