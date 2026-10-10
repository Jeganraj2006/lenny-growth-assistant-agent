import DOMPurify from 'dompurify';

/**
 * Sanitizes raw HTML or Markdown content using DOMPurify.
 * Rejects dangerous elements (<script>, <iframe>, <object>, <embed>, <form>),
 * inline event handlers (on*), javascript: URIs, and unsafe embedded content.
 * 
 * @param {string} rawHtml 
 * @returns {string} Sanitized clean HTML string
 */
export function sanitizeArtifactHtml(rawHtml) {
  if (!rawHtml || typeof rawHtml !== 'string') return '';

  return DOMPurify.sanitize(rawHtml, {
    FORBID_TAGS: [
      'script', 'iframe', 'object', 'embed', 'form', 'input', 
      'textarea', 'button', 'select', 'option', 'meta', 'base', 
      'link', 'applet', 'frame', 'frameset'
    ],
    FORBID_ATTR: [
      'onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 
      'onblur', 'onchange', 'onsubmit', 'onkeydown', 'onkeypress'
    ],
    ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp):|[^a-z]|[a-z0-9+.\-]+(?:[^a-z0-9+.\-:]|$))/i,
    ADD_ATTR: ['target']
  });
}
