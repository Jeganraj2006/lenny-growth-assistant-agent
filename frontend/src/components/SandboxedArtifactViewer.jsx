import React, { useState } from 'react';
import { sanitizeArtifactHtml } from '../utils/sanitizer';

/**
 * Builds a clean HTML document string for srcDoc rendering inside the sandboxed iframe.
 */
function buildSrcDoc(artifact) {
  const cleanBody = sanitizeArtifactHtml(artifact?.content || '');
  const title = artifact?.title || 'Artifact Preview';

  return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>${title}</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          background-color: #020617;
          color: #f8fafc;
          margin: 0;
          padding: 24px;
          line-height: 1.6;
        }
        h1, h2, h3, h4 {
          color: #f1f5f9;
          margin-top: 1.5em;
          margin-bottom: 0.5em;
        }
        h1 { border-bottom: 1px solid #1e293b; padding-bottom: 8px; font-size: 1.5rem; color: #818cf8; }
        p { margin-bottom: 1em; color: #cbd5e1; font-size: 0.95rem; }
        ul, ol { padding-left: 1.5em; color: #cbd5e1; }
        li { margin-bottom: 0.5em; }
        code { background: #0f172a; border: 1px solid #1e293b; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #38bdf8; font-size: 0.85rem; }
        pre { background: #0f172a; border: 1px solid #1e293b; padding: 16px; border-radius: 8px; overflow-x: auto; font-family: monospace; color: #e2e8f0; }
        blockquote { border-left: 3px solid #6366f1; margin: 1em 0; padding-left: 1rem; color: #94a3b8; font-style: italic; }
        a { color: #818cf8; text-decoration: underline; }
      </style>
    </head>
    <body>
      ${cleanBody}
    </body>
    </html>
  `;
}

export default function SandboxedArtifactViewer({ artifact, onClose }) {
  const [viewMode, setViewMode] = useState('preview'); // 'preview' or 'raw'

  if (!artifact) return null;

  const srcDocHtml = buildSrcDoc(artifact);

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
      {/* Viewer Header */}
      <div className="h-12 bg-slate-950 border-b border-slate-800 px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3 truncate">
          <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 font-mono font-semibold uppercase border border-indigo-500/30">
            {artifact.format}
          </span>
          <h3 className="text-sm font-semibold text-slate-100 truncate max-w-xs">{artifact.title}</h3>
        </div>

        <div className="flex items-center space-x-2">
          {/* Mode Switcher */}
          <div className="flex bg-slate-900 p-0.5 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setViewMode('preview')}
              className={`px-3 py-1 rounded-md transition ${viewMode === 'preview' ? 'bg-indigo-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Sandboxed Preview
            </button>
            <button
              onClick={() => setViewMode('raw')}
              className={`px-3 py-1 rounded-md transition ${viewMode === 'raw' ? 'bg-indigo-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Raw Source
            </button>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-100 px-2 py-1 text-sm font-bold transition"
              title="Close Viewer"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Content Display Area */}
      <div className="flex-1 min-h-0 relative p-4">
        {viewMode === 'preview' ? (
          <iframe
            title={artifact.title || 'Sandboxed Artifact'}
            sandbox=""
            srcDoc={srcDocHtml}
            className="w-full h-full border-0 rounded-lg bg-slate-950"
          />
        ) : (
          <textarea
            readOnly
            value={artifact.content}
            className="w-full h-full bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-xs text-slate-300 resize-none focus:outline-none"
          />
        )}
      </div>

      {/* Viewer Footer & Grounded Citations */}
      {artifact.citations && artifact.citations.length > 0 && (
        <div className="border-t border-slate-800 p-3 bg-slate-950/80 shrink-0 space-y-1 max-h-36 overflow-y-auto">
          <div className="text-[11px] font-semibold uppercase text-indigo-400 tracking-wider">
            📚 Artifact Evidence Citations ({artifact.citations.length})
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            {artifact.citations.map((c, idx) => (
              <div key={idx} className="bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-md text-slate-300">
                🎙️ <span className="font-medium text-slate-200">{c.episode_title}</span>
                {c.speaker && <span className="text-slate-400"> ({c.speaker})</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
