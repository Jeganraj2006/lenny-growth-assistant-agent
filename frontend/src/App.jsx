import React, { useState, useEffect, useRef } from 'react';
import { listSessions, createSession, getSessionMessages, deleteSession } from './api/sessions';
import { sendChatMessage } from './api/chat';
import { generateEssay, listSessionArtifacts, deleteArtifact } from './api/artifacts';
import SandboxedArtifactViewer from './components/SandboxedArtifactViewer';

export default function App() {
  const [health, setHealth] = useState(null);
  const [agentProof, setAgentProof] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [selectedArtifact, setSelectedArtifact] = useState(null);
  
  const [inputMessage, setInputMessage] = useState('');
  const [selectedProvider, setSelectedProvider] = useState('ollama');
  const [selectedModel, setSelectedModel] = useState('llama3.2:3b');
  
  // Essay Modal State
  const [showEssayModal, setShowEssayModal] = useState(false);
  const [essayTopic, setEssayTopic] = useState('');
  const [essayFormat, setEssayFormat] = useState('markdown');
  const [isGeneratingEssay, setIsGeneratingEssay] = useState(false);
  const [essayError, setEssayError] = useState(null);

  const [loadingHealth, setLoadingHealth] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState(null);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat', 'artifacts', or 'diagnostics'
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const messagesEndRef = useRef(null);
  const isSendingRef = useRef(false);
  const lastPromptRef = useRef('');

  useEffect(() => {
    fetchHealthAndProof();
    fetchSessions();
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      loadSessionHistory(activeSessionId);
      loadArtifacts(activeSessionId);
    } else {
      setMessages([]);
      setArtifacts([]);
      setSelectedArtifact(null);
    }
  }, [activeSessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchHealthAndProof = async () => {
    setLoadingHealth(true);
    try {
      const healthRes = await fetch('/api/v1/health');
      const healthData = await healthRes.json();
      setHealth(healthData);

      const proofRes = await fetch('/api/v1/test-agent');
      const proofData = await proofRes.json();
      setAgentProof(proofData);
    } catch (err) {
      console.error("Failed to connect to backend API:", err);
    } finally {
      setLoadingHealth(false);
    }
  };

  const fetchSessions = async () => {
    try {
      const data = await listSessions();
      setSessions(data.sessions || []);
      if (data.sessions && data.sessions.length > 0 && !activeSessionId) {
        setActiveSessionId(data.sessions[0].id);
      }
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  };

  const loadSessionHistory = async (sessionId) => {
    setLoadingHistory(true);
    setChatError(null);
    try {
      const data = await getSessionMessages(sessionId);
      // Deduplicate messages by ID to prevent repeated chat history items
      const raw = data.messages || [];
      const seen = new Set();
      const unique = [];
      for (const m of raw) {
        const key = m.id || `${m.role}-${m.created_at}`;
        if (!seen.has(key)) {
          seen.add(key);
          unique.push(m);
        }
      }
      setMessages(unique);
    } catch (err) {
      console.error("Failed to load message history:", err);
      setChatError(`Failed to load history: ${err.message}`);
    } finally {
      setLoadingHistory(false);
    }
  };

  const loadArtifacts = async (sessionId) => {
    try {
      const data = await listSessionArtifacts(sessionId);
      setArtifacts(data.artifacts || []);
    } catch (err) {
      console.error("Failed to load artifacts:", err);
    }
  };

  const handleCreateSession = async () => {
    try {
      const newSess = await createSession("New Growth Session");
      setSessions(prev => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
      setMessages([]);
      setArtifacts([]);
      setSelectedArtifact(null);
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  };

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this session?")) return;
    try {
      await deleteSession(sessionId);
      const updated = sessions.filter(s => s.id !== sessionId);
      setSessions(updated);
      if (activeSessionId === sessionId) {
        setActiveSessionId(updated.length > 0 ? updated[0].id : null);
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const handleDeleteArtifact = async (artifactId, e) => {
    e.stopPropagation();
    if (!window.confirm("Delete this artifact?")) return;
    try {
      await deleteArtifact(artifactId);
      const updated = artifacts.filter(a => a.id !== artifactId);
      setArtifacts(updated);
      if (selectedArtifact?.id === artifactId) {
        setSelectedArtifact(null);
      }
    } catch (err) {
      console.error("Failed to delete artifact:", err);
    }
  };

  const handleSendMessage = async (e, retryText = null) => {
    e?.preventDefault();
    const userText = retryText || inputMessage.trim();
    if (!userText || isSendingRef.current || !activeSessionId) return;

    lastPromptRef.current = userText;
    if (!retryText) setInputMessage('');
    setChatError(null);
    isSendingRef.current = true;
    setIsSending(true);

    const tempUserMsg = {
      id: 'temp-' + Date.now(),
      session_id: activeSessionId,
      role: 'user',
      content: userText,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    const targetSessionId = activeSessionId;

    try {
      const res = await sendChatMessage({
        session_id: targetSessionId,
        message: userText,
        provider: selectedProvider,
        model: selectedModel
      });

      if (activeSessionId === targetSessionId) {
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== tempUserMsg.id && m.id !== res.user_message.id && m.id !== res.assistant_message.id);
          return [...filtered, res.user_message, res.assistant_message];
        });
      }
      
      fetchSessions();
    } catch (err) {
      if (activeSessionId === targetSessionId) {
        setChatError(`Error: ${err.message}`);
      }
    } finally {
      isSendingRef.current = false;
      setIsSending(false);
    }
  };

  const handleGenerateEssay = async (e) => {
    e.preventDefault();
    if (!essayTopic.trim() || isGeneratingEssay || !activeSessionId) return;

    setIsGeneratingEssay(true);
    setEssayError(null);

    try {
      const res = await generateEssay({
        session_id: activeSessionId,
        topic: essayTopic,
        format: essayFormat,
        provider: selectedProvider,
        model: selectedModel
      });

      setShowEssayModal(false);
      setEssayTopic('');
      
      // Refresh session history & artifacts list
      loadSessionHistory(activeSessionId);
      loadArtifacts(activeSessionId);

      // Open newly generated artifact in viewer
      setSelectedArtifact(res);
      setActiveTab('artifacts');
    } catch (err) {
      setEssayError(err.message);
    } finally {
      setIsGeneratingEssay(false);
    }
  };

  const activeSessionObj = sessions.find(s => s.id === activeSessionId);

  const displayedMessages = React.useMemo(() => {
    const seen = new Set();
    return messages.filter(m => {
      const key = m.id || `${m.role}-${m.created_at}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [messages]);

  return (
    <div className="flex h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Mobile Drawer Backdrop */}
      {isMobileSidebarOpen && (
        <div 
          onClick={() => setIsMobileSidebarOpen(false)}
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-xs z-30 md:hidden"
        />
      )}

      {/* Sidebar Navigation */}
      <aside className={`
        ${isMobileSidebarOpen ? 'fixed inset-y-0 left-0 z-40 shadow-2xl flex' : 'hidden'}
        md:relative md:flex w-72 bg-slate-900 border-r border-slate-800 flex-col p-4 shrink-0 transition-all
      `}>
        <div className="flex items-center justify-between mb-6 px-2">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30">
              L
            </div>
            <div>
              <h1 className="font-semibold text-sm tracking-wide text-slate-100">Lenny Assistant</h1>
              <p className="text-xs text-slate-400">PM & Growth Intelligence</p>
            </div>
          </div>
          <button
            onClick={() => setIsMobileSidebarOpen(false)}
            className="md:hidden text-slate-400 hover:text-slate-200 text-sm p-1"
          >
            ✕
          </button>
        </div>

        <div className="space-y-2">
          <button 
            onClick={() => { handleCreateSession(); setIsMobileSidebarOpen(false); }}
            className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition flex items-center justify-center space-x-2 shadow-md shadow-indigo-600/20"
          >
            <span>+ New Chat Session</span>
          </button>

          <button 
            onClick={() => { setShowEssayModal(true); setEssayError(null); setIsMobileSidebarOpen(false); }}
            disabled={!activeSessionId}
            className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 font-medium text-xs border border-slate-700 transition flex items-center justify-center space-x-2"
          >
            <span>✍️ Generate Ship 30 Essay</span>
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="mt-4 flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-medium">
          <button 
            onClick={() => { setActiveTab('chat'); setIsMobileSidebarOpen(false); }}
            className={`flex-1 py-1.5 rounded-md transition ${activeTab === 'chat' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Chat
          </button>
          <button 
            onClick={() => { setActiveTab('artifacts'); setIsMobileSidebarOpen(false); }}
            className={`flex-1 py-1.5 rounded-md transition ${activeTab === 'artifacts' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Artifacts ({artifacts.length})
          </button>
          <button 
            onClick={() => { setActiveTab('diagnostics'); setIsMobileSidebarOpen(false); }}
            className={`flex-1 py-1.5 rounded-md transition ${activeTab === 'diagnostics' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Diag
          </button>
        </div>

        {/* Active Sessions List */}
        <div className="mt-4 flex-1 overflow-y-auto space-y-1">
          <div className="px-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>Sessions</span>
            <span className="text-[10px] text-indigo-400 font-normal">({sessions.length})</span>
          </div>
          {sessions.length === 0 ? (
            <div className="px-3 py-2 text-xs text-slate-500 italic">No active sessions</div>
          ) : (
            sessions.map(s => (
              <div 
                key={s.id}
                onClick={() => { setActiveSessionId(s.id); setIsMobileSidebarOpen(false); }}
                className={`group px-3 py-2 rounded-lg text-sm cursor-pointer transition flex items-center justify-between ${
                  s.id === activeSessionId
                    ? 'bg-slate-800/80 text-indigo-400 font-medium border border-indigo-500/30'
                    : 'hover:bg-slate-800/40 text-slate-400'
                }`}
              >
                <span className="truncate pr-2">💬 {s.title}</span>
                <button 
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 text-xs px-1 transition"
                  title="Delete Session"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>

        <div className="pt-4 border-t border-slate-800 text-xs text-slate-500 px-2 space-y-1">
          <div>Ollama: <span className={health?.services?.ollama_status === 'online' ? 'text-emerald-400 font-medium' : 'text-rose-400'}>{health?.services?.ollama_status || 'Checking...'}</span></div>
          <div>Model: <span className="text-slate-300">{selectedModel}</span></div>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-slate-950">
        {/* Top Header */}
        <header className="h-14 border-b border-slate-800 px-4 md:px-6 flex items-center justify-between bg-slate-900/50 backdrop-blur shrink-0">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsMobileSidebarOpen(prev => !prev)}
              className="md:hidden p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white"
              title="Toggle Navigation Menu"
            >
              ☰
            </button>
            <span className="text-sm font-semibold text-slate-200 truncate max-w-[180px] sm:max-w-xs md:max-w-md">
              {activeSessionObj ? `💬 ${activeSessionObj.title}` : 'Lenny Growth Assistant Workspace'}
            </span>
            <span className="hidden sm:inline-block px-2 py-0.5 text-xs rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
              Phase C6 — Demo Ready
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <label className="text-xs text-slate-400 hidden sm:inline">LLM Provider:</label>
            <select 
              value={`${selectedProvider}:${selectedModel}`}
              onChange={(e) => {
                const val = e.target.value;
                if (val === 'anthropic') {
                  setSelectedProvider('anthropic');
                  setSelectedModel('claude-3-5-sonnet-20241022');
                } else if (val === 'ollama:qwen3:4b') {
                  setSelectedProvider('ollama');
                  setSelectedModel('qwen3:4b');
                } else {
                  setSelectedProvider('ollama');
                  setSelectedModel('llama3.2:3b');
                }
              }}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-md px-3 py-1.5 focus:outline-none focus:border-indigo-500"
            >
              <option value="ollama:llama3.2:3b">Ollama (llama3.2:3b - Fast Local)</option>
              <option value="ollama:qwen3:4b">Ollama (qwen3:4b - Local Reasoning)</option>
              <option value="anthropic">Anthropic (Claude 3.5 Sonnet)</option>
            </select>
          </div>
        </header>

        {/* Tab Views */}
        {activeTab === 'diagnostics' ? (
          <div className="flex-1 p-6 overflow-y-auto">
            <div className="max-w-4xl mx-auto bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <h2 className="text-base font-semibold text-slate-100">System Diagnostics & Health</h2>
                  <p className="text-xs text-slate-400">FastAPI, PostgreSQL pgvector, and Ollama service check</p>
                </div>
                <button 
                  onClick={fetchHealthAndProof} 
                  disabled={loadingHealth}
                  className="px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition border border-slate-700"
                >
                  {loadingHealth ? 'Testing...' : 'Re-run Provider Proof'}
                </button>
              </div>

              <div>
                <h3 className="text-xs font-semibold uppercase text-slate-400 tracking-wider mb-2">Backend Health Status</h3>
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 font-mono text-xs text-slate-300">
                  <pre>{JSON.stringify(health, null, 2)}</pre>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-semibold uppercase text-slate-400 tracking-wider mb-2">Agent Provider Compatibility Proof Output</h3>
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 font-mono text-xs text-slate-300 overflow-x-auto max-h-80">
                  <pre>{JSON.stringify(agentProof, null, 2)}</pre>
                </div>
              </div>
            </div>
          </div>
        ) : activeTab === 'artifacts' ? (
          /* Artifacts List & Sandboxed Viewer Tab */
          <div className="flex-1 flex min-h-0 p-6 gap-6">
            {/* Left Column: Artifact List */}
            <div className="w-80 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col shrink-0">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Session Artifacts</h3>
                <span className="text-xs text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">{artifacts.length}</span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2">
                {artifacts.length === 0 ? (
                  <div className="text-center py-8 text-xs text-slate-500 italic">
                    No generated artifacts yet.<br />
                    Click "Generate Ship 30 Essay" to create one!
                  </div>
                ) : (
                  artifacts.map(art => (
                    <div 
                      key={art.id}
                      onClick={() => setSelectedArtifact(art)}
                      className={`group p-3 rounded-lg border cursor-pointer transition ${
                        selectedArtifact?.id === art.id
                          ? 'bg-indigo-600/10 border-indigo-500 text-indigo-300'
                          : 'bg-slate-950 hover:bg-slate-800/50 border-slate-800 text-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono uppercase bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">
                          {art.format}
                        </span>
                        <button 
                          onClick={(e) => handleDeleteArtifact(art.id, e)}
                          className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 text-xs px-1"
                        >
                          ✕
                        </button>
                      </div>
                      <div className="text-xs font-medium line-clamp-2">{art.title}</div>
                      <div className="text-[10px] text-slate-500 mt-2">
                        {new Date(art.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right Column: Sandboxed Viewer */}
            <div className="flex-1 flex flex-col min-w-0">
              {selectedArtifact ? (
                <SandboxedArtifactViewer 
                  artifact={selectedArtifact} 
                  onClose={() => setSelectedArtifact(null)} 
                />
              ) : (
                <div className="h-full bg-slate-900/50 border border-slate-800 rounded-xl flex flex-col items-center justify-center text-slate-500 text-sm space-y-2">
                  <div className="text-3xl">📄</div>
                  <p>Select an artifact from the list to view in the Sandboxed Render Engine.</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Chat Feed Workspace */
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex-1 p-6 overflow-y-auto space-y-4">
              {!activeSessionId ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 text-sm space-y-3">
                  <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center text-2xl border border-slate-800">💡</div>
                  <p>Select or create a chat session to start asking growth questions.</p>
                </div>
              ) : loadingHistory ? (
                <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                  Loading message history...
                </div>
              ) : displayedMessages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs space-y-2">
                  <p className="font-medium text-slate-400">Ask any question grounded in Lenny's Podcast transcripts.</p>
                  <div className="flex flex-wrap justify-center gap-2 max-w-lg mt-2">
                    <button 
                      onClick={() => setInputMessage("How do you handle onboarding in B2B SaaS?")}
                      className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 transition text-xs"
                    >
                      "How do you handle onboarding in B2B SaaS?"
                    </button>
                    <button 
                      onClick={() => setInputMessage("What is Patrick Campbell's advice on value metrics?")}
                      className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 transition text-xs"
                    >
                      "What is Patrick Campbell's advice on value metrics?"
                    </button>
                  </div>
                </div>
              ) : (
                displayedMessages.map((msg, index) => (
                  <div key={msg.id || index} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className="text-[10px] font-semibold text-slate-500 mb-1 px-1">
                      {msg.role === 'user' ? 'You' : `Lenny Assistant (${msg.model_used || selectedModel})`}
                    </div>
                    <div 
                      className={`max-w-3xl rounded-2xl px-4 py-3 text-sm shadow-md leading-relaxed whitespace-pre-wrap ${
                        msg.role === 'user' 
                          ? 'bg-indigo-600 text-white rounded-tr-none' 
                          : 'bg-slate-900 text-slate-200 border border-slate-800 rounded-tl-none'
                      }`}
                    >
                      {msg.content}
                    </div>

                    {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                      <div className="mt-2 max-w-3xl w-full bg-slate-900/60 border border-indigo-500/20 rounded-xl p-3 text-xs space-y-2">
                        <div className="font-semibold text-[11px] text-indigo-400 tracking-wide uppercase flex items-center space-x-1">
                          <span>📚 Grounded Transcript Evidence ({msg.citations.length})</span>
                        </div>
                        <div className="grid grid-cols-1 gap-2">
                          {msg.citations.map((c, cIdx) => (
                            <div key={cIdx} className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800 text-slate-300 space-y-1">
                              <div className="flex items-center justify-between font-medium text-slate-200">
                                <span>🎙️ {c.episode_title}</span>
                                <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                                  {(c.similarity_score * 100).toFixed(0)}% match
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-400">Speaker: <span className="text-slate-300">{c.speaker}</span></div>
                              {c.source_url && (
                                <a 
                                  href={c.source_url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="inline-block text-[11px] text-indigo-400 hover:text-indigo-300 underline font-mono truncate max-w-full"
                                >
                                  🔗 {c.source_url}
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}

              {isSending && (
                <div className="flex flex-col items-start">
                  <div className="text-[10px] font-semibold text-slate-500 mb-1 px-1">
                    Lenny Assistant ({selectedProvider === 'ollama' ? `Local Ollama: ${selectedModel}` : 'Anthropic Claude'})
                  </div>
                  <div className="bg-slate-900 border border-indigo-500/30 rounded-2xl rounded-tl-none px-4 py-3 text-xs text-slate-300 flex items-center space-x-3 shadow-lg">
                    <span className="relative flex h-2.5 w-2.5 shrink-0">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
                    </span>
                    <span>
                      {selectedProvider === 'ollama' 
                        ? `Generating response via local Ollama (${selectedModel}) on CPU... Typically takes 20–35s.`
                        : 'Generating grounded response via Anthropic Claude 3.5 Sonnet...'}
                    </span>
                  </div>
                </div>
              )}

              {chatError && (
                <div className="bg-rose-500/10 border border-rose-500/30 text-rose-300 p-3.5 rounded-xl text-xs space-y-2">
                  <div className="flex items-start space-x-2">
                    <span className="text-rose-400 text-sm leading-none mt-0.5">⚠️</span>
                    <div className="flex-1">
                      <strong className="block text-rose-200 mb-0.5">Request Notice</strong>
                      <span>{chatError}</span>
                      {(chatError.toLowerCase().includes('503') || chatError.toLowerCase().includes('api key') || chatError.toLowerCase().includes('unconfigured')) && (
                        <p className="mt-1 text-[11px] text-slate-400">
                          The Anthropic API key is unconfigured. Click below to switch to local Ollama.
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 pt-1 border-t border-rose-500/20">
                    {selectedProvider === 'anthropic' && (
                      <button 
                        onClick={() => {
                          setSelectedProvider('ollama');
                          setSelectedModel('llama3.2:3b');
                          handleSendMessage(null, lastPromptRef.current);
                        }} 
                        className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-[11px] font-medium transition"
                      >
                        Switch to Ollama (Local) & Retry
                      </button>
                    )}
                    <button 
                      onClick={() => handleSendMessage(null, lastPromptRef.current)} 
                      className="px-2.5 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 rounded text-[11px] transition"
                    >
                      Retry Message
                    </button>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar Form */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/50 backdrop-blur shrink-0">
              <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex items-center space-x-3">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder={activeSessionId ? "Ask a PM or growth question grounded in Lenny's Podcast..." : "Select a session first"}
                  disabled={!activeSessionId || isSending}
                  className="flex-1 bg-slate-950 border border-slate-800 text-slate-100 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 disabled:opacity-50 placeholder:text-slate-500"
                />
                <button
                  type="submit"
                  disabled={!activeSessionId || !inputMessage.trim() || isSending}
                  className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-medium text-sm transition shadow-lg shadow-indigo-600/20 shrink-0"
                >
                  {isSending ? 'Thinking...' : 'Send'}
                </button>
              </form>
            </div>
          </div>
        )}
      </main>

      {/* Generate Ship 30 Essay Modal */}
      {showEssayModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
                <span>✍️ Generate Ship 30 for 30 Essay</span>
              </h2>
              <button 
                onClick={() => setShowEssayModal(false)} 
                className="text-slate-400 hover:text-slate-200 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleGenerateEssay} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Essay Brief / Growth Topic
                </label>
                <input 
                  type="text"
                  value={essayTopic}
                  onChange={(e) => setEssayTopic(e.target.value)}
                  placeholder="e.g. 3 Rules for SaaS Pricing & Value Metrics"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Output Format
                  </label>
                  <select 
                    value={essayFormat}
                    onChange={(e) => setEssayFormat(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none"
                  >
                    <option value="markdown">Markdown (.md)</option>
                    <option value="html">HTML Preview (.html)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Provider
                  </label>
                  <select 
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none"
                  >
                    <option value="ollama">Ollama (Local)</option>
                    <option value="anthropic">Anthropic (Cloud)</option>
                  </select>
                </div>
              </div>

              {isGeneratingEssay && (
                <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded-xl text-xs flex items-start space-x-3">
                  <span className="relative flex h-3 w-3 mt-1 shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
                  </span>
                  <div>
                    <strong className="block text-amber-200 mb-0.5">
                      Writing Ship 30 Essay with {selectedProvider === 'ollama' ? `Ollama (${selectedModel})` : 'Anthropic Claude'}
                    </strong>
                    <span>
                      {selectedProvider === 'ollama'
                        ? 'Generating ~1,250 words on local CPU typically takes 2–4 minutes. Please leave this modal open while the model writes.'
                        : 'Generating grounded essay (~15–30s)...'}
                    </span>
                  </div>
                </div>
              )}

              {essayError && (
                <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl text-xs space-y-2">
                  <div><strong>Error:</strong> {essayError}</div>
                  {selectedProvider === 'anthropic' && (
                    <div className="pt-1 border-t border-rose-500/20">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedProvider('ollama');
                          setSelectedModel('llama3.2:3b');
                          setEssayError(null);
                        }}
                        className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-[11px] font-medium transition"
                      >
                        Switch to Ollama (Local) & Try Again
                      </button>
                    </div>
                  )}
                </div>
              )}

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowEssayModal(false)}
                  className="px-4 py-2 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGeneratingEssay || !essayTopic.trim()}
                  className="px-5 py-2 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-xl transition shadow-lg shadow-indigo-600/20"
                >
                  {isGeneratingEssay ? 'Writing Essay...' : 'Generate Artifact'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
