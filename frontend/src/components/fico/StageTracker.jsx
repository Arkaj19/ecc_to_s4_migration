import React from 'react';

/**
 * StageTracker — shows where the user is in the Upload → Preview → Process →
 * Download pipeline using color alone (gray/orange/green/red), no icons or
 * emoji. Each stage is one of:
 *   pending  - gray  - not reached yet
 *   active   - orange - in progress right now
 *   success  - green - completed
 *   error    - red   - failed
 */
const DOT_STYLES = {
  pending: 'bg-gray-200 border-gray-300',
  active: 'bg-orange-500 border-orange-500 animate-pulse',
  success: 'bg-green-500 border-green-500',
  error: 'bg-red-500 border-red-500',
};

const LABEL_STYLES = {
  pending: 'text-gray-400',
  active: 'text-orange-600 font-medium',
  success: 'text-green-700 font-medium',
  error: 'text-red-600 font-medium',
};

const LINE_STYLES = {
  pending: 'bg-gray-200',
  active: 'bg-orange-300',
  success: 'bg-green-400',
  error: 'bg-red-300',
};

const StageTracker = ({ stages }) => {
  return (
    <div className="flex items-center w-full">
      {stages.map((stage, i) => (
        <React.Fragment key={stage.key}>
          <div className="flex flex-col items-center gap-1.5 shrink-0">
            <span
              className={`block w-3 h-3 rounded-full border-2 ${DOT_STYLES[stage.status]}`}
              aria-hidden="true"
            />
            <span className={`text-[11px] leading-none ${LABEL_STYLES[stage.status]}`}>
              {stage.label}
            </span>
          </div>
          {i < stages.length - 1 && (
            <div className={`h-0.5 flex-1 mx-2 mb-4 rounded-full ${LINE_STYLES[stage.status]}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

export default StageTracker;
