import { useEffect, useState } from 'react';

import { createAnonymousSession, getAnonymousSessionId } from '../api/client.js';

export function useAnonymousSession() {
  const [anonymousSessionId, setAnonymousSessionId] = useState(getAnonymousSessionId());
  const [loading, setLoading] = useState(!anonymousSessionId);

  useEffect(() => {
    if (anonymousSessionId) {
      return;
    }

    createAnonymousSession()
      .then(setAnonymousSessionId)
      .finally(() => setLoading(false));
  }, [anonymousSessionId]);

  return { anonymousSessionId, loading };
}
