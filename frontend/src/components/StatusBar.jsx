import './StatusBar.css';

export default function StatusBar({ items }) {
  return (
    <div className="statusbar">
      {items.map((item) => (
        <button
          key={item.key}
          className="statusbar-item"
          onClick={item.onClick}
          disabled={!item.onClick}
        >
          <span className="statusbar-key">{item.key}</span>
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  );
}
