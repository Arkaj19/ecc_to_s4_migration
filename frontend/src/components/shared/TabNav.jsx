import React from 'react';

export default function TabNav({
  domains,
  activeDomain,
  activeSubTab,
  onDomainChange,
  onSubTabChange,
}) {
  const current = domains.find((d) => d.key === activeDomain);

  return (
    <nav className="w-full bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Top-level: FICO | Inventory */}
        <div className="flex gap-6">
          {domains.map((d) => {
            const isActive = activeDomain === d.key;
            return (
              <button
                key={d.key}
                onClick={() => onDomainChange(d.key)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  isActive
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {d.label}
              </button>
            );
          })}
        </div>

        {/* Sub-level: Migration | Data Validation (only when the domain has children) */}
        {current?.children && (
          <div className="flex gap-2 pb-2 -mt-1">
            {current.children.map((c) => {
              const isActive = activeSubTab === c.key;
              return (
                <button
                  key={c.key}
                  onClick={() => onSubTabChange(c.key)}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  {c.label}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </nav>
  );
}