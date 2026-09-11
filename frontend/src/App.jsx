import React, { useState, useEffect } from 'react';

import Header from './components/shared/Header';
import Footer from './components/shared/Footer';
import TabNav from './components/shared/TabNav';

// FICO
import MigrationTab from './components/fico/MigrationTab';
import DataValidationTab from './components/fico/DataValidationTab';

// Inventory
import InventoryValidationTab from './components/inventory/InventoryValidationTab';

import { checkHealth } from './api/client';

// Domain registry — single source of truth for nav + dispatch.
const DOMAINS = [
  {
    key: 'fico',
    label: 'FICO',
    children: [
      { key: 'migration', label: 'Migration' },
      { key: 'data-validation', label: 'Data Validation' },
    ],
  },
  {
    key: 'inventory',
    label: 'Inventory',
    children: null, // single screen — no sub-tabs
  },
];

function App() {
  const [activeDomain, setActiveDomain] = useState('fico');
  const [activeSubTab, setActiveSubTab] = useState('migration');

  const [isConnected, setIsConnected] = useState(false);
  const [connectionChecked, setConnectionChecked] = useState(false);

  // Connection status lives here, not in either tab — Header needs it
  // regardless of which tab is active, and it shouldn't re-check every
  // time someone switches tabs.
  useEffect(() => {
    const check = async () => {
      try {
        await checkHealth();
        setIsConnected(true);
      } catch (error) {
        setIsConnected(false);
      } finally {
        setConnectionChecked(true);
      }
    };
    check();
  }, []);

  // When switching domains, land on the first sub-tab of the new domain
  // (or null if that domain has no sub-tabs). Without this, going
  // FICO -> Inventory -> FICO would leave activeSubTab stale.
  const handleDomainChange = (domainKey) => {
    setActiveDomain(domainKey);
    const domain = DOMAINS.find((d) => d.key === domainKey);
    setActiveSubTab(domain?.children?.[0]?.key ?? null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-gray-50 to-gray-100">
      <Header isConnected={isConnected} connectionChecked={connectionChecked} />
      <TabNav
        domains={DOMAINS}
        activeDomain={activeDomain}
        activeSubTab={activeSubTab}
        onDomainChange={handleDomainChange}
        onSubTabChange={setActiveSubTab}
      />

      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeDomain === 'fico' && activeSubTab === 'migration' && (
          <MigrationTab
            isConnected={isConnected}
            connectionChecked={connectionChecked}
          />
        )}

        {activeDomain === 'fico' && activeSubTab === 'data-validation' && (
          <DataValidationTab isConnected={isConnected} />
        )}

        {activeDomain === 'inventory' && <InventoryValidationTab />}
      </main>

      <Footer />

      <style>{`
        @keyframes slideDown {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-slideDown { animation: slideDown 0.3s ease-out; }
      `}</style>
    </div>
  );
}

export default App;