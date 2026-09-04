import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { steamLoginUrl, isMocked } from '../api/client';
import './Login.css';

const BOOT_LINES = [
  'STEAMSTATS BIOS v0.4.1 ................ OK',
  'CHECKING STEAM WEB API .................. OK',
  'MOUNTING LIBRARY.DAT ..................... OK',
  'SESSION TABLE ............................ EMPTY',
];

export default function Login() {
  const navigate = useNavigate();
  const [quitMsg, setQuitMsg] = useState(false);
  const [about, setAbout] = useState(false);

  function handleLogin() {
    const url = steamLoginUrl();
    if (url) {
      window.location.href = url;
    } else {
      // No backend wired up yet — drop straight into the dashboard with fixture data.
      navigate('/dashboard');
    }
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

      <nav className="menu" aria-label="Главное меню">
        <button className="menu-item" onClick={handleLogin} autoFocus>
          <span className="menu-cursor">&gt;</span> LOGIN_WITH_STEAM.EXE
        </button>
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
Личная аналитика библиотеки Steam: время в играх,
прогресс достижений и то, что пылится непройденным.

Вход выполняется через Steam OpenID — пароль от
Steam здесь никогда не запрашивается и не хранится.`}
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
