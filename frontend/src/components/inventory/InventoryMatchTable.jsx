import React from 'react';

export default function InventoryMatchTable({ rows, columns }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="p-6 text-sm text-gray-500 text-center">
        No rows to display.
      </div>
    );
  }

  return (
    <table className="min-w-full text-xs">
      <thead className="sticky top-0 bg-gray-100 z-10">
        <tr>
          {/* Row number column — helps line up the two panes visually */}
          <th className="border-b border-r border-gray-200 px-2 py-1.5 text-gray-500 font-medium text-right w-10">
            #
          </th>
          {columns.map((c) => (
            <th
              key={c}
              className="border-b border-gray-200 px-2 py-1.5 text-left font-semibold text-gray-700 whitespace-nowrap"
            >
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr
            key={i}
            className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
          >
            <td className="border-b border-r border-gray-100 px-2 py-1 text-right text-gray-400 font-mono">
              {i + 1}
            </td>
            {columns.map((c) => (
              <td
                key={c}
                className="border-b border-gray-100 px-2 py-1 text-gray-800 whitespace-nowrap"
                title={row[c] ?? ''}
              >
                {row[c] ?? ''}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}