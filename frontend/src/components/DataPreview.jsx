import React, { useState } from 'react';

const DataPreview = ({ data, columns, totalRows, isLoading }) => {
  const [showAllColumns, setShowAllColumns] = useState(false);
  
  if (isLoading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
          <span className="ml-2 text-gray-600">Loading preview...</span>
        </div>
      </div>
    );
  }
  
  if (!data || data.length === 0) {
    return (
      <div className="card">
        <p className="text-gray-500 text-center py-8">
          Upload a registry file to see a preview
        </p>
      </div>
    );
  }
  
  const displayColumns = showAllColumns ? columns : columns.slice(0, 8);
  
  return (
    <div className="card">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-700">
          Data Preview
          <span className="ml-2 text-sm font-normal text-gray-500">
            ({totalRows} total rows, showing {data.length})
          </span>
        </h3>
        {columns.length > 8 && (
          <button
            onClick={() => setShowAllColumns(!showAllColumns)}
            className="text-sm text-primary-600 hover:text-primary-800"
          >
            {showAllColumns ? 'Show fewer columns' : 'Show all columns'}
          </button>
        )}
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {displayColumns.map((col, index) => (
                <th
                  key={index}
                  className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((row, rowIndex) => (
              <tr key={rowIndex} className="hover:bg-gray-50">
                {displayColumns.map((col, colIndex) => (
                  <td
                    key={colIndex}
                    className="px-4 py-2 text-sm text-gray-700 whitespace-nowrap max-w-xs truncate"
                    title={String(row[col] ?? '')}
                  >
                    {row[col] !== null && row[col] !== undefined ? String(row[col]) : ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {totalRows > data.length && (
        <p className="text-sm text-gray-500 mt-2">
          Showing first {data.length} of {totalRows} rows
        </p>
      )}
    </div>
  );
};

export default DataPreview;
