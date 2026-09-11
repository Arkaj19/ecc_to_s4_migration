// components/inventory/InventoryFileUpload.jsx
import React from 'react';
import FileUpload from '../shared/FileUpload';

export default function InventoryFileUpload({
  eccFile,
  s4File,
  onEccChange,
  onS4Change,
  onUpload,
  onReset,
  uploaded,
  uploading,
}) {
  const bothChosen = eccFile && s4File;
  const locked = uploaded || uploading;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <FileUpload
          title="ECC File"
          dropText="your ECC inventory file"
          supportedHint="Supports .csv, .xlsx and .xls files"
          acceptedExtensions={['.csv', '.xlsx', '.xls']}
          file={eccFile}
          onFileUpload={onEccChange}
          disabled={locked}
        />
        <FileUpload
          title="S4 File"
          dropText="your S4 inventory file"
          supportedHint="Supports .csv, .xlsx and .xls files"
          acceptedExtensions={['.csv', '.xlsx', '.xls']}
          file={s4File}
          onFileUpload={onS4Change}
          disabled={locked}
        />
      </div>

      <div className="flex gap-3">
        <button
          onClick={onUpload}
          disabled={!bothChosen || locked}
          className="px-5 py-2 rounded-md bg-slate-700 text-white font-medium
                     hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-colors"
        >
          {uploading ? 'Uploading…' : uploaded ? 'Uploaded ✓' : 'Upload Files'}
        </button>

        {(eccFile || s4File || uploaded) && (
          <button
            onClick={onReset}
            disabled={uploading}
            className="px-5 py-2 rounded-md border border-gray-300 text-gray-700
                       hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  );
}