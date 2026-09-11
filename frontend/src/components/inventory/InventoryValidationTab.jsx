import React, { useState } from 'react';
import InventoryFileUpload from './InventoryFileUpload';
import InventoryMatchPanes from './InventoryMatchPanes';
import InventoryValidationSummary from './InventoryValidationSummary';
import {
  uploadInventoryFiles,
  validateInventory,
  downloadInventoryResults,
} from '../../api/client';

export default function InventoryValidationTab() {
  const [eccFile, setEccFile] = useState(null);
  const [s4File, setS4File] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const [uploading, setUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const bothChosen = eccFile && s4File;

  // --- Upload ---------------------------------------------------------
  const handleUpload = async () => {
    setError(null);
    setUploading(true);
    try {
      const res = await uploadInventoryFiles(eccFile, s4File);
      setSessionId(res.session_id);
      setResult(null); // clear previous validation
    } catch (e) {
      setError(e.message || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  // --- Validate -------------------------------------------------------
  const handleValidate = async () => {
    if (!sessionId) {
      setError('Upload files first.');
      return;
    }
    setError(null);
    setValidating(true);
    try {
      const res = await validateInventory(sessionId, 50);
      setResult(res);
    } catch (e) {
      setError(e.message || 'Validation failed.');
    } finally {
      setValidating(false);
    }
  };

  // --- Download ---------------------------------------------------------
  const handleDownload = async () => {
    if (!result?.download_id) return;
    setDownloading(true);
    try {
      const { blob, filename } = await downloadInventoryResults(result.download_id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message || 'Download failed.');
    } finally {
      setDownloading(false);
    }
  };

  // --- Reset (nice-to-have) ------------------------------------------
  const handleReset = () => {
    setEccFile(null);
    setS4File(null);
    setSessionId(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="space-y-6">
      {/* Step 1: upload */}
      <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Inventory ECC &harr; S4 Validation
        </h2>

        <InventoryFileUpload
          eccFile={eccFile}
          s4File={s4File}
          onEccChange={(f) => {
            setEccFile(f);
            setSessionId(null);
            setResult(null);
          }}
          onS4Change={(f) => {
            setS4File(f);
            setSessionId(null);
            setResult(null);
          }}
          onUpload={handleUpload}
          onReset={handleReset}
          uploaded={!!sessionId}
          uploading={uploading}
        />
      </section>

      {/* Step 2: validate */}
      {sessionId && (
        <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Files uploaded. Ready to sample 50 common rows.
          </div>
          <button
            onClick={handleValidate}
            disabled={validating}
            className="px-5 py-2 rounded-md bg-blue-600 text-white font-medium
                       hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
          >
            {validating ? 'Validating…' : 'Validate'}
          </button>
        </section>
      )}

      {/* Error banner */}
      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Step 3: results */}
      {result && (
        <>
          {/* Two Excel panes side by side */}
          <InventoryMatchPanes
            eccRows={result.ecc_rows}
            eccColumns={result.columns_ecc}
            s4Rows={result.s4_rows}
            s4Columns={result.columns_s4}
          />

          {/* Validation summary below the panes */}
          <InventoryValidationSummary summary={result.summary} />

          {/* Download button */}
          <div className="flex justify-end">
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="px-5 py-2 rounded-md bg-green-600 text-white font-medium
                         hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed
                         transition-colors"
            >
              {downloading ? 'Downloading…' : 'Download Results'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}