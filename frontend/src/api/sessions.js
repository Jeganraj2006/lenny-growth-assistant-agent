/**
 * API client functions for Chat Sessions management.
 */

const BASE_URL = '/api/v1/sessions';

/**
 * Creates a new chat session.
 * @param {string} [title] Optional custom title for session
 */
export async function createSession(title) {
  const res = await fetch(BASE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(title ? { title } : {})
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to create session');
  }
  return await res.json();
}

/**
 * Lists active chat sessions ordered by activity.
 * @param {number} [limit=50] 
 * @param {number} [offset=0] 
 */
export async function listSessions(limit = 50, offset = 0) {
  const res = await fetch(`${BASE_URL}?limit=${limit}&offset=${offset}`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to list sessions');
  }
  return await res.json();
}

/**
 * Gets details for a specific session by UUID.
 * @param {string} sessionId 
 */
export async function getSession(sessionId) {
  const res = await fetch(`${BASE_URL}/${sessionId}`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch session details');
  }
  return await res.json();
}

/**
 * Gets paginated messages for a session in chronological order.
 * @param {string} sessionId 
 * @param {number} [limit=50] 
 * @param {number} [offset=0] 
 */
export async function getSessionMessages(sessionId, limit = 50, offset = 0) {
  const res = await fetch(`${BASE_URL}/${sessionId}/messages?limit=${limit}&offset=${offset}`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch session messages');
  }
  return await res.json();
}

/**
 * Updates a session's title.
 * @param {string} sessionId 
 * @param {string} title 
 */
export async function updateSessionTitle(sessionId, title) {
  const res = await fetch(`${BASE_URL}/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title })
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to update session title');
  }
  return await res.json();
}

/**
 * Deletes a session and its linked records.
 * @param {string} sessionId 
 */
export async function deleteSession(sessionId) {
  const res = await fetch(`${BASE_URL}/${sessionId}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to delete session');
  }
  return await res.json();
}
