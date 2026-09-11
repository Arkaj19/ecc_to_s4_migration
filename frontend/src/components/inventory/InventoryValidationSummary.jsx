import React from 'react';

export default function InventoryValidationSummary({ summary }) {
  if (!summary) return null;

  const cells = [
    { label: 'ECC rows', value: summary.ecc_rows },
    { label: 'S4 rows', value: summary.s4_rows },
    { label: 'ECC unique keys', value: summary.ecc_unique_keys },
    { label: 'S4 unique keys', value: summary.s4_unique_keys },
    { label: 'Common keys', value: summary.common_keys, accent: true },
    { label: 'Sampled', value: summary.sample_size },
  ];

  return (
    <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        Validation Results
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {cells.map(({ label, value, accent }) => (
          <div
            key={label}
            className={`rounded-lg border p-3 ${
              accent
                ? 'border-blue-200 bg-blue-50'
                : 'border-gray-200 bg-gray-50'
            }`}
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide">
              {label}
            </div>
            <div
              className={`mt-1 text-2xl font-semibold font-mono ${
                accent ? 'text-blue-700' : 'text-gray-800'
              }`}
            >
              {value}
            </div>
          </div>
        ))}
      </div>

      <p className="mt-4 text-xs text-gray-500">
        Matched on composite key: <code>Material | Plant | Storage_Location</code>.
        ECC keys use converted Plant/Storage_Location per ECC &rarr; S4 rules.
      </p>
    </section>
  );
}