import React, { useState } from 'react';

/**
 * ValidationScoreboard — renders ar_validator.py's `checks` array as a
 * LeetCode-style pass/fail list with an overall score. Deliberately
 * generic over check shape: some checks (record count) are flat,
 * others (company code distribution) carry a `details` array of
 * per-company-code sub-results — both render, sub-details collapsed
 * by default since they can get long.
 */
const CheckRow = ({ check, index }) => {
  const [expanded, setExpanded] = useState(false);
  const passed = check.status === 'PASS';
  const hasDetails = Array.isArray(check.details) && check.details.length > 0;

  return (
    <div className="border border-gray-100 rounded-lg overflow-hidden">
      <button
        onClick={() => hasDetails && setExpanded((v) => !v)}
        className={`w-full flex items-center gap-3 px-4 py-3 text-left ${hasDetails ? 'cursor-pointer hover:bg-gray-50' : 'cursor-default'}`}
      >
        <span className={`text-lg leading-none ${passed ? 'text-green-600' : 'text-red-600'}`}>
          {passed ? '✅' : '❌'}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800">
            Test {index + 1} — {check.check_name}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">{check.message}</p>
        </div>
        {hasDetails && (
          <span className="text-xs text-gray-400 shrink-0">{expanded ? 'Hide' : 'Details'}</span>
        )}
      </button>

      {hasDetails && expanded && (
        <div className="border-t border-gray-100 divide-y divide-gray-50">
          {check.details.map((d, i) => (
            <div key={i} className="px-4 py-2 flex items-center justify-between text-xs">
              <span className="text-gray-600">
                {d.ecc_code}{d.s4_code ? ` → ${d.s4_code}` : ''}
              </span>
              <span className={d.status === 'PASS' ? 'text-green-700' : 'text-red-700'}>
                {d.status === 'PASS'
                  ? `${d.ecc_count} = ${d.s4_count}`
                  : d.message}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const ValidationScoreboard = ({ result }) => {
  if (!result) return null;

  const { process, summary, checks } = result;
  const allPassed = summary.failed === 0;

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-700">
          {process} Validation Score
        </h3>
        <span
          className={`text-sm font-semibold px-3 py-1 rounded-full ${
            allPassed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}
        >
          {summary.passed}/{summary.total_checks}
        </span>
      </div>

      <div className="space-y-2">
        {checks.map((check, i) => (
          <CheckRow key={check.check_name || i} check={check} index={i} />
        ))}
      </div>
    </div>
  );
};

export default ValidationScoreboard;
