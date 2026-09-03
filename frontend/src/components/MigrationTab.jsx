import React, { useState, useEffect } from 'react';

import FileUpload from './FileUpload';
import ProcessSelector, { PROCESS_OPTIONS } from './ProcessSelector';
import DataPreview from './DataPreview';
import MappingDisplay from './MappingDisplay';
import StatusMessage from './StatusMessage';
import ProcessButton from './ProcessButton';
import DownloadButton from './DownloadButton';
import StageTracker from './StageTracker';
import ValidationReport from './ValidationReport';

import {
  processAssetFile,
  processCreditFile,
  processApFile,
  processArFile,
  validateAssetFile,
  validateCreditFile,
  validateApFile,
  getDefaultMappings,
} from '../api/client';
import { previewExcelFile } from '../utils/excelPreview';

// Maps each active process type to its API calls. Add an entry here (and
// matching exports in api/client.js) whenever a new process type flips
// from 'coming-soon' to 'active' in ProcessSelector's PROCESS_OPTIONS.
const PROCESS_HANDLERS = {
  ASSETS: processAssetFile,
  CREDIT: processCreditFile,
  AP: processApFile,
  AR: processArFile,
};

// A process type missing from this map means "validation not implemented
// for it yet" and must be handled as "don't claim anything" wherever this
// map is read — not "assume it passed".
//
// AR is deliberately absent: the backend's /validate-ar route was
// repurposed for the Data Validation tab's ECC-vs-S/4 comparison (two
// files, a completely different response shape) — there's currently no
// route left that checks a freshly-processed AR file for missing
// mandatory fields the way this map expects.
const VALIDATE_HANDLERS = {
  ASSETS: validateAssetFile,
  CREDIT: validateCreditFile,
  AP: validateApFile,
};

