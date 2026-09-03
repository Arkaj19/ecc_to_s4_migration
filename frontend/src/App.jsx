import React, { useState, useEffect } from 'react';

import Header from './components/Header';
import Footer from './components/Footer';
import TabNav from './components/TabNav';
import MigrationTab from './components/MigrationTab';
import DataValidationTab from './components/DataValidationTab';

import { checkHealth } from './api/client';

function App() {
  const [activeTab, setActiveTab] = useState('migration');
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

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-gray-50 to-gray-100">
      <Header isConnected={isConnected} connectionChecked={connectionChecked} />
      <TabNav activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'migration' ? (
          <MigrationTab isConnected={isConnected} connectionChecked={connectionChecked} />
        ) : (
          <DataValidationTab isConnected={isConnected} />
        )}
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
