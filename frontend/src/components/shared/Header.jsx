import React from 'react';

/**
 * Header — persistent app-shell chrome, separate from the per-file
 * StageTracker in the main content. This carries system-level state
 * (is the backend reachable, which SAP environment does this point at)
 * that stays true regardless of what file is currently loaded, the way
 * an environment badge does in any real migration/deployment tool —
 * getting that wrong (running against the wrong system) is the kind of
 * mistake this badge exists to prevent.
 */
const Header = ({ isConnected, connectionChecked, environment = 'SIT2' }) => {
  return (
    <header className="bg-slate-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="shrink-0 w-8 h-8 rounded-md bg-blue-600 flex items-center justify-center">
            <span className="text-xs font-bold tracking-tight">S4</span>
          </div>
          <div className="min-w-0">
            <h1 className="text-sm sm:text-base font-semibold leading-tight truncate">
              ECC → S/4 Migration Tool
            </h1>
            <p className="text-[10px] sm:text-[11px] uppercase tracking-wider text-slate-400 leading-tight">
              FICO Data Migration
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 sm:gap-4 shrink-0">
          <div
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded border border-slate-700 text-slate-300"
            title="Target SAP environment for this migration run"
          >
            <span className="text-[10px] uppercase tracking-wider text-slate-500">Env</span>
            <span className="text-xs font-mono font-medium">{environment}</span>
          </div>

          <div className="w-px h-5 bg-slate-700 hidden sm:block" />

          <div className="flex items-center gap-1.5">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                !connectionChecked ? 'bg-orange-400 animate-pulse' : isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}
            ></span>
            <span className="text-xs text-slate-300">
              {!connectionChecked ? 'Checking...' : isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
