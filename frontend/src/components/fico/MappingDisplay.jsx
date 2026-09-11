import React, { useState } from 'react';

/**
 * MappingDisplay — shows the ECC → S/4 mapping tables from GET
 * /default-mappings. The backend now returns flat arrays of {ecc_*, s4_*}
 * objects (previously it was nested dicts under different key names), so
 * this reads `mappings.cocd`, `mappings.plant_loc`, `mappings.cost_center`
 * rather than the old plant_location_mapping / location_mapping /
 * cost_center_mapping / company_code_mapping shape.
 */
const SECTIONS = [
  { key: 'cocd', label: 'Company Code Mapping', from: 'ecc_cocd', to: 's4_cocd', limit: 8 },
  { key: 'plant_loc', label: 'Plant + Location → S/4 Plant', from: null, to: null, limit: 10 },
  { key: 'cost_center', label: 'Cost Center Overrides', from: 'ecc_cost_center', to: 's4_cost_center', limit: 8 },
];

const MappingDisplay = ({ mappings, isLoading }) => {
  const [expanded, setExpanded] = useState(false);

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        disabled={!mappings}
        className="text-sm text-primary-600 hover:text-primary-800 font-medium disabled:text-gray-400 disabled:cursor-not-allowed"
      >
        View Mapping Tables
      </button>
    );
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500">Loading mappings...</p>;
  }

  if (!mappings) {
    return <p className="text-sm text-red-600">Mapping tables aren't available right now.</p>;
  }

  return (
    <div className="card mt-4">
      <div className="flex justify-between items-center mb-4">
        <h4 className="font-semibold text-gray-700">Mapping Tables</h4>
        <button onClick={() => setExpanded(false)} className="text-sm text-gray-500 hover:text-gray-700">
          Hide
        </button>
      </div>

      <div className="space-y-4">
        {SECTIONS.map(({ key, label, from, to, limit }) => {
          const entries = mappings?.[key];
          if (!entries || entries.length === 0) return null;
          const shown = entries.slice(0, limit);

          return (
            <div key={key}>
              <h5 className="text-sm font-medium text-gray-600">{label}</h5>
              <div className="mt-1 max-h-32 overflow-y-auto bg-gray-50 rounded p-2">
                <div className="text-xs text-gray-700 space-y-0.5">
                  {shown.map((item, i) => (
                    <div key={i}>
                      {key === 'plant_loc' ? (
                        <span>
                          {item.ecc_plant} / {item.ecc_location} → {item.s4_plant} / {item.s4_location}
                        </span>
                      ) : (
                        <span>{item[from]} → {item[to]}</span>
                      )}
                    </div>
                  ))}
                  {entries.length > limit && (
                    <div className="text-gray-400">... and {entries.length - limit} more</div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MappingDisplay;