function MigrationTab({ isConnected, connectionChecked }) {
  const [file, setFile] = useState(null);
  const [selectedProcess, setSelectedProcess] = useState('ASSETS');
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processError, setProcessError] = useState(false);
  const [processedFile, setProcessedFile] = useState(null);
  const [downloaded, setDownloaded] = useState(false);
  const [validationReport, setValidationReport] = useState(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [mappings, setMappings] = useState(null);
  const [mappingsLoading, setMappingsLoading] = useState(false);
  const [status, setStatus] = useState({ type: null, message: null, details: null });

  // Connection health is owned by App.jsx (Header needs it too, and it's
  // app-shell state, not Migration-specific) — this only loads the
  // mapping tables, which genuinely are scoped to this tab, and surfaces
  // a helpful status message if the backend isn't reachable.
  useEffect(() => {
    if (!connectionChecked) return;

    if (!isConnected) {
      setStatus({
        type: 'error',
        message: 'Cannot connect to backend API',
        details: 'Make sure the FastAPI server is running on port 8000',
      });
      return;
    }

    const loadMappings = async () => {
      setMappingsLoading(true);
      try {
        const mappingsData = await getDefaultMappings();
        setMappings(mappingsData);
      } catch (error) {
        // Non-fatal — MappingDisplay just won't have data to show.
      } finally {
        setMappingsLoading(false);
      }
    };
    loadMappings();
  }, [connectionChecked, isConnected]);

  const handleFileUpload = async (uploadedFile) => {
    setFile(uploadedFile);
    setProcessedFile(null);
    setPreviewData(null);
    setPreviewError(false);
    setProcessError(false);
    setDownloaded(false);
    setValidationReport(null);
    setValidationLoading(false);
    setStatus({ type: null, message: null });

    if (!uploadedFile) return;

    setStatus({ type: 'info', message: `Reading ${uploadedFile.name}...` });
    setPreviewLoading(true);
    try {
      const result = await previewExcelFile(uploadedFile, 10);

      if (result.success) {
        setPreviewData({
          data: result.data,
          columns: result.columns,
          totalRows: result.total_rows,
        });
        setStatus({
          type: 'success',
          message: `File loaded: ${uploadedFile.name}`,
          details: `${result.total_rows} rows, ${result.columns?.length || 0} columns`,
        });
      } else {
        setPreviewError(true);
        setStatus({ type: 'error', message: 'Failed to preview file', details: result.error });
      }
    } catch (error) {
      setPreviewError(true);
      setStatus({ type: 'error', message: 'Error previewing file', details: error.message });
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleProcess = async () => {
    const isSupported = PROCESS_OPTIONS[selectedProcess]?.status === 'active';
    if (!file || !isSupported) return;

    setProcessing(true);
    setProcessError(false);
    setProcessedFile(null);
    setDownloaded(false);
    setValidationReport(null);
    setStatus({ type: 'info', message: `Processing ${file.name}...` });

    try {
      const handler = PROCESS_HANDLERS[selectedProcess];
      const result = await handler(file);

      setProcessedFile(result);
      setStatus({
        type: 'success',
        message: 'Processing complete',
        details: `Generated ${PROCESS_OPTIONS[selectedProcess].label.toLowerCase()} load sheet with ${previewData?.totalRows || 0} rows`,
      });

      const validateFn = VALIDATE_HANDLERS[selectedProcess];

      if (!validateFn) {
        setValidationReport(null);
      } else if (result.validationErrorCount > 0 || result.skippedSheetsCount > 0) {
        setValidationLoading(true);
        try {
          const report = await validateFn(file);
          setValidationReport(report);
        } catch {
          // Validation detail fetch failing shouldn't block the user from
          // downloading the file they already successfully generated.
        } finally {
          setValidationLoading(false);
        }
      } else {
        setValidationReport({ valid: true, errors: [], skipped_sheets: [] });
      }
    } catch (error) {
      setProcessError(true);
      setStatus({ type: 'error', message: 'Processing failed', details: error.message });
    } finally {
      setProcessing(false);
    }
  };

  const handleDownloaded = (filename) => {
    setDownloaded(true);
    setStatus({ type: 'success', message: 'Download started', details: filename });
  };

  const stages = [
    {
      key: 'connect',
      label: 'Connect',
      status: !connectionChecked ? 'active' : isConnected ? 'success' : 'error',
    },
    {
      key: 'upload',
      label: 'Upload',
      status: previewLoading ? 'active' : previewError ? 'error' : previewData ? 'success' : 'pending',
    },
    {
      key: 'process',
      label: 'Process',
      status: processing ? 'active' : processError ? 'error' : processedFile ? 'success' : 'pending',
    },
    {
      key: 'download',
      label: 'Download',
      status: downloaded ? 'success' : processedFile ? 'active' : 'pending',
    },
  ];

  return (
    <>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 px-5 py-4 mb-6">
        <StageTracker stages={stages} />
      </div>

      {status.message && (
        <div className="mb-4 animate-slideDown">
          <StatusMessage type={status.type} message={status.message} details={status.details} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        <div className="lg:col-span-4 space-y-4">
          <FileUpload
            onFileUpload={handleFileUpload}
            file={file}
            disabled={processing || previewLoading}
          />

          <ProcessSelector
            selectedProcess={selectedProcess}
            onProcessChange={setSelectedProcess}
            disabled={processing}
          />

          <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6 space-y-3">
            <ProcessButton
              onClick={handleProcess}
              isProcessing={processing}
              file={file}
              selectedProcess={selectedProcess}
              isConnected={isConnected}
            />

            {processedFile && (
              <DownloadButton
                blob={processedFile.blob}
                filename={processedFile.filename}
                onDownload={handleDownloaded}
              />
            )}

            {file && isConnected && PROCESS_OPTIONS[selectedProcess]?.status === 'active' && !processing && !processedFile && (
              <div className="flex items-center justify-center gap-1.5 text-xs text-gray-500">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                Ready to process {file.name}
              </div>
            )}
          </div>

          {(validationReport || validationLoading) && (
            <ValidationReport report={validationReport} isLoading={validationLoading} />
          )}

          {processedFile && !validationLoading && !VALIDATE_HANDLERS[selectedProcess] && (
            <div className="flex items-center gap-2 text-xs text-gray-500 px-1">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
              Mandatory-field validation isn't available yet for {PROCESS_OPTIONS[selectedProcess]?.label}.
            </div>
          )}

          <MappingDisplay mappings={mappings} isLoading={mappingsLoading} />
        </div>

        <div className="lg:col-span-8 space-y-4">
          <DataPreview
            data={previewData?.data || []}
            columns={previewData?.columns || []}
            totalRows={previewData?.totalRows || 0}
            isLoading={previewLoading}
          />

          {previewData && (
            <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">File Summary</h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Total Rows</p>
                  <p className="text-lg font-semibold text-gray-800">{previewData.totalRows || 0}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Columns</p>
                  <p className="text-lg font-semibold text-gray-800">{previewData.columns?.length || 0}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">File</p>
                  <p className="text-sm font-medium text-gray-700 truncate">{file?.name || '-'}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Process</p>
                  <p className="text-sm font-medium text-gray-700">
                    {PROCESS_OPTIONS[selectedProcess]?.label ?? selectedProcess}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

      </div>
    </>
  );
}

export default MigrationTab;
