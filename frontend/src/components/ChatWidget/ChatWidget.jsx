import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, User, Bot, Loader2 } from 'lucide-react';

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', content: "Hello! I am AkashBot, your OrbitOps guide. How can I help you today?" }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const endOfMessagesRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const handleSend = async () => {
    if (!message.trim() || isTyping) return;

    const userMsg = message.trim();
    setMessage('');
    
    // Add user message to history
    setChatHistory(prev => [...prev, { role: 'user', content: userMsg }]);
    
    // Filter out the welcome message for the backend history to keep it clean, 
    // or just send previous history. The backend expects { role, content } pairs.
    const historyForBackend = chatHistory.filter((msg, idx) => idx > 0); 
    
    setIsTyping(true);
    
    // Create an empty assistant message that will be populated via stream
    setChatHistory(prev => [...prev, { role: 'assistant', content: '' }]);

    try {
      const response = await fetch('/api/v1/chatbot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          conversation_history: historyForBackend,
          language: "en"
        })
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      let done = false;
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const baseLines = chunk.split('\n');
          
          for (let line of baseLines) {
            line = line.trim();
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '');
              if (dataStr === '[DONE]') {
                done = true;
                break;
              }
              try {
                const parsedText = JSON.parse(dataStr);
                // Append streamed text by creating a fresh object reference
                setChatHistory(prev => {
                  const newHistory = [...prev];
                  const lastIdx = newHistory.length - 1;
                  newHistory[lastIdx] = { 
                    ...newHistory[lastIdx], 
                    content: newHistory[lastIdx].content + parsedText 
                  };
                  return newHistory;
                });
              } catch (e) {
                console.error("Parse error on chunk:", dataStr);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error("Chat error:", err);
      setChatHistory(prev => {
        const newHistory = [...prev];
        newHistory[newHistory.length - 1].content = "⚠️ Connection to neural network failed. Please try again later.";
        return newHistory;
      });
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      <button 
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-6 right-6 w-14 h-14 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full shadow-[0_0_20px_rgba(79,70,229,0.5)] flex items-center justify-center transition-all duration-300 z-50 ${isOpen ? 'scale-0 opacity-0' : 'scale-100 opacity-100'}`}
      >
         <MessageSquare className="w-6 h-6" />
      </button>

      {/* Chat Window */}
      <div 
        className={`fixed bottom-6 right-6 w-[350px] h-[500px] bg-[#0a0c12]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden transition-all duration-300 z-50 origin-bottom-right ${isOpen ? 'scale-100 opacity-100' : 'scale-0 opacity-0 pointer-events-none'}`}
      >
        {/* Header */}
        <div className="p-4 border-b border-white/10 bg-gradient-to-r from-indigo-900/50 to-purple-900/50 flex justify-between items-center">
          <div className="flex items-center gap-3">
             <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center border border-indigo-400/30">
               <Bot className="w-4 h-4 text-indigo-400" />
             </div>
             <div>
               <h3 className="text-sm font-bold text-white tracking-wide">AkashBot</h3>
               <p className="text-[10px] text-green-400 tracking-wider">ONLINE · ORBITOPS AI</p>
             </div>
          </div>
          <button 
            onClick={() => setIsOpen(false)}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Messages Layout */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 dark-scrollbar">
          {chatHistory.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl p-3 text-sm leading-relaxed ${
                msg.role === 'user' 
                  ? 'bg-indigo-600/90 text-white rounded-br-sm' 
                  : 'bg-white/5 border border-white/10 text-gray-200 rounded-bl-sm'
              }`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isTyping && (
             <div className="flex justify-start">
               <div className="bg-white/5 border border-white/10 rounded-2xl p-3 rounded-bl-sm flex gap-1">
                 <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                 <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                 <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
               </div>
             </div>
          )}
          <div ref={endOfMessagesRef} />
        </div>

        {/* Input Area */}
        <div className="p-3 border-t border-white/10 bg-black/40">
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="flex items-center gap-2"
          >
            <input 
              type="text" 
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask AkashBot..."
              className="flex-1 bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 transition-colors"
            />
            <button 
              type="submit"
              disabled={!message.trim() || isTyping}
              className="w-9 h-9 flex items-center justify-center rounded-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:bg-white/10 text-white transition-colors flex-shrink-0"
            >
              {isTyping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
