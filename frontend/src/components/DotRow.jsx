import './DotRow.css';

export default function DotRow({ label, value, children }) {
  return (
    <div className="dotrow">
      <span className="dotrow-label">{label}</span>
      <span className="dotrow-leader" />
      <span className="dotrow-value mono-num">{children ?? value}</span>
    </div>
  );
}
