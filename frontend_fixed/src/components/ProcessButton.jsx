import React from 'react';
import { ClipLoader } from 'react-spinners';

const ProcessButton = ({ onClick, isProcessing, file, selectedProcess, isConnected }) => {
  const disabled = !file || isProcessing || !isConnected || selectedProcess !== 'ASSETS';

  const label = () => {
    if (isProcessing) return 'Processing...';
    if (!isConnected) return 'Backend not connected';
    if (!file) return 'Upload a file first';
    if (selectedProcess !== 'ASSETS') return `${selectedProcess} coming soon`;
    return 'Process File';
  };

  return (
    <button onClick={onClick} disabled={disabled} className="w-full btn-primary py-3 text-lg">
      {isProcessing ? (
        <span className="flex items-center justify-center gap-2">
          <ClipLoader size={20} color="#ffffff" />
          Processing...
        </span>
      ) : (
        label()
      )}
    </button>
  );
};

export default ProcessButton;
