const SESSION_STORAGE_KEY = 'anonymousSessionId';

export function getAnonymousSessionId() {
  return localStorage.getItem(SESSION_STORAGE_KEY);
}

export function setAnonymousSessionId(anonymousSessionId) {
  localStorage.setItem(SESSION_STORAGE_KEY, anonymousSessionId);
}

export async function createAnonymousSession() {
  const response = await fetch('/api/v1/anonymous-sessions', {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('익명 세션을 생성하지 못했습니다.');
  }

  const body = await response.json();
  const anonymousSessionId = body.data?.anonymousSessionId;
  setAnonymousSessionId(anonymousSessionId);
  return anonymousSessionId;
}
