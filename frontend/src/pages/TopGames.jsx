import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import TerminalWindow from '../components/TerminalWindow';
import MeterRow from '../components/MeterRow';
import StatusBar from '../components/StatusBar';
import { getTopGames, getGameStats, searchGames } from '../api/client';
import { fmtInt, fmtPct } from '../lib/format';
import './Home.css';
import './Profile.css';
import './TopGames.css';

const DISPLAY_LIMIT = 30;

function ratingOf(g) {
  const total = g.positive + g.negative;
  return total > 0 ? (g.positive / total) * 100 : null;
}

// undefined = loading, 'loading' = lookup in flight, 'not_found', object = found
export default function TopGames() {
  const navigate = useNavigate();
  const [games, setGames] = useState(undefined);
  const [query, setQuery] = useState('');
  const [lookup, setLookup] = useState(undefined);
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
      setLookupError('Введите название игры или app_id.');
      return;
    }
    setLookupError('');
    setSuggestions(null);
    setLookup(undefined);

    if (/^\d+$/.test(term)) {
      setLookup('loading');
      const data = await getGameStats(Number(term)).catch(() => null);
      setLookup(data ?? 'not_found');
      return;
    }

    const results = await searchGames(term).catch(() => []);
    if (results.length === 1) {
      handlePick(results[0].app_id);
    } else {
      setSuggestions(results);
    }
  }

  async function handlePick(appId) {
    setSuggestions(null);
    setLookup('loading');
    const data = await getGameStats(appId).catch(() => null);
    setLookup(data ?? 'not_found');
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
              placeholder="LOOKUP <название игры или app_id>, например team fortress"
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
              Ничего не нашлось в Steam по такому названию.
            </div>
          )}
          {suggestions !== null && suggestions.length > 0 && (
            <div className="list" style={{ marginTop: 10 }}>
              {suggestions.map((s) => (
                <button key={s.app_id} className="suggestion-row" onClick={() => handlePick(s.app_id)}>
                  {s.name} <span className="dim">· {s.app_id}</span>
                </button>
              ))}
            </div>
          )}
          {lookup === 'loading' && (
            <div className="dim" style={{ marginTop: 10 }}>
              ищу…
            </div>
          )}
          {lookup === 'not_found' && (
            <div className="dim" style={{ marginTop: 10 }}>
              У SteamSPY нет данных по этой игре.
            </div>
          )}
          {lookup && typeof lookup === 'object' && lookup.ccu === 0 && ratingOf(lookup) === null && (
            <div className="dim" style={{ marginTop: 10 }}>
              {lookup.name}: SteamSPY пока не собрал по этой игре статистику (обычно так у свежих релизов).
            </div>
          )}
          {lookup && typeof lookup === 'object' && (lookup.ccu > 0 || ratingOf(lookup) !== null) && (
            <div className="list" style={{ marginTop: 10 }}>
              <MeterRow
                name={lookup.name}
                ratio={lookup.positive + lookup.negative > 0 ? lookup.positive / (lookup.positive + lookup.negative) : 0}
                value={`${fmtInt(lookup.ccu)} онлайн${ratingOf(lookup) !== null ? ` · ${fmtPct(ratingOf(lookup))}%` : ''}`}
              />
            </div>
          )}
        </TerminalWindow>

        <TerminalWindow title="C:\STEAMSTATS\TOP_ONLINE.LOG" right={<span>STEAMSPY · ТОП {topGames.length}</span>}>
          {games === undefined && (
            <div className="dim">
              LOADING TOP_ONLINE.LOG<span className="blink">_</span>
            </div>
          )}
          {games === 'error' && <div className="dim">Не удалось загрузить список. Попробуйте позже.</div>}
          {topGames.length > 0 && (
            <div className="list">
              {topGames.map((g, i) => (
                <MeterRow
                  key={g.app_id}
                  rank={i + 1}
                  name={g.name}
                  ratio={g.ratio}
                  value={`${fmtInt(g.ccu)} онлайн${g.rating !== null ? ` · ${fmtPct(g.rating)}%` : ''}`}
                />
              ))}
            </div>
          )}
        </TerminalWindow>
      </div>

      <StatusBar items={[{ key: 'F9', label: 'HOME', onClick: () => navigate('/') }]} />
    </div>
  );
}
