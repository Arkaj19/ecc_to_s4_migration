import * as XLSX from 'xlsx';

/**
 * previewExcelFile — reads the first `nRows` of a spreadsheet entirely in
 * the browser and returns the same shape the old backend /preview endpoint
 * used to: { success, columns, data, total_rows }.
 *
 * The backend no longer has a /preview route (the new API only exposes
 * /health, /default-mappings, /process-asset), so there's nothing to call
 * for a preview anymore. Doing it client-side means the user still sees
 * their data before committing to a full process/download round trip, and
 * it's actually faster since it never touches the network.
 */
export const previewExcelFile = (file, nRows = 10) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const workbook = XLSX.read(e.target.result, { type: 'array', cellDates: true });
        const firstSheetName = workbook.SheetNames[0];
        const sheet = workbook.Sheets[firstSheetName];

        // Array-of-arrays first so we can pull the header row out explicitly,
        // even if some header cells are blank.
        const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false, defval: '' });

        if (!rows.length) {
          resolve({ success: true, columns: [], data: [], total_rows: 0 });
          return;
        }

        const columns = rows[0].map((c, i) => (c === '' ? `Column ${i + 1}` : String(c)));
        const bodyRows = rows.slice(1);

        const data = bodyRows.slice(0, nRows).map((row) => {
          const obj = {};
          columns.forEach((col, i) => { obj[col] = row[i] ?? ''; });
          return obj;
        });

        resolve({
          success: true,
          columns,
          data,
          total_rows: bodyRows.length,
        });
      } catch (err) {
        reject(new Error(`Could not read this spreadsheet: ${err.message}`));
      }
    };

    reader.onerror = () => reject(new Error('Failed to read the file.'));
    reader.readAsArrayBuffer(file);
  });
};
