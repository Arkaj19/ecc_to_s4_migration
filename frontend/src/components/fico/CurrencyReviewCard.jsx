import React from 'react';
import { ClipLoader } from 'react-spinners';

/**
 * Shown in place of the normal success state when POST /process-ar comes
 * back with { status: 'CURRENCY_REVIEW_REQUIRED', ... } instead of a file.
 * That happens when a row's company code doesn't match its expected
 * currency (e.g. company code 1200 expects CAD but the row is USD).
 *
 * KEEP  -> re-submit with currency_action=KEEP; mismatched rows stay in
 *          the output, highlighted red.
 * DELETE -> re-submit with currency_action=DELETE; mismatched rows are
 *           removed from the main sheet and moved to a
 *           "Currency Mismatch Dump" sheet in the same workbook.
 */
const CurrencyReviewCard = ({ payload, onKeep, onDelete, isSubmitting }) => {
  if (!payload) return null;

  const mismatches = payload.mismatches || [];

  return (
    <div className="bg-white rounded-xl shadow-lg border border-red-200 p-5 space-y-4">
      <div className="flex items-start gap-3">
        <span className="flex-shrink-0 w-8 h-8 rounded-full bg-red-100 text-red-600 flex items-center justify-center font-semibold">
          !
        </span>
        <div>
          <h4 className="text-sm font-semibold text-gray-800">
            Currency mismatch{payload.mismatch_count === 1 ? '' : 'es'} found
          </h4>
          <p className="text-sm text-gray-600 mt-1">{payload.message}</p>
        </div>
      </div>

      {mismatches.length > 0 && (
        <div className="max-h-48 overflow-y-auto border border-gray-100 rounded-lg">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 text-gray-500 sticky top-0">
              <tr>
                <th className="text-left px-3 py-2 font-medium">Source Row</th>
                <th className="text-left px-3 py-2 font-medium">Company Code</th>
                <th className="text-left px-3 py-2 font-medium">Currency</th>
                <th className="text-left px-3 py-2 font-medium">Expected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {mismatches.map((m, i) => (
                <tr key={i} className="text-gray-700">
                  <td className="px-3 py-1.5">{m.source_row}</td>
                  <td className="px-3 py-1.5">{m.company_code}</td>
                  <td className="px-3 py-1.5">{m.currency || 'blank'}</td>
                  <td className="px-3 py-1.5">{m.expected_currency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-2 pt-1">
        <button
          onClick={onKeep}
          disabled={isSubmitting}
          className="flex-1 btn-primary py-2.5 text-sm bg-amber-600 hover:bg-amber-700 disabled:opacity-60"
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center gap-2">
              <ClipLoader size={16} color="#ffffff" />
              Working...
            </span>
          ) : (
            'Keep rows (highlight red)'
          )}
        </button>
        <button
          onClick={onDelete}
          disabled={isSubmitting}
          className="flex-1 btn-primary py-2.5 text-sm bg-red-600 hover:bg-red-700 disabled:opacity-60"
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center gap-2">
              <ClipLoader size={16} color="#ffffff" />
              Working...
            </span>
          ) : (
            'Delete rows (move to log sheet)'
          )}
        </button>
      </div>
    </div>
  );
};

export default CurrencyReviewCard;
