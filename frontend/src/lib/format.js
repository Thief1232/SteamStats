export function hoursFromMinutes(minutes) {
  return minutes / 60;
}

export function fmtHours(minutes) {
  return (minutes / 60).toLocaleString('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

export function fmtInt(n) {
  return n.toLocaleString('ru-RU');
}

export function fmtNum(n, decimals = 1) {
  return n.toLocaleString('ru-RU', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function fmtPct(n) {
  return n.toLocaleString('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

export function fmtDate(unixSeconds) {
  if (!unixSeconds) return '—';
  return new Date(unixSeconds * 1000).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}
