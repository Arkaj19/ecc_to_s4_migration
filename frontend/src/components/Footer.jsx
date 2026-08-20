import React from 'react';
import { PROCESS_OPTIONS } from './ProcessSelector';

const APP_VERSION = '1.2.0';

/**
 * Footer — the "how many processes are actually live" count is derived
 * from PROCESS_OPTIONS rather than hardcoded, so it can't drift out of
 * sync the way a hand-written "3 of 4 processes live" string would the
 * next time a process flips from coming-soon to active.
 */
const Footer = () => {
  const total = Object.keys(PROCESS_OPTIONS).length;
  const live = Object.values(PROCESS_OPTIONS).filter((p) => p.status === 'active').length;

  return (
    <footer className="border-t border-gray-200 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row items-center justify-between gap-1.5 text-xs text-gray-400">
        <span>ECC → S/4 Migration Tool · v{APP_VERSION}</span>
        <span>{live} of {total} migration processes live</span>
      </div>
    </footer>
  );
};

export default Footer;
