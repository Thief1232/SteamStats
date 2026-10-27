import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import TerminalWindow from '../components/TerminalWindow';
import DotRow from '../components/DotRow';
import MeterRow from '../components/MeterRow';
import StatusBar from '../components/StatusBar';
import {
  getUser,
  getUserLibrary,
  refreshLibraryAchievements,
  getAchievementsProgress,
  getGameStats,
} from '../api/client';
import { fmtHours, fmtInt, fmtPct, fmtNum, fmtDate } from '../lib/format';
import './Profile.css';
import './Placeholder.css';

const PACMAN_WIDTH = 24;

function pacmanBar(done, total) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const filled = total > 0 ? Math.round((done / total) * PACMAN_WIDTH) : 0;
  const bar = '#'.repeat(filled) + '-'.repeat(PACMAN_WIDTH - filled);
  return `[${bar}] ${pct}% (${done}/${total})`;
}

const BUCKETS = [
  { label: '0 H (NEVER)', test: (h) => h === 0 },
  { label: '< 1 H', test: (h) => h > 0 && h < 1 },
  { label: '1–10 H', test: (h) => h >= 1 && h < 10 },
  { label: '10–50 H', test: (h) => h >= 10 && h < 50 },
  { label: '50–100 H', test: (h) => h >= 50 && h < 100 },
  { label: '100 H+', test: (h) => h >= 100 },
];

