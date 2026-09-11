import React from 'react';

// Exported so App.jsx and ProcessButton.jsx can check which process types
// are actually implemented without duplicating this list elsewhere — this
// is the single source of truth for "active" vs "coming soon".
export const PROCESS_OPTIONS = {
  ASSETS: { label: 'Assets', status: 'active', description: 'Asset Master & Values Migration' },
  AP: { label: 'Accounts Payable', status: 'active', description: 'Vendor & Invoice Migration' },
  AR: { label: 'Accounts Receivable', status: 'active', description: 'Customer & Invoice Migration' },
  CREDIT: { label: 'Credit Management', status: 'active', description: 'Credit Limit & Risk Migration' },
};

const ProcessSelector = ({ selectedProcess, onProcessChange, disabled }) => {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-700 mb-4">
        Process Selection
      </h3>
      <div className="space-y-2">
        {Object.entries(PROCESS_OPTIONS).map(([key, value]) => {
          const isActive = value.status === 'active';
          const isSelected = selectedProcess === key;
          
          return (
            <label
              key={key}
              className={`flex items-center p-3 rounded-lg border-2 cursor-pointer transition-all
                ${isSelected ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'}
                ${!isActive ? 'opacity-60' : ''}
                ${disabled ? 'cursor-not-allowed opacity-50' : ''}
              `}
              onClick={() => !disabled && isActive && onProcessChange(key)}
            >
              <input
                type="radio"
                name="process"
                value={key}
                checked={isSelected}
                onChange={() => {}}
                disabled={!isActive || disabled}
                className="sr-only"
              />
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-gray-700">{value.label}</span>
                  {!isActive && (
                    <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">
                      Coming Soon
                    </span>
                  )}
                  {isActive && isSelected && (
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                      Selected
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500">{value.description}</p>
              </div>
              {isActive && (
                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center
                  ${isSelected ? 'border-primary-500 bg-primary-500' : 'border-gray-300'}`}
                >
                  {isSelected && (
                    <svg className="w-2 h-2 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
              )}
            </label>
          );
        })}
      </div>
    </div>
  );
};

export default ProcessSelector;