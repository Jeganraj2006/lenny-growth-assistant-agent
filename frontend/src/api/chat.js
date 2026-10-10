/**
 * API client functions for Chat Completion & Grounded RAG.
 */

const BASE_URL = '/api/v1/chat';

/**
 * Sends a user message to the grounded RAG chat completion endpoint.
 * @param {Object} params 
 * @param {string} params.session_id - UUID of active chat session
 * @param {string} params.message - User prompt string
 * @param {string} [params.provider='ollama'] - 'ollama' or 'anthropic'
 * @param {string} [params.model] - Optional model override string
 */
export async function sendChatMessage({ session_id, message, provider = 'ollama', model }) {
  const res = await fetch(BASE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id,
      message,
      provider,
      model
    })
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Chat request failed with status ${res.status}`);
  }

  return await res.json();
}
