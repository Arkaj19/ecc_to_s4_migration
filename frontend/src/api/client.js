import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create a dedicated client for file uploads with longer timeout
const fileUploadClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 600000, // 10 minutes for large files (was 300000/5 minutes)
});

// Keep the original client for quick JSON requests
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds for quick requests
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
 * Now uses fileUploadClient with 10-minute timeout and progress tracking
 */
const postForFile = async (endpoint, file, extraFields = {}, fallbackFilename = 'output.xlsx') => {
  const formData = new FormData();
  formData.append('file', file);
  Object.entries(extraFields).forEach(([key, value]) => {
    if (value !== null && value !== undefined) formData.append(key, value);
  });

  try {
    const response = await fileUploadClient.post(endpoint, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob',
      // Track upload progress
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          console.log(`${endpoint} upload progress: ${percentCompleted}%`);
        }
      },
    });

    const contentType = response.headers['content-type'] || response.data?.type || '';

    if (contentType.includes('application/json')) {
      const text = await response.data.text();
      const payload = JSON.parse(text);
      return { reviewRequired: true, payload };
    }

    const disposition = response.headers['content-disposition'] || '';
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : fallbackFilename;
    const validationErrorCount = parseInt(response.headers['x-validation-error-count'] || '0', 10);
    const skippedSheetsCount = parseInt(response.headers['x-skipped-sheets-count'] || '0', 10);
    const currencyReview = {
      status: response.headers['x-currency-review-status'] || null,
      action: response.headers['x-currency-action'] || null,
      mismatchCount: parseInt(response.headers['x-currency-mismatch-count'] || '0', 10),
      dumpRows: parseInt(response.headers['x-currency-dump-rows'] || '0', 10),
      retainedRows: parseInt(response.headers['x-currency-retained-rows'] || '0', 10),
    };

    return {
      reviewRequired: false,
      blob: response.data,
      filename,
      validationErrorCount,
      skippedSheetsCount,
      currencyReview,
    };
  } catch (error) {
    // Handle timeout specifically
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      console.error(`${endpoint} timed out:`, error);
      throw new Error(
        `Processing timed out. Your file (${Math.round(file.size / 1024 / 1024)}MB) is taking too long. Please try again or contact support.`
      );
    }

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
 * Shared by every /validate-* route. These return a plain JSON report
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
export const processAssetFile = (file, mappingOverrides = null) => {
  const extraFields = mappingOverrides ? { mappings_json: JSON.stringify(mappingOverrides) } : {};
  return postForFile('/process-asset', file, extraFields, 'assets_load_template_filled.xlsx');
};

// Process the credit registry — POST /process-credit
export const processCreditFile = (file) => {
  return postForFile('/process-credit', file, {}, 'credit_data_load_filled.xlsx');
};

// Process the AP registry — POST /process-ap
// export const processApFile = (file) => {
//   return postForFile('/process-ap', file, {}, 'AP_Data_Load_SIT2_filled.xlsx');
// };
// Process the AP registry — POST /process-ap
export const processApFile = (file, currencyAction = null) => {
  const extraFields = currencyAction ? { currency_action: currencyAction } : {};
  return postForFile('/process-ap', file, extraFields, 'AP_Data_Load_SIT2_filled.xlsx');
};

// Process the AR registry — POST /process-ar
export const processArFile = (file, currencyAction = null) => {
  const extraFields = currencyAction ? { currency_action: currencyAction } : {};
  return postForFile('/process-ar', file, extraFields, 'ar_data_load_filled.xlsx');
};

// Detailed mandatory-field validation reports
export const validateAssetFile = (file, mappingOverrides = null) => {
  const extraFields = mappingOverrides ? { mappings_json: JSON.stringify(mappingOverrides) } : {};
  return postForJson('/validate-asset', file, extraFields);
};

export const validateCreditFile = (file) => postForJson('/validate-credit', file);
export const validateApFile = (file) => postForJson('/validate-ap', file);

// Data Validation tab — compares an original ECC AR registry against the already-migrated S/4 output file
export const validateArMigration = async (eccRegistryFile, s4FilledFile) => {
  const formData = new FormData();
  formData.append('registry_file', eccRegistryFile);
  formData.append('filled_file', s4FilledFile);

  try {
    const response = await fileUploadClient.post('/validate-ar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    console.error('/validate-ar (migration comparison) failed:', detail || error);
    throw new Error(detail || 'AR validation failed.');
  }
};

// Data Validation tab — compares an ECC AP registry against the already-migrated S/4 output file
export const validateApReconciliation = async (eccRegistryFile, s4FilledFile) => {
  const formData = new FormData();
  formData.append('registry_file', eccRegistryFile);
  formData.append('filled_file', s4FilledFile);

  try {
    const response = await fileUploadClient.post('/validate-ap-reconciliation', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    console.error('/validate-ap-reconciliation failed:', detail || error);
    throw new Error(detail || 'AP validation failed.');
  }
};

// Data Validation tab — compares an ECC Credit registry against the already-migrated S/4 output file
export const validateCreditReconciliation = async (eccRegistryFile, s4FilledFile) => {
  const formData = new FormData();
  formData.append('registry_file', eccRegistryFile);
  formData.append('filled_file', s4FilledFile);

  try {
    const response = await fileUploadClient.post('/validate-credit-reconciliation', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    console.error('/validate-credit-reconciliation failed:', detail || error);
    throw new Error(detail || 'Credit validation failed.');
  }
};

// Inventory — upload ECC + S4 files, returns { session_id } used for validation
// Router: POST /api/inventory/upload
export const uploadInventoryFiles = async (eccFile, s4File) => {
  const formData = new FormData();
  formData.append('ecc_file', eccFile);
  formData.append('s4_file', s4File);

  try {
    const response = await fileUploadClient.post('/api/inventory/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    console.error('/api/inventory/upload failed:', detail || error);
    throw new Error(detail || 'Inventory file upload failed.');
  }
};

// Inventory — sample & validate common rows for a previously-uploaded session
// Router: POST /api/inventory/validate/{session_id}?sample_size=
export const validateInventory = async (sessionId, sampleSize = 50) => {
  try {
    const response = await apiClient.post(
      `/api/inventory/validate/${sessionId}`,
      null,
      { params: { sample_size: sampleSize } }
    );
    return response.data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    console.error('/api/inventory/validate failed:', detail || error);
    throw new Error(detail || 'Inventory validation failed.');
  }
};

// Inventory — download the full comparison result for a given download_id
// Router: GET /api/inventory/download/{download_id}
export async function downloadInventoryResults(downloadId) {
  const response = await fetch(`${API_BASE_URL}/api/inventory/download/${downloadId}`, {
    method: 'GET',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || 'Failed to download inventory results.');
  }

  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : 'ecc_s4_50_sample.xlsx';

  return { blob, filename };
}

export async function downloadArCurrencyDump() {
  const response = await fetch(`${API_BASE_URL}/download-ar-currency-dump`, {
    method: 'GET',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || 'Failed to download deleted records file');
  }

  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : 'AR_Currency_Mismatch_Deleted.xlsx';

  return { blob, filename };
}

export default apiClient;