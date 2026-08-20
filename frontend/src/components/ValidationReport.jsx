import React from 'react';

/**
 * ValidationReport — shows which mandatory columns still have missing data
 * after processing. The file is generated either way (the backend never
 * blocks on this), so this is a data-quality warning, not an error state:
 * amber, not red. Errors are grouped by sheet since that's how the
 * underlying template is structured and how someone would go fix them.
 */
const ValidationReport = ({ report, isLoading }) => {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-500 px-1">
        <span className="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse"></span>
        Checking mandatory fields...
      </div>
    );
  }

  if (!report) return null;

  if (report.valid) {
    return (
      <div className="flex items-center gap-2 text-xs text-green-700 px-1">
        <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
        All mandatory fields are populated.
      </div>
    );
  }

  const bySheet = report.errors.reduce((acc, err) => {
    (acc[err.sheet] ??= []).push(err);
    return acc;
  }, {});

  const totalMissingRows = report.errors.reduce((sum, e) => sum + e.missing_rows, 0);

  return (
    <div className="border border-orange-200 bg-orange-50 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-orange-200">
        <span className="w-1.5 h-1.5 rounded-full bg-orange-500"></span>
        <h4 className="text-sm font-medium text-orange-900">
          Data quality warnings
        </h4>
        <span className="text-xs text-orange-700 ml-auto">
          {report.errors.length} column{report.errors.length !== 1 ? 's' : ''} · {totalMissingRows} row{totalMissingRows !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="divide-y divide-orange-100 max-h-56 overflow-y-auto">
        {Object.entries(bySheet).map(([sheet, errors]) => (
          <div key={sheet} className="px-4 py-2.5">
            <p className="text-xs font-medium text-gray-500 mb-1.5">{sheet}</p>
            <div className="space-y-1">
              {errors.map((err) => (
                <div key={err.column} className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="text-gray-700">{err.column}</span>
                  <span className="text-orange-700 text-xs whitespace-nowrap">
                    {err.missing_rows} missing row{err.missing_rows !== 1 ? 's' : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ValidationReport;
