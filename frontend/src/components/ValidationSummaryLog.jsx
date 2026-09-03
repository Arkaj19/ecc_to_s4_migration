import React from 'react';

/**
 * ValidationSummaryLog — plain-language findings log built directly from
 * ar_validator.py's structured output.
 *
 * Per the spec, this is Phase 1: rendered straight from the existing
 * validation logic's `message` strings, no LLM involved yet. The
 * `buildRawFindings` export below is the intended hand-off point for
 * that later step — swap its call site for an API call that sends this
 * same string (or the raw `result` object) to an LLM and renders the
 * response instead, without needing to touch how the result is fetched.
 */
export const buildRawFindings = (result) => {
  const lines = [];
  lines.push(`${result.process} Validation — ${result.overall_status}`);
  lines.push(`${result.summary.passed}/${result.summary.total_checks} checks passed`);
  lines.push('');
  result.checks.forEach((check, i) => {
    lines.push(`${i + 1}. [${check.status}] ${check.check_name}: ${check.message}`);
    (check.details || []).forEach((d) => {
      if (d.status !== 'PASS') {
        lines.push(`   - ${d.ecc_code}: ${d.message}`);
      }
    });
  });
  return lines.join('\n');
};

const ValidationSummaryLog = ({ result }) => {
  if (!result) return null;

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-700">Validation Summary</h3>
        <span
          className={`text-xs font-medium px-2.5 py-1 rounded-full ${
            result.overall_status === 'PASS' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}
        >
          {result.overall_status}
        </span>
      </div>
      <pre className="text-xs text-gray-700 bg-gray-50 rounded-lg p-4 whitespace-pre-wrap font-mono leading-relaxed">
        {buildRawFindings(result)}
      </pre>
      <p className="text-xs text-gray-400 mt-2">
        Generated directly from the validation checks. A narrative summary (via LLM) is planned for a later phase.
      </p>
    </div>
  );
};

export default ValidationSummaryLog;
