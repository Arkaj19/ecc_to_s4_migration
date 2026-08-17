/**
 * Format file size for display, e.g. 482816 -> "471.5 KB".
 * The only helper in this module that's actually used anywhere in the app —
 * the rest (truncateText, getFileExtension, isExcelFile, formatDate) were
 * dead exports with no callers and have been removed.
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};
