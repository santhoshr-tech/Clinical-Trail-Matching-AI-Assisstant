import React, { useState } from 'react';
import { Bot, Sparkles, X } from 'lucide-react';
import { ChatbotModal } from './ChatbotModal';

export const FloatingWidgets: React.FC = () => {
  const [chatOpen, setChatOpen] = useState<boolean>(false);

  return (
    <>
      {/* Single Professional Floating AI Assistant Button */}
      <div className="fixed bottom-6 right-3 z-40">
        <button
          onClick={() => setChatOpen(true)}
          className="ai-assistant-btn group flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-full shadow-lg hover:shadow-xl transition-all duration-200 border border-blue-400 active:scale-95"
          title="Clinical Trial AI Assistant"
        >
          <div className="relative flex items-center justify-center">
            <Bot className="w-4 h-4 text-white group-hover:rotate-6 transition-transform" />
            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
            </span>
          </div>

          <span className="text-[11px] font-bold tracking-wide text-white">
            AI Assistant
          </span>

          <Sparkles className="w-3 h-3 text-amber-300 opacity-90 group-hover:opacity-100 transition-opacity" />
        </button>
      </div>

      {/* RAG Clinical Chatbot Modal */}
      <ChatbotModal isOpen={chatOpen} onClose={() => setChatOpen(false)} />
    </>
  );
};
