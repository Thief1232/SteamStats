import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import TerminalWindow from '../components/TerminalWindow';
import DotRow from '../components/DotRow';
import MeterRow from '../components/MeterRow';
import StatusBar from '../components/StatusBar';
import { getGameStats } from '../api/client';
import { fmtHours, fmtInt, fmtPct } from '../lib/format';
import './Profile.css';
import './Placeholder.css';

const dash = (n, format = fmtInt) => (n == null ? '—' : format(n));
// SteamSPY reports 0 playtime for games it has no playtime data for.
const playtime = (m) => (m ? `${fmtHours(m)} h` : '—');

// state.result: 'not_found' | 'error' | object (the game's stats). The state is tagged with
// the app id it belongs to, so a stale response never shows up under a different game.
export default function GameStats() {
  const navigate = useNavigate();
  const { appId } = useParams();
  const [state, setState] = useState({ appId: null, result: undefined });
  const validId = /^\d+$/.test(appId);

  useEffect(() => {
    if (!validId) return;
    let cancelled = false;
    getGameStats(Number(appId))
      .then((data) => !cancelled && setState({ appId, result: data ?? 'not_found' }))
      .catch(() => !cancelled && setState({ appId, result: 'error' }));
    return () => {
      cancelled = true;
    };
  }, [appId, validId]);

  const result = !validId ? 'not_found' : state.appId === appId ? state.result : undefined;

  if (result === undefined) {
    return (
      <div className="dash-loading">
        LOADING GAME {appId}
        <span className="blink">_</span>
      </div>
    );
  }

  if (result === 'not_found' || result === 'error') {
    return (
      <div className="soon-screen">
        <pre className="soon-log">
{`C:\\STEAMSTATS> GAME ${appId}

${result === 'not_found' ? 'SteamSPY has no data for this game.' : 'Could not load the data. Please try again.'}
`}
        </pre>
        <Link className="soon-back" to="/games">
          &gt; RETURN TO TOP_ONLINE.EXE
        </Link>
      </div>
    );
  }

  const game = result;
  const reviews = (game.positive ?? 0) + (game.negative ?? 0);
  const rating = reviews > 0 ? (game.positive / reviews) * 100 : null;
  // SteamSPY returns a valid record with zeroed stats for games it has not indexed yet
  // (usually fresh releases) — that means "no data", not "0 players".
  const hasData = game.ccu > 0 || reviews > 0 || game.owners_max > 0;

  return (
    <div className="dash">
      <div className="dash-identity">
        <div>
          <div className="dash-identity-name">{game.name}</div>
          <div className="dim" style={{ fontSize: 12 }}>
            app_id {game.app_id} ·{' '}
            <a
              href={`https://store.steampowered.com/app/${game.app_id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              store page ↗
            </a>
          </div>
        </div>
      </div>

      <div className="dash-content">
        {!hasData && (
          <TerminalWindow title="C:\STEAMSTATS\GAME.DAT">
            <div className="dim">
              SteamSPY has not collected stats for this game yet (usually the case for fresh
              releases).
            </div>
          </TerminalWindow>
        )}

        {hasData && (
          <>
            <TerminalWindow title="C:\STEAMSTATS\SUMMARY.DAT" right={<span>STEAMSPY</span>}>
              <div className="hero-grid">
                <DotRow label="Players online" value={dash(game.ccu)} />
                <DotRow
                  label="Owners (estimate)"
                  value={
                    game.owners_min == null || game.owners_max == null
                      ? '—'
                      : `${fmtInt(game.owners_min)} – ${fmtInt(game.owners_max)}`
                  }
                />
                <DotRow label="Average playtime" value={playtime(game.average_playtime_forever)} />
                <DotRow label="Median playtime" value={playtime(game.median_playtime_forever)} />
              </div>
            </TerminalWindow>

            <TerminalWindow title="C:\STEAMSTATS\REVIEWS.LOG" right={<span>{fmtInt(reviews)} REVIEWS</span>}>
              {rating === null ? (
                <div className="dim">No reviews yet.</div>
              ) : (
                <div className="list">
                  <MeterRow
                    name="POSITIVE"
                    ratio={game.positive / reviews}
                    value={`${fmtInt(game.positive)} · ${fmtPct(rating)}%`}
                  />
                  <MeterRow
                    name="NEGATIVE"
                    ratio={game.negative / reviews}
                    value={`${fmtInt(game.negative)} · ${fmtPct(100 - rating)}%`}
                  />
                </div>
              )}
            </TerminalWindow>
          </>
        )}
      </div>

      <StatusBar
        items={[
          { key: 'F5', label: 'TOP ONLINE', onClick: () => navigate('/games') },
          { key: 'F9', label: 'HOME', onClick: () => navigate('/') },
        ]}
      />
    </div>
  );
}
