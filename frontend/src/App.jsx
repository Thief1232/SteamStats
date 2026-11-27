import { BrowserRouter, Routes, Route, useParams } from 'react-router-dom';
import Home from './pages/Home';
import Profile from './pages/Profile';
import TopGames from './pages/TopGames';
import GameStats from './pages/GameStats';

// A new key per profile remounts Profile, so moving from one profile to another
// starts from fresh state instead of resetting every field by hand.
function ProfileRoute() {
  const { lookup } = useParams();
  return <Profile key={lookup} />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/u/:lookup" element={<ProfileRoute />} />
        <Route path="/games" element={<TopGames />} />
        <Route path="/games/:appId" element={<GameStats />} />
      </Routes>
    </BrowserRouter>
  );
}
