// export default ValidationScoreboard;
import React, { useState } from 'react';

/**
 * ValidationScoreboard — renders ar_validator.py's `checks` array as a
 * LeetCode-style pass/fail list with an overall score.
 *
 * Every check now carries a unified `details` array (record count and
 * payment terms get a single row, company code gets one row per code,
 * sign validation gets one row per S/H side), each shaped as:
 *   { label, left_count, right_count, status, message, money? }
 * so a single renderer below covers all four checks instead of one
 * hard-coded to the company-code shape.
 */
const formatCount = (value, money) => {
  if (value === null || value === undefined) return '—';
  return money
    ? Number(value).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    : Number(value).toLocaleString();
};

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
            <div key={i} className="px-4 py-2 flex items-center justify-between gap-3 text-xs">
              <span className="text-gray-600 shrink-0">{d.label}</span>
              <span
                className={`text-right ${
                  d.status === 'PASS' ? 'text-green-700' : 'text-red-700'
                }`}
              >
                {d.status === 'PASS'
                  ? `${formatCount(d.left_count, d.money)} = ${formatCount(d.right_count, d.money)}`
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
  const [downloading, setDownloading] = useState(false);
  
  if (!result) return null;

  const { process, summary, checks, report_available } = result;
  const allPassed = summary.failed === 0;

  const handleDownloadReport = async () => {
    setDownloading(true);
    try {
      const response = await fetch('/api/download-ar-report');
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'AR_Validation_Report.pdf';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        console.error('Failed to download report');
      }
    } catch (error) {
      console.error('Error downloading report:', error);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-700">
          {process} Validation Score
        </h3>
        <div className="flex items-center gap-3">
          <span
            className={`text-sm font-semibold px-3 py-1 rounded-full ${
              allPassed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}
          >
            {summary.passed}/{summary.total_checks}
          </span>
          
          {/* Download Report Button */}
          {report_available && (
            <button
              onClick={handleDownloadReport}
              disabled={downloading}
              className="text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white px-3 py-1 rounded-lg transition-colors flex items-center gap-2"
            >
              {downloading ? (
                <>
                  <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  Generating...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download PDF
                </>
              )}
            </button>
          )}
        </div>
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