// undefined = loading, 'not_found' | 'private' | 'error' = failure state, object = loaded
// library: undefined = loading, 'private' | 'empty' | 'error' = no stats to show, object = loaded
export default function Profile() {
  const navigate = useNavigate();
  const { lookup } = useParams();
  const [user, setUser] = useState(undefined);
  const [library, setLibrary] = useState(undefined);
  const [achLoading, setAchLoading] = useState(false);
  const [achError, setAchError] = useState(false);
  const [achProgress, setAchProgress] = useState(null);
  const [gameStats, setGameStats] = useState({});

  useEffect(() => {
    let cancelled = false;
    setUser(undefined);
    setLibrary(undefined);
    setAchLoading(false);
    setAchError(false);
    setAchProgress(null);
    setGameStats({});

    getUser(lookup)
      .then((u) => {
        if (cancelled) return;
        setUser(u);
        if (u.visibility === 'private') {
          setLibrary('private');
          return;
        }
        getUserLibrary(u.steam_id)
          .then((lib) => !cancelled && setLibrary(lib.games.length > 0 ? lib : 'empty'))
          .catch((err) => !cancelled && setLibrary(err.status === 403 ? 'private' : 'error'));
      })
      .catch((err) => !cancelled && setUser(err.status === 404 ? 'not_found' : 'error'));

    return () => {
      cancelled = true;
    };
  }, [lookup]);

  // SteamSPY data is shared by all players — load it for the 12 most played games,
  // not the whole library, to avoid piling up requests to steamspy-service.
  useEffect(() => {
    if (!library || typeof library !== 'object') return;
    let cancelled = false;

    const topAppIds = [...library.games]
      .sort((a, b) => b.playtime_minutes - a.playtime_minutes)
      .slice(0, 12)
      .map((g) => g.app_id);

    Promise.allSettled(topAppIds.map((id) => getGameStats(id))).then((results) => {
      if (cancelled) return;
      const next = {};
      results.forEach((r, i) => {
        if (r.status === 'fulfilled' && r.value) next[topAppIds[i]] = r.value;
      });
      setGameStats(next);
    });

    return () => {
      cancelled = true;
    };
  }, [library]);

  async function handleLoadAchievements() {
    setAchLoading(true);
    setAchError(false);
    setAchProgress({ done: 0, total: library.total_games });

    const poll = setInterval(async () => {
      try {
        const p = await getAchievementsProgress(user.steam_id);
        if (p.total > 0) setAchProgress(p);
      } catch {
        // progress is not critical — just skip this tick
      }
    }, 350);

    try {
      const lib = await refreshLibraryAchievements(user.steam_id);
      setLibrary(lib);
    } catch {
      setAchError(true);
    } finally {
      clearInterval(poll);
      setAchLoading(false);
      setAchProgress(null);
    }
  }

  const stats = useMemo(() => {
    if (!library || typeof library !== 'object') return null;
    const games = library.games;
    const totalHours = library.total_playtime_minutes / 60;

    const topGames = [...games].sort((a, b) => b.playtime_minutes - a.playtime_minutes).slice(0, 12);
    const maxMinutes = topGames[0]?.playtime_minutes || 1;

    const achievementGames = games
      .filter((g) => g.achievements && g.achievements.total > 0)
      .sort((a, b) => b.achievements.pct - a.achievements.pct);

    const distribution = BUCKETS.map((b) => ({
      label: b.label,
      count: games.filter((g) => b.test(g.playtime_minutes / 60)).length,
    }));
    const maxBucket = Math.max(...distribution.map((d) => d.count));

    const neverPlayed = games.filter((g) => g.playtime_minutes === 0).map((g) => g.name);
    const recent = library.recent[0];
    const mostPlayed = topGames[0];

    return { totalHours, topGames, maxMinutes, achievementGames, distribution, maxBucket, neverPlayed, recent, mostPlayed };
  }, [library]);

  const communityGames = useMemo(() => {
    if (!stats) return [];
    const withStats = stats.topGames
      .map((g) => ({ game: g, spy: gameStats[g.app_id] }))
      // SteamSPY returns a valid record with zeroed stats for games it has not indexed
      // yet (usually fresh releases) — that means "no data", not "0 online".
      .filter((x) => x.spy && (x.spy.ccu > 0 || x.spy.positive > 0 || x.spy.negative > 0));
    const maxCcu = Math.max(...withStats.map((x) => x.spy.ccu), 1);
    return withStats
      .map((x) => ({ ...x, ratio: x.spy.ccu / maxCcu }))
      .sort((a, b) => b.spy.ccu - a.spy.ccu);
  }, [stats, gameStats]);

  if (user === undefined) {
    return (
      <div className="dash-loading">
        LOOKING UP {lookup}<span className="blink">_</span>
      </div>
    );
  }

  if (user === 'not_found' || user === 'error') {
    return (
      <div className="soon-screen">
        <pre className="soon-log">
{`C:\\STEAMSTATS> LOOKUP ${lookup}

${user === 'not_found' ? 'Profile not found.' : 'Could not load the data. Please try again.'}
`}
        </pre>
        <Link className="soon-back" to="/">
          &gt; RETURN TO STEAMSTATS.EXE
        </Link>
      </div>
    );
  }

  return (
    <div className="dash">
      <div className="dash-identity">
        <img className="dash-avatar" src={user.avatar_url} alt="" />
        <div>
          <div className="dash-identity-name">{user.persona_name}</div>
          <div className="dim" style={{ fontSize: 12 }}>
            member since {fmtDate(user.account_created)} ·{' '}
            <a href={user.profile_url} target="_blank" rel="noopener noreferrer">
              profile ↗
            </a>
          </div>
        </div>
      </div>

      {library === undefined && (
        <div className="dash-loading">
          LOADING LIBRARY.DAT<span className="blink">_</span>
        </div>
      )}

      {library === 'private' && (
        <div className="dash-content">
          <TerminalWindow title="C:\STEAMSTATS\LIBRARY.DAT">
            <div className="dim">This profile's library is hidden by Steam privacy settings.</div>
          </TerminalWindow>
        </div>
      )}

      {library === 'empty' && (
        <div className="dash-content">
          <TerminalWindow title="C:\STEAMSTATS\LIBRARY.DAT">
            <div className="dim">This profile's library has no games.</div>
          </TerminalWindow>
        </div>
      )}

      {library === 'error' && (
        <div className="dash-content">
          <TerminalWindow title="C:\STEAMSTATS\LIBRARY.DAT">
            <div className="dim">Could not load the library. Please try again later.</div>
          </TerminalWindow>
        </div>
      )}

      {stats && (
        <div className="dash-content">
          <TerminalWindow
            title="C:\STEAMSTATS\SUMMARY.DAT"
            right={<span>{library.total_games} GAMES SCANNED</span>}
          >
            <div className="hero-grid">
              <DotRow label="Total playtime" value={`${fmtHours(library.total_playtime_minutes)} h`} />
              <DotRow label="≈ Days nonstop" value={fmtNum(stats.totalHours / 24)} />
              <DotRow label="Games in library" value={fmtInt(library.total_games)} />
              <DotRow label="Played / never launched" value={`${fmtInt(library.played_count)} / ${fmtInt(library.never_played_count)}`} />
              <DotRow label="Most played" value={stats.mostPlayed.name} />
              <DotRow
                label="Share of total time"
                value={
                  library.total_playtime_minutes > 0
                    ? `${fmtPct((stats.mostPlayed.playtime_minutes / library.total_playtime_minutes) * 100)}%`
                    : '—'
                }
              />
            </div>
          </TerminalWindow>

          <TerminalWindow title="C:\STEAMSTATS\TOP_GAMES.LOG" right={<span>TOP 12 / {library.total_games}</span>}>
            <div className="list">
              {stats.topGames.map((g, i) => (
                <MeterRow
                  key={g.app_id}
                  rank={i + 1}
                  name={g.name}
                  ratio={g.playtime_minutes / stats.maxMinutes}
                  value={`${fmtHours(g.playtime_minutes)} h`}
                />
              ))}
            </div>
          </TerminalWindow>

          {communityGames.length > 0 && (
            <TerminalWindow title="C:\STEAMSTATS\COMMUNITY.LOG" right={<span>STEAMSPY · {communityGames.length} GAMES</span>}>
              <div className="list">
                {communityGames.map(({ game, spy, ratio }) => {
                  const rating = spy.positive + spy.negative > 0 ? (spy.positive / (spy.positive + spy.negative)) * 100 : null;
                  return (
                    <MeterRow
                      key={game.app_id}
                      name={game.name}
                      ratio={ratio}
                      value={`${fmtInt(spy.ccu)} online${rating !== null ? ` · ${fmtPct(rating)}%` : ''}`}
                    />
                  );
                })}
              </div>
            </TerminalWindow>
          )}

          <TerminalWindow
            title="C:\STEAMSTATS\ACHIEVEMENTS.LOG"
            right={stats.achievementGames.length > 0 && <span>{stats.achievementGames.length} GAMES WITH STATS</span>}
          >
            <button className="ach-load-btn" onClick={handleLoadAchievements} disabled={achLoading}>
              {achLoading
                ? pacmanBar(achProgress?.done ?? 0, achProgress?.total ?? 0)
                : stats.achievementGames.length > 0
                  ? '> REFRESH ACHIEVEMENTS'
                  : '> LOAD ACHIEVEMENTS'}
            </button>
            {achError && (
              <div className="dim" style={{ marginTop: 12 }}>
                Could not load achievements. Please try again.
              </div>
            )}
            {stats.achievementGames.length > 0 ? (
              <div className="list" style={{ marginTop: 16 }}>
                {stats.achievementGames.map((g) => (
                  <MeterRow
                    key={g.app_id}
                    name={g.name}
                    ratio={g.achievements.pct / 100}
                    value={`${g.achievements.unlocked}/${g.achievements.total} · ${fmtPct(g.achievements.pct)}%`}
                  />
                ))}
              </div>
            ) : (
              !achLoading &&
              !achError && (
                <div className="dim" style={{ marginTop: 12 }}>
                  Achievements are not loaded automatically so the profile opens faster.
                </div>
              )
            )}
          </TerminalWindow>

          <div className="two-col">
            <TerminalWindow title="C:\STEAMSTATS\RECENT.LOG">
              {stats.recent ? (
                <>
                  <div className="recent-big mono-num">{fmtHours(stats.recent.playtime_2weeks_minutes)} h</div>
                  <div className="dim" style={{ fontSize: 13 }}>
                    in {stats.recent.name} over the last 14 days
                  </div>
                  <div style={{ marginTop: 14 }}>
                    <MeterRow
                      name="OF 336H WINDOW"
                      ratio={stats.recent.playtime_2weeks_minutes / 60 / 336}
                      value={`${fmtPct((stats.recent.playtime_2weeks_minutes / 60 / 336) * 100)}%`}
                      meterWidth={16}
                    />
                  </div>
                </>
              ) : (
                <div className="dim">No activity in the last 14 days.</div>
              )}
            </TerminalWindow>

            <TerminalWindow title="C:\STEAMSTATS\HISTOGRAM.LOG">
              <div className="list">
                {stats.distribution.map((d) => (
                  <MeterRow key={d.label} name={d.label} ratio={d.count / stats.maxBucket} value={`${d.count} games`} meterWidth={14} />
                ))}
              </div>
            </TerminalWindow>
          </div>

          <TerminalWindow title="C:\STEAMSTATS\NEVER_LAUNCHED.LOG" right={<span>{stats.neverPlayed.length} GAMES</span>}>
            <div className="chips">
              {stats.neverPlayed.map((name) => (
                <span key={name} className="chip">
                  [ {name} ]
                </span>
              ))}
            </div>
          </TerminalWindow>
        </div>
      )}

      <StatusBar
        items={[
          { key: 'F1', label: 'HELP', onClick: () => navigate('/soon/help') },
          { key: 'F2', label: 'WRAPPED', onClick: () => navigate('/soon/wrapped') },
          { key: 'F3', label: 'LEADERBOARD', onClick: () => navigate('/soon/leaderboard') },
          { key: 'F4', label: 'WISHLIST', onClick: () => navigate('/soon/wishlist') },
          { key: 'F9', label: 'HOME', onClick: () => navigate('/') },
        ]}
      />
    </div>
  );
}
