const SESSION_STORAGE_KEY = 'anonymousSessionId';
export const CHAT_SESSION_STORAGE_KEY = 'leaseguardChatSessionsByContract';
export const REVIEW_JOB_STORAGE_PREFIX = 'leaseguard-review-job-';

export function getAnonymousSessionId() {
  return localStorage.getItem(SESSION_STORAGE_KEY);
}

export function setAnonymousSessionId(anonymousSessionId) {
  if (!anonymousSessionId) {
    return;
  }
  localStorage.setItem(SESSION_STORAGE_KEY, anonymousSessionId);
}

export function clearAnonymousSession() {
  localStorage.removeItem(SESSION_STORAGE_KEY);
  localStorage.removeItem(CHAT_SESSION_STORAGE_KEY);
  Object.keys(localStorage)
    .filter((key) => key.startsWith(REVIEW_JOB_STORAGE_PREFIX))
    .forEach((key) => localStorage.removeItem(key));
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

export async function getContracts() {
  return apiFetch('/api/v1/contracts');
}

export async function getContract(contractId) {
  return apiFetch(`/api/v1/contracts/${contractId}`);
}

export async function getContractAnalysis(contractId) {
  return apiFetch(`/api/v1/contracts/${contractId}/analysis`);
}

export async function deleteContract(contractId) {
  return apiFetch(`/api/v1/contracts/${contractId}`, {
    method: 'DELETE',
  });
}

export async function startReviewJob(contractId) {
  return apiFetch(`/api/v1/contracts/${contractId}/review-jobs`, {
    method: 'POST',
  });
}

export async function getReviewJob(contractId, jobId) {
  return apiFetch(`/api/v1/contracts/${contractId}/review-jobs/${jobId}`);
}

export async function getReviewReport(contractId) {
  return apiFetch(`/api/v1/contracts/${contractId}/review-report`);
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

export async function getChatSessions() {
  return apiFetch('/api/v1/chat-sessions');
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
