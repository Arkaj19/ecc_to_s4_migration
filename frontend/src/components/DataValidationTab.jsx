import React, { useState, useEffect } from 'react';

import FileUpload from './FileUpload';
import ValidationProcessSelector, { VALIDATION_PROCESS_OPTIONS } from './ValidationProcessSelector';
import StatusMessage from './StatusMessage';
import ValidationSummaryLog from './ValidationSummaryLog';
import ValidationScoreboard from './ValidationScoreboard';
import ProcessingStatus from './ProcessingStatus';

import { validateArMigration } from '../api/client';
import { previewExcelFile } from '../utils/excelPreview';

// Maps each active validation process to its API call. Same pattern as
// MigrationTab's PROCESS_HANDLERS — add an entry here when a process
// flips from 'coming-soon' to 'active' in VALIDATION_PROCESS_OPTIONS.
const VALIDATION_HANDLERS = {
  AR: validateArMigration,
};

function DataValidationTab({ isConnected }) {
  const [eccFile, setEccFile] = useState(null);
  const [s4File, setS4File] = useState(null);
  const [selectedProcess, setSelectedProcess] = useState('AR');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState({ type: null, message: null, details: null });

  // Drives the ProcessingStatus progress bar below, same as MigrationTab.
  // The ECC file is read client-side just for its row count (no visible
  // preview here) so the bar has something to estimate against.
  const [eccRowCount, setEccRowCount] = useState(0);
  const [validationTime, setValidationTime] = useState(0);

  const isSupported = VALIDATION_PROCESS_OPTIONS[selectedProcess]?.status === 'active';
  const canRun = isConnected && isSupported && eccFile && s4File && !running;

  // Elapsed-time ticker while validation is running — feeds ProcessingStatus's
  // elapsedTime prop the same way MigrationTab's processingTime does.
  useEffect(() => {
    let timer;
    if (running) {
      setValidationTime(0);
      timer = setInterval(() => {
        setValidationTime((prev) => prev + 1);
      }, 1000);
    } else {
      setValidationTime(0);
    }
    return () => clearInterval(timer);
  }, [running]);

  const handleEccFileUpload = async (uploadedFile) => {
    setEccFile(uploadedFile);
    setEccRowCount(0);
    setResult(null);
    setStatus({ type: null, message: null });

    if (!uploadedFile) return;

    try {
      const preview = await previewExcelFile(uploadedFile, 1);
      if (preview.success) {
        setEccRowCount(preview.total_rows);
      }
    } catch {
      // Row count is only used to drive the progress-bar estimate — if it
      // can't be read, the bar just won't render; validation itself isn't
      // blocked by this.
    }
  };

  const handleRun = async () => {
    if (!canRun) return;

    setRunning(true);
    setResult(null);
    setStatus({ type: 'info', message: 'Running validation...' });

    try {
      const handler = VALIDATION_HANDLERS[selectedProcess];
      const validationResult = await handler(eccFile, s4File);
      setResult(validationResult);
      setStatus({
        type: validationResult.overall_status === 'PASS' ? 'success' : 'error',
        message: `Validation complete — ${validationResult.overall_status}`,
        details: `${validationResult.summary.passed}/${validationResult.summary.total_checks} checks passed`,
      });
    } catch (error) {
      setStatus({ type: 'error', message: 'Validation failed', details: error.message });
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      {status.message && (
        <div className="mb-4 animate-slideDown">
          <StatusMessage type={status.type} message={status.message} details={status.details} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 space-y-4">
          <FileUpload
            title="Original ECC File"
            dropText="the original ECC registry"
            onFileUpload={handleEccFileUpload}
            file={eccFile}
            disabled={running}
          />

          <FileUpload
            title="Migrated S/4 File"
            dropText="the migrated S/4 output"
            onFileUpload={setS4File}
            file={s4File}
            disabled={running}
          />

          <ValidationProcessSelector
            selectedProcess={selectedProcess}
            onProcessChange={setSelectedProcess}
            disabled={running}
          />

          <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
            <button
              onClick={handleRun}
              disabled={!canRun}
              className="w-full btn-primary py-3 text-lg"
            >
              {running
                ? 'Running Validation...'
                : !isConnected
                ? 'Backend not connected'
                : !isSupported
                ? `${VALIDATION_PROCESS_OPTIONS[selectedProcess]?.label} coming soon`
                : (!eccFile || !s4File)
                ? 'Upload both files first'
                : 'Run Validation'}
            </button>

            {running && eccRowCount > 0 && (
              <ProcessingStatus
                totalRows={eccRowCount}
                elapsedTime={validationTime}
                fileSize={eccFile?.size || 0}
              />
            )}
          </div>
        </div>

        <div className="lg:col-span-8 space-y-4">
          {!result && !running && (
            <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-8 text-center text-gray-400 text-sm">
              Upload the ECC registry and the migrated S/4 file, then run validation to see results here.
            </div>
          )}

          {result && (
            <>
              <ValidationSummaryLog result={result} />
              <ValidationScoreboard result={result} />
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default DataValidationTab;
