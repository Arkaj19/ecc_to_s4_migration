// components/ProcessingStatus.jsx

import React from 'react';

const ProcessingStatus = ({ totalRows, elapsedTime, fileSize }) => {
  const isLargeFile = totalRows > 10000;
  const estimatedSeconds = Math.max(Math.ceil(totalRows / 500), 30); // ~500 rows per second, min 30s
  const fileSizeMB = fileSize ? (fileSize / 1024 / 1024).toFixed(1) : 0;
  
  // Calculate progress percentage
  const progressPercentage = Math.min((elapsedTime / estimatedSeconds) * 100, 95);
  
  // Format time
  const formatTime = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-blue-800 font-medium">
            Processing {totalRows.toLocaleString()} rows
          </p>
          {isLargeFile && (
            <p className="text-xs text-blue-600 mt-0.5">
              Large file detected ({fileSizeMB}MB)
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-blue-600">
            {formatTime(elapsedTime)}
          </span>
          <span className="text-xs text-blue-400">
            / ~{formatTime(estimatedSeconds)}
          </span>
        </div>
      </div>
      
      <div className="mt-2 w-full bg-blue-200 rounded-full h-2 overflow-hidden">
        <div 
          className="bg-blue-600 h-2 rounded-full transition-all duration-1000 ease-in-out"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>
      
      <div className="mt-1.5 flex justify-between text-xs text-blue-600">
        <span>
          {isLargeFile 
            ? `${Math.round((elapsedTime / estimatedSeconds) * 100)}% complete`
            : 'Processing...'}
        </span>
        <span>
          {isLargeFile 
            ? `Estimated ${Math.ceil(estimatedSeconds / 60)} minute${Math.ceil(estimatedSeconds / 60) > 1 ? 's' : ''}`
            : 'Please wait'}
        </span>
      </div>
      
      {/* Show speed indicator for large files */}
      {isLargeFile && elapsedTime > 10 && (
        <div className="mt-1.5 text-xs text-blue-500">
          ⚡ Processing ~{(totalRows / Math.max(elapsedTime, 1)).toFixed(0)} rows/second
        </div>
      )}
    </div>
  );
};

export default ProcessingStatus;