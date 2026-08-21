import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Send, Sparkles, AlertTriangle, X, Bot, User, ExternalLink, ShieldCheck, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';

interface ChatbotModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  citedTrials?: any[];
  timestamp?: string;
}

export const ChatbotModal: React.FC<ChatbotModalProps> = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-msg',
      sender: 'assistant',
      text: 'Hello! I am your Clinical Trial Research Assistant. Ask me any question regarding active trial protocols, conditions, or locations (e.g. "trials for stage 4 lung cancer near Chennai"). All responses are strictly grounded in live database study records.',
    },
  ]);
  const [input, setInput] = useState<string>('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  if (!isOpen) return null;

  const handleSendQuery = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput('');

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: userText,
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    fetch(`${BASE_URL}/api/v1/chatbot/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || 'researcher',
      },
      body: JSON.stringify({
        message: userText,
        conversation_id: conversationId,
        role: user?.role || 'researcher',
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.data) {
          if (data.data.conversation_id) {
            setConversationId(data.data.conversation_id);
          }

          const botMsg: Message = {
            id: data.data.message_id || `bot-${Date.now()}`,
            sender: 'assistant',
            text: data.data.answer,
            citedTrials: data.data.cited_trials || [],
          };

          setMessages((prev) => [...prev, botMsg]);
        }
      })
      .catch((err) => {
        console.error(err);
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            sender: 'assistant',
            text: 'I encountered an error accessing trial records. Please try asking your question again.',
          },
        ]);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-end sm:items-center justify-center sm:p-4 z-50">
      <div className="bg-slate-900 border border-slate-800 rounded-t-2xl sm:rounded-2xl max-w-2xl w-full h-[600px] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-cyan-500/10 rounded-xl border border-cyan-500/20 text-cyan-400">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <span>RAG Research Assistant</span>
                <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded font-mono">
                  Grounded AI
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">Grounded strictly in verified database study records</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Prototype Safety Disclaimer Banner */}
        <div className="bg-amber-950/40 border-b border-amber-800/40 px-4 py-2 text-[11px] text-amber-300 flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>
            This assistant summarizes publicly available trial data. It does not provide medical advice. Consult your doctor or research coordinator for enrollment decisions.
          </span>
        </div>

        {/* Chat Message Scroll Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex items-start space-x-3 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {m.sender === 'assistant' && (
                <div className="p-2 bg-slate-800 border border-slate-700 rounded-lg text-cyan-400 flex-shrink-0 mt-1">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-lg rounded-2xl p-4 text-xs space-y-3 ${
                  m.sender === 'user'
                    ? 'bg-cyan-600 text-white rounded-br-none'
                    : 'bg-slate-950 border border-slate-800 text-slate-200 rounded-bl-none'
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{m.text}</p>

                {/* Grounded Cited Trial Cards */}
                {m.citedTrials && m.citedTrials.length > 0 && (
                  <div className="pt-2 border-t border-slate-800 space-y-2">
                    <p className="text-[10px] uppercase font-mono text-cyan-400 font-bold">
                      Source Trial Citations ({m.citedTrials.length})
                    </p>
                    <div className="grid grid-cols-1 gap-2">
                      {m.citedTrials.map((t) => (
                        <div
                          key={t.id}
                          className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-[11px] space-y-1 flex items-center justify-between"
                        >
                          <div>
                            <span className="font-mono font-bold text-cyan-300 block">{t.nct_id || t.id}</span>
                            <span className="text-slate-300 line-clamp-1">{t.title}</span>
                          </div>
                          <Link
                            to={`/trials/${t.nct_id || t.id}`}
                            onClick={onClose}
                            className="bg-slate-800 hover:bg-slate-700 text-cyan-300 p-1.5 rounded-lg border border-slate-700 flex-shrink-0"
                            title="View Trial Protocol Details"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {m.sender === 'user' && (
                <div className="p-2 bg-cyan-600 rounded-lg text-white flex-shrink-0 mt-1">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-slate-800 border border-slate-700 rounded-lg text-cyan-400">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-cyan-300 flex items-center space-x-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Searching trial database & generating grounded response...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Query Input Footer */}
        <form onSubmit={handleSendQuery} className="p-4 bg-slate-950 border-t border-slate-800 flex items-center space-x-2">
          <input
            type="text"
            placeholder="Ask questions about trials, conditions, locations..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-cyan-600 hover:bg-cyan-500 text-white p-3 rounded-xl transition-colors disabled:opacity-50 flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
