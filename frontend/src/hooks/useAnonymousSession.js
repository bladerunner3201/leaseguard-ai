import { useEffect, useState } from 'react';

import { ensureAnonymousSession, getAnonymousSessionId } from '../api/client.js';

export function useAnonymousSession() {
  const [anonymousSessionId, setAnonymousSessionId] = useState(getAnonymousSessionId());
  const [loading, setLoading] = useState(!anonymousSessionId);
  const [error, setError] = useState('');

  useEffect(() => {
    if (anonymousSessionId) {
      return;
    }

    let mounted = true;
    ensureAnonymousSession()
      .then((sessionId) => {
        if (mounted) {
          setAnonymousSessionId(sessionId);
        }
      })
      .catch((sessionError) => {
        if (mounted) {
          setError(sessionError.message);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [anonymousSessionId]);

  return { anonymousSessionId, loading, error };
}
