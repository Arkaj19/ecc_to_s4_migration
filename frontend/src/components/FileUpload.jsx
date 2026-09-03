import React, { useCallback, useRef, useState } from 'react';
import { formatFileSize } from '../utils/helpers';

const ACCEPTED_EXTENSIONS = ['.xlsx', '.xls'];

const isAcceptedFile = (filename) =>
  ACCEPTED_EXTENSIONS.some((ext) => filename.toLowerCase().endsWith(ext));

/**
 * FileUpload — pure, controlled file picker.
 *
 * It only ever does two things: let the user choose a file (via click or
 * drag-and-drop), and report that choice up through `onFileUpload`.
 * It does not call the API and does not know about preview/process state —
 * that all lives in App.jsx via api/client.js, so there's exactly one place
 * that talks to the backend.
 */
const FileUpload = ({ onFileUpload, file, disabled, title = 'Upload Registry File', dropText = 'your registry file' }) => {
  const inputRef = useRef(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [rejection, setRejection] = useState(null);

  const selectFile = useCallback((selected) => {
    if (!selected) return;
    if (!isAcceptedFile(selected.name)) {
      setRejection(`"${selected.name}" isn't a .xlsx or .xls file.`);
      return;
    }
    setRejection(null);
    onFileUpload(selected);
  }, [onFileUpload]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragActive(false);
    if (disabled) return;
    selectFile(e.dataTransfer.files?.[0]);
  }, [disabled, selectFile]);

  const handleRemove = () => {
    setRejection(null);
    onFileUpload(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-700">{title}</h3>
        {file && (
          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
            File loaded
          </span>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls"
        disabled={disabled}
        onChange={(e) => selectFile(e.target.files?.[0])}
        className="hidden"
      />

      <div
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setIsDragActive(true); }}
        onDragLeave={() => setIsDragActive(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && !file && inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200
          ${!file ? 'cursor-pointer' : ''}
          ${isDragActive ? 'border-blue-500 bg-blue-50 shadow-inner' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'}
          ${file ? 'border-green-400 bg-green-50/50' : ''}
          ${disabled ? 'opacity-60 cursor-not-allowed' : ''}`}
      >
        {file ? (
          <div className="flex items-center justify-center gap-4">
            <div className="shrink-0 w-11 h-11 rounded-lg bg-green-100 flex items-center justify-center">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M14 2v6h6" />
              </svg>
            </div>
            <div className="text-left min-w-0">
              <p className="font-semibold text-gray-800 truncate max-w-[220px] sm:max-w-[320px]">
                {file.name}
              </p>
              <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); handleRemove(); }}
              disabled={disabled}
              title="Remove file"
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ) : (
          <div>
            <div className="flex justify-center mb-3">
              <div className="p-3 bg-blue-50 rounded-full">
                <svg className="w-10 h-10 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              {isDragActive ? 'Drop your file here...' : `Drag & drop ${dropText}, or click to browse`}
            </p>
            <p className="text-xs text-gray-400 mt-2">Supports .xlsx and .xls files</p>
          </div>
        )}
      </div>

      {!file && (
        <button
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          className="mt-4 w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
                     transition-colors font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Browse Files
        </button>
      )}

      {rejection && (
        <p className="mt-3 text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg p-2">
          {rejection}
        </p>
      )}
    </div>
  );
};

export default FileUpload;
