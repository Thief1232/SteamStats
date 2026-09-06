import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { steamLoginUrl, isMocked, logout } from '../api/client';
import { useAuth } from '../hooks/useAuth';
import './Home.css';

const BOOT_LINES = [
  'STEAMSTATS BIOS v0.4.1 ................ OK',
  'CHECKING STEAM WEB API .................. OK',
  'MOUNTING LIBRARY.DAT ..................... OK',
  'SESSION TABLE ............................ EMPTY',
];

// Accepts a raw SteamID64, a vanity name, or a full profile URL and returns
// whatever /api/users/{lookup} expects.
function parseLookup(input) {
  const trimmed = input.trim();
  if (!trimmed) return null;
  const urlMatch = trimmed.match(/steamcommunity\.com\/(?:profiles|id)\/([^/?#]+)/i);
  return urlMatch ? urlMatch[1] : trimmed;
}

export default function Home() {
  const navigate = useNavigate();
  const me = useAuth();
  const [quitMsg, setQuitMsg] = useState(false);
  const [about, setAbout] = useState(false);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');

  function handleSearch(e) {
    e.preventDefault();
    const lookup = parseLookup(query);
    if (!lookup) {
      setError('Введите SteamID, vanity-имя или ссылку на профиль.');
      return;
    }
    navigate(`/u/${encodeURIComponent(lookup)}`);
  }

  function handleLogin() {
    const url = steamLoginUrl();
    if (url) {
      window.location.href = url;
    } else {
      // No backend wired up yet — drop straight into the fixture profile.
      navigate('/u/76561199009068887');
    }
  }

  async function handleLogout() {
    await logout();
    window.location.reload();
  }

  return (
    <div className="login-screen">
      <div className="boot-log">
        {BOOT_LINES.map((line, i) => (
          <div key={line} className="boot-line" style={{ animationDelay: `${i * 90}ms` }}>
            {line}
          </div>
        ))}
      </div>

      <h1 className="login-banner">STEAMSTATS OS</h1>
      <div className="login-sub dim">
        v0.1.0 — personal build{isMocked ? ' · NO BACKEND LINKED (fixture data)' : ''}
      </div>

      <form className="lookup-form" onSubmit={handleSearch}>
        <span className="lookup-prompt">C:\STEAMSTATS&gt;</span>
        <input
          className="lookup-input"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (error) setError('');
          }}
          placeholder="LOOKUP <steamid | vanity | ссылка на профиль>"
          autoFocus
          spellCheck={false}
        />
      </form>
      {error && <div className="quit-msg">{error}</div>}

      <nav className="menu" aria-label="Главное меню">
        {me ? (
          <>
            <button className="menu-item" onClick={() => navigate(`/u/${me.steam.steam_id}`)}>
              <span className="menu-cursor">&gt;</span> MY_PROFILE.EXE ({me.steam.persona_name})
            </button>
            <button className="menu-item" onClick={handleLogout}>
              <span className="menu-cursor">&gt;</span> LOGOUT.EXE
            </button>
          </>
        ) : (
          <button className="menu-item" onClick={handleLogin}>
            <span className="menu-cursor">&gt;</span> LOGIN_WITH_STEAM.EXE
          </button>
        )}
        <button className="menu-item" onClick={() => setAbout((v) => !v)}>
          <span className="menu-cursor">&gt;</span> ABOUT.EXE
        </button>
        <button className="menu-item" onClick={() => setQuitMsg(true)}>
          <span className="menu-cursor">&gt;</span> QUIT.EXE
        </button>
      </nav>

      {about && (
        <pre className="about-box">
{`STEAMSTATS.EXE
---------------
Публичная аналитика библиотек Steam: время в играх,
прогресс достижений и то, что пылится непройденным.

Смотреть чужую (или свою) статистику можно без входа —
достаточно SteamID, vanity-имени или ссылки на профиль.
Вход через Steam OpenID нужен только для удобства
(быстрый переход на свой профиль); пароль от Steam здесь
никогда не запрашивается и не хранится.`}
        </pre>
      )}

      {quitMsg && (
        <div className="quit-msg">У вас недостаточно прав для выключения этой системы.</div>
      )}

      <div className="login-cursor">
        C:\STEAMSTATS&gt; <span className="blink">_</span>
      </div>
    </div>
  );
}
