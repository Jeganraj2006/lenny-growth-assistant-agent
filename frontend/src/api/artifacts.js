/**
 * API client functions for Essay Generation & Artifact Viewer Management.
 */

/**
 * Triggers Ship 30 for 30 essay generation grounded in podcast transcripts.
 * @param {Object} params 
 * @param {string} params.session_id - Active session UUID
 * @param {string} params.topic - Essay topic string
 * @param {string} [params.format='markdown'] - 'markdown' or 'html'
 * @param {string} [params.provider='ollama'] - 'ollama' or 'anthropic'
 * @param {string} [params.model] - Model identifier
 */
export async function generateEssay({ session_id, topic, format = 'markdown', provider = 'ollama', model }) {
  const res = await fetch('/api/v1/essays/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id,
      topic,
      format,
      provider,
      model
    })
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Essay generation failed with status ${res.status}`);
  }

  return await res.json();
}

/**
 * Lists all artifacts created for a specific session.
 * @param {string} sessionId 
 */
export async function listSessionArtifacts(sessionId) {
  const res = await fetch(`/api/v1/sessions/${sessionId}/artifacts`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to list session artifacts');
  }
  return await res.json();
}

/**
 * Retrieves a specific artifact by UUID.
 * @param {string} artifactId 
 */
export async function getArtifact(artifactId) {
  const res = await fetch(`/api/v1/artifacts/${artifactId}`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch artifact');
  }
  return await res.json();
}

/**
 * Deletes an artifact by UUID.
 * @param {string} artifactId 
 */
export async function deleteArtifact(artifactId) {
  const res = await fetch(`/api/v1/artifacts/${artifactId}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to delete artifact');
  }
  return await res.json();
}
