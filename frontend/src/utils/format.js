export const formatNumber = value => value == null ? '—' : Number(value).toLocaleString();
export const percentage = (numerator, denominator) => denominator ? Math.round(numerator / denominator * 100) : 0;
export const formatDate = value => value ? new Date(value).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Not recorded';
