import React from 'react';
import InventoryMatchTable from './InventoryMatchTable';

export default function InventoryMatchPanes({
  eccRows,
  eccColumns,
  s4Rows,
  s4Columns,
}) {
  return (
    <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* ECC pane */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50 rounded-t-lg">
          <h3 className="font-semibold text-gray-800">ECC — 50 samples</h3>
          <span className="text-xs text-gray-500">{eccRows?.length ?? 0} rows</span>
        </div>
        <div className="overflow-auto max-h-[70vh]">
          <InventoryMatchTable rows={eccRows} columns={eccColumns} />
        </div>
      </div>

      {/* S4 pane */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50 rounded-t-lg">
          <h3 className="font-semibold text-gray-800">S4 — 50 samples</h3>
          <span className="text-xs text-gray-500">{s4Rows?.length ?? 0} rows</span>
        </div>
        <div className="overflow-auto max-h-[70vh]">
          <InventoryMatchTable rows={s4Rows} columns={s4Columns} />
        </div>
      </div>
    </section>
  );
}