import React from 'react';

/**
 * DownloadButton owns the object-URL lifecycle itself (create on click,
 * revoke right after) instead of App.jsx managing a `url` string in state —
 * one less piece of shared state to keep in sync.
 */
const DownloadButton = ({ blob, filename, onDownload }) => {
  const handleDownload = () => {
    if (!blob) return;
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    onDownload?.(filename);
  };

  return (
    <button
      onClick={handleDownload}
      className="w-full btn-primary py-3 text-lg bg-green-600 hover:bg-green-700"
    >
      Download S/4 Load Sheet
    </button>
  );
};

export default DownloadButton;
