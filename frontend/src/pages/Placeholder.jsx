import { useParams, Link } from 'react-router-dom';
import './Placeholder.css';

const NAMES = {
  help: 'HELP.EXE',
  wrapped: 'WRAPPED.EXE',
  leaderboard: 'LEADERBOARD.EXE',
  wishlist: 'WISHLIST.EXE',
};

export default function Placeholder() {
  const { feature } = useParams();
  const name = NAMES[feature] || `${(feature || 'MODULE').toUpperCase()}.EXE`;

  return (
    <div className="soon-screen">
      <pre className="soon-log">
{`C:\\STEAMSTATS> RUN ${name}

Bad command or file name.
Модуль ещё не скомпилирован оператором.
`}
      </pre>
      <Link className="soon-back" to="/dashboard">
        &gt; RETURN TO DASHBOARD.EXE
      </Link>
    </div>
  );
}
