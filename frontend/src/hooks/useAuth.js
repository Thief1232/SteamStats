import { useEffect, useState } from 'react';
import { getMe } from '../api/client';

// undefined = still checking session, null = signed out, object = signed in
export function useAuth() {
  const [me, setMe] = useState(undefined);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((res) => !cancelled && setMe(res))
      .catch(() => !cancelled && setMe(null));
    return () => {
      cancelled = true;
    };
  }, []);

  return me;
}
