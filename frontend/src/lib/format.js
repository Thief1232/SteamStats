export function hoursFromMinutes(minutes) {
  return minutes / 60;
}

export function fmtHours(minutes) {
  return (minutes / 60).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

export function fmtInt(n) {
  return n.toLocaleString('en-US');
}

export function fmtNum(n, decimals = 1) {
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function fmtPct(n) {
  return n.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

export function fmtDate(unixSeconds) {
  if (!unixSeconds) return '—';
  return new Date(unixSeconds * 1000).toLocaleDateString('en-US', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}
