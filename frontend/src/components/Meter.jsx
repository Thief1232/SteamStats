const FULL = '█';
const EMPTY = '░';

export default function Meter({ ratio, width = 20 }) {
  const clamped = Math.max(0, Math.min(1, ratio));
  const filled = Math.max(clamped > 0 ? 1 : 0, Math.round(clamped * width));
  const empty = Math.max(0, width - filled);
  return (
    <span className="meter mono-num" aria-hidden="true">
      {FULL.repeat(filled)}
      <span className="faint">{EMPTY.repeat(empty)}</span>
    </span>
  );
}
