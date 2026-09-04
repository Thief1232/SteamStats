import './TerminalWindow.css';

export default function TerminalWindow({ title, right, children, className = '' }) {
  return (
    <div className={`win ${className}`}>
      <div className="win-title">
        <span>{title}</span>
        {right && <span className="win-title-right">{right}</span>}
      </div>
      <div className="win-body">{children}</div>
    </div>
  );
}
