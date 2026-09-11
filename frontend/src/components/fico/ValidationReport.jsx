import React from 'react';

/**
 * ValidationReport — shows two distinct kinds of data-quality signal after
 * processing, both from routes that generate the file either way:
 *
 *  - skipped sheets: entire tabs in the uploaded workbook that didn't
 *    match the expected column shape, so none of their rows made it into
 *    the output at all. This is flagged in red — it's not a "some fields
 *    are blank" warning, it's "some of your data isn't in the file."
 *  - mandatory field gaps: rows that did make it in, but are missing a
 *    value the target template marks as required. Amber, since the file
 *    was still generated.
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

  const skippedSheets = report.skipped_sheets || [];
  const hasFieldErrors = !report.valid && report.errors?.length > 0;

  if (skippedSheets.length === 0 && !hasFieldErrors) {
    return (
      <div className="flex items-center gap-2 text-xs text-green-700 px-1">
        <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
        All sheets included, all mandatory fields populated.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {skippedSheets.length > 0 && (
        <div className="border border-red-200 bg-red-50 rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-red-200">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
            <h4 className="text-sm font-medium text-red-900">
              Sheets not included
            </h4>
            <span className="text-xs text-red-700 ml-auto">
              {skippedSheets.length} sheet{skippedSheets.length !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="divide-y divide-red-100">
            {skippedSheets.map((s) => (
              <div key={s.sheet} className="px-4 py-2.5">
                <p className="text-sm text-gray-800">{s.sheet}</p>
                <p className="text-xs text-red-700 mt-0.5">{s.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasFieldErrors && <MandatoryFieldPanel report={report} />}
    </div>
  );
};

const MandatoryFieldPanel = ({ report }) => {
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
