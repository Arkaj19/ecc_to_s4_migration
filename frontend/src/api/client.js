import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutes for large files
});

// Health check — GET /health
export const checkHealth = async () => {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
};

// Default ECC → S/4 mappings — GET /default-mappings
// Shape: { cocd: [{ecc_cocd, s4_cocd}], plant_loc: [{ecc_plant, ecc_location,
// s4_plant, s4_location}], cost_center: [{ecc_cost_center, s4_cost_center}] }
export const getDefaultMappings = async () => {
  try {
    const response = await apiClient.get('/default-mappings');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch default mappings:', error);
    throw error;
  }
};

/**
 * Shared by every "upload a registry, get a populated template back" route
 * (/process-asset, /process-credit, /process-ap). Resolves to
 * { blob, filename, validationErrorCount }:
 *   - filename comes from the server's Content-Disposition header rather
 *     than being guessed on the frontend, since each route names its
 *     output differently.
 *   - validationErrorCount comes from X-Validation-Error-Count — the file
 *     is always generated even when some mandatory fields are missing, so
 *     this is how the caller knows whether to also fetch the detailed
 *     report from the matching /validate-* route.
 */
const postForFile = async (endpoint, file, extraFields = {}, fallbackFilename = 'output.xlsx') => {
  const formData = new FormData();
  formData.append('file', file);
  Object.entries(extraFields).forEach(([key, value]) => {
    if (value !== null && value !== undefined) formData.append(key, value);
  });

  try {
    const response = await apiClient.post(endpoint, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob',
    });

    const disposition = response.headers['content-disposition'] || '';
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : fallbackFilename;
    const validationErrorCount = parseInt(response.headers['x-validation-error-count'] || '0', 10);
    const skippedSheetsCount = parseInt(response.headers['x-skipped-sheets-count'] || '0', 10);

    return { blob: response.data, filename, validationErrorCount, skippedSheetsCount };
  } catch (error) {
    // With responseType: 'blob', a FastAPI error response (400/500 JSON)
    // arrives as a Blob too, so error.message is useless on its own —
    // read the blob back out as text to get the real `detail` message.
    if (error.response?.data instanceof Blob) {
      let detail = null;
      try {
        const text = await error.response.data.text();
        detail = JSON.parse(text)?.detail;
      } catch {
        // response wasn't JSON — ignore and fall through to generic error
      }
      if (detail) {
        console.error(`${endpoint} failed:`, detail);
        throw new Error(detail);
      }
    }
    console.error(`${endpoint} failed:`, error);
    throw error;
  }
};

/**
 * Shared by every /validate-* route. These return a plain JSON report —
 * { valid, errors: [{sheet, column, missing_rows, message}] } — rather
 * than a file, so error handling is simpler than postForFile: axios
 * already parses a FastAPI error body normally since responseType stays
 * the default 'json'.
 */
const postForJson = async (endpoint, file, extraFields = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  Object.entries(extraFields).forEach(([key, value]) => {
    if (value !== null && value !== undefined) formData.append(key, value);
  });

  try {
    const response = await apiClient.post(endpoint, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    console.error(`${endpoint} failed:`, detail || error);
    throw new Error(detail || 'Validation check failed.');
  }
};

// Process the asset registry — POST /process-asset
// `mappingOverrides`, if provided, is sent as the `mappings_json` field in
// the same shape /default-mappings returns, and the backend merges it over
// the built-in mapping tables for this run only.
export const processAssetFile = (file, mappingOverrides = null) => {
  const extraFields = mappingOverrides ? { mappings_json: JSON.stringify(mappingOverrides) } : {};
  return postForFile('/process-asset', file, extraFields, 'assets_load_template_filled.xlsx');
};

// Process the credit registry — POST /process-credit
// No mapping overrides supported on this route — the backend hardcodes the
// Profile/Segment field mapping for now.
export const processCreditFile = (file) => {
  return postForFile('/process-credit', file, {}, 'credit_data_load_filled.xlsx');
};

// Process the AP registry — POST /process-ap
// No mapping overrides supported on this route either — Payment Terms,
// Company Code, and Tax Code are all mapped internally on the backend.
export const processApFile = (file) => {
  return postForFile('/process-ap', file, {}, 'AP_Data_Load_SIT2_filled.xlsx');
};

// Process the AR registry — POST /process-ar
export const processArFile = (file) => {
  return postForFile('/process-ar', file, {}, 'ar_data_load_filled.xlsx');
};

// Detailed mandatory-field validation for AR — POST /validate-ar
// Note: the backend only detects gaps when the AR template uses the
// standard Row 5 technical-header layout; if it falls back to Row 1
// headers, this will correctly report valid:true for a template it
// isn't actually able to check yet (see ar_processor.py).
export const validateArFile = (file) => postForJson('/validate-ar', file);

// Detailed mandatory-field validation reports — same underlying mapping
// logic as the matching /process-* route, but returns the report instead
// of the file. Only worth calling when processFile's validationErrorCount
// came back > 0.
export const validateAssetFile = (file, mappingOverrides = null) => {
  const extraFields = mappingOverrides ? { mappings_json: JSON.stringify(mappingOverrides) } : {};
  return postForJson('/validate-asset', file, extraFields);
};

export const validateCreditFile = (file) => postForJson('/validate-credit', file);

export const validateApFile = (file) => postForJson('/validate-ap', file);

export default apiClient;
