import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Profile from './pages/Profile';
import TopGames from './pages/TopGames';
import Placeholder from './pages/Placeholder';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/u/:lookup" element={<Profile />} />
        <Route path="/games" element={<TopGames />} />
        <Route path="/soon/:feature" element={<Placeholder />} />
      </Routes>
    </BrowserRouter>
  );
}
