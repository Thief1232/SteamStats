import Meter from './Meter';
import './MeterRow.css';

export default function MeterRow({ rank, name, ratio, value, meterWidth = 20 }) {
  return (
    <div className="meterrow">
      {rank != null && <span className="meterrow-rank faint">{String(rank).padStart(2, '0')}</span>}
      <span className="meterrow-name" title={name}>
        {name}
      </span>
      <span className="meterrow-meter">
        <Meter ratio={ratio} width={meterWidth} />
      </span>
      <span className="meterrow-value mono-num dim">{value}</span>
    </div>
  );
}
