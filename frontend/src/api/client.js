const SESSION_STORAGE_KEY = 'anonymousSessionId';

export function getAnonymousSessionId() {
  return localStorage.getItem(SESSION_STORAGE_KEY);
}

export function setAnonymousSessionId(anonymousSessionId) {
  if (!anonymousSessionId) {
    return;
  }
  localStorage.setItem(SESSION_STORAGE_KEY, anonymousSessionId);
}

async function parseResponse(response) {
  const body = await response.json().catch(() => null);

  if (!response.ok || body?.success === false) {
    const message = body?.message || `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return body?.data ?? body;
}

export async function createAnonymousSession() {
  const response = await fetch('/api/v1/anonymous-sessions', {
    method: 'POST',
  });
  const data = await parseResponse(response);
  setAnonymousSessionId(data.anonymousSessionId);
  return data.anonymousSessionId;
}

export async function ensureAnonymousSession() {
  const existingSessionId = getAnonymousSessionId();
  if (existingSessionId) {
    return existingSessionId;
  }
  return createAnonymousSession();
}

async function apiFetch(path, options = {}) {
  const anonymousSessionId = await ensureAnonymousSession();
  const headers = new Headers(options.headers || {});
  headers.set('X-Anonymous-Session-Id', anonymousSessionId);

  const response = await fetch(path, {
    ...options,
    headers,
  });

  return parseResponse(response);
}

export async function uploadContract(file) {
  const formData = new FormData();
  formData.append('file', file);

  return apiFetch('/api/v1/contracts', {
    method: 'POST',
    body: formData,
  });
}

export async function createChatSession({ contractId, title }) {
  return apiFetch('/api/v1/chat-sessions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ contractId, title }),
  });
}

export async function sendChatMessage({ chatSessionId, contractId, message }) {
  return apiFetch(`/api/v1/chat-sessions/${chatSessionId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ contractId, message }),
  });
}

export async function getChatMessages(chatSessionId) {
  return apiFetch(`/api/v1/chat-sessions/${chatSessionId}/messages`);
}
