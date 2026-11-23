import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import TerminalWindow from '../components/TerminalWindow';
import MeterRow from '../components/MeterRow';
import StatusBar from '../components/StatusBar';
import { getTopGames, searchGames } from '../api/client';
import { fmtInt, fmtPct } from '../lib/format';
import './Home.css';
import './Profile.css';
import './TopGames.css';

const DISPLAY_LIMIT = 30;

function ratingOf(g) {
  const total = g.positive + g.negative;
  return total > 0 ? (g.positive / total) * 100 : null;
}

// games: undefined = loading, 'error' = failed, array = loaded
export default function TopGames() {
  const navigate = useNavigate();
  const [games, setGames] = useState(undefined);
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [lookupError, setLookupError] = useState('');
  const [suggestions, setSuggestions] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getTopGames()
      .then((data) => !cancelled && setGames(data))
      .catch(() => !cancelled && setGames('error'));
    return () => {
      cancelled = true;
    };
  }, []);

  const topGames = useMemo(() => {
    if (!Array.isArray(games)) return [];
    const sorted = [...games].sort((a, b) => b.ccu - a.ccu).slice(0, DISPLAY_LIMIT);
    const maxCcu = Math.max(...sorted.map((g) => g.ccu), 1);
    return sorted.map((g) => ({ ...g, ratio: g.ccu / maxCcu, rating: ratingOf(g) }));
  }, [games]);

  async function handleLookup(e) {
    e.preventDefault();
    const term = query.trim();
    if (!term) {
      setLookupError('Enter a game name or app_id.');
      return;
    }
    setLookupError('');
    setSuggestions(null);

    if (/^\d+$/.test(term)) {
      navigate(`/games/${term}`);
      return;
    }

    setSearching(true);
    const results = await searchGames(term).catch(() => []);
    setSearching(false);
    if (results.length === 1) {
      navigate(`/games/${results[0].app_id}`);
    } else {
      setSuggestions(results);
    }
  }

  return (
    <div className="dash">
      <div className="dash-content">
        <TerminalWindow title="C:\STEAMSTATS\GAME_LOOKUP.EXE">
          <form className="lookup-form" onSubmit={handleLookup}>
            <span className="lookup-prompt">C:\STEAMSTATS&gt;</span>
            <input
              className="lookup-input"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (lookupError) setLookupError('');
              }}
              placeholder="LOOKUP <game name or app_id>, e.g. team fortress"
              spellCheck={false}
            />
          </form>

          {lookupError && (
            <div className="dim" style={{ marginTop: 10 }}>
              {lookupError}
            </div>
          )}
          {suggestions !== null && suggestions.length === 0 && (
            <div className="dim" style={{ marginTop: 10 }}>
              Nothing found in Steam for that name.
            </div>
          )}
          {suggestions !== null && suggestions.length > 0 && (
            <div className="list" style={{ marginTop: 10 }}>
              {suggestions.map((s) => (
                <button key={s.app_id} className="suggestion-row" onClick={() => navigate(`/games/${s.app_id}`)}>
                  {s.name} <span className="dim">· {s.app_id}</span>
                </button>
              ))}
            </div>
          )}
          {searching && (
            <div className="dim" style={{ marginTop: 10 }}>
              searching…
            </div>
          )}
        </TerminalWindow>

        <TerminalWindow title="C:\STEAMSTATS\TOP_ONLINE.LOG" right={<span>STEAMSPY · TOP {topGames.length}</span>}>
          {games === undefined && (
            <div className="dim">
              LOADING TOP_ONLINE.LOG<span className="blink">_</span>
            </div>
          )}
          {games === 'error' && <div className="dim">Could not load the list. Please try again later.</div>}
          {topGames.length > 0 && (
            <div className="list">
              {topGames.map((g, i) => (
                <Link key={g.app_id} className="row-link" to={`/games/${g.app_id}`}>
                  <MeterRow
                    rank={i + 1}
                    name={g.name}
                    ratio={g.ratio}
                    value={`${fmtInt(g.ccu)} online${g.rating !== null ? ` · ${fmtPct(g.rating)}%` : ''}`}
                  />
                </Link>
              ))}
            </div>
          )}
        </TerminalWindow>
      </div>

      <StatusBar items={[{ key: 'F9', label: 'HOME', onClick: () => navigate('/') }]} />
    </div>
  );
}
