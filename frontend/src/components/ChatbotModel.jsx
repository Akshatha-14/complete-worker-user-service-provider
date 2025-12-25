import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

// Typing animation for bot messages
function ChatbotMessage({ response }) {
  const [displayedLines, setDisplayedLines] = useState([]);

  useEffect(() => {
    const lines = response.split("\n");
    let index = 0;
    const interval = setInterval(() => {
      setDisplayedLines((prev) => [...prev, lines[index]]);
      index++;
      if (index === lines.length) clearInterval(interval);
    }, 400);
    return () => clearInterval(interval);
  }, [response]);

  return (
    <div>
      {displayedLines.map((line, i) => (
        <p key={i} className="my-0.5 leading-relaxed">{line}</p>
      ))}
    </div>
  );
}

function ChatbotModal({ open, onClose }) {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([
    { sender: "bot", text: "👋 Hello! I’m your Personal Assistant. How can I help you today?" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto scroll
  useEffect(() => {
    if (messagesEndRef.current) messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    setMessages((msgs) => [...msgs, { sender: "user", text: input }]);
    setLoading(true);
    try {
      const response = await axios.post("http://localhost:8000/api/chatbot/", { message: input });
      let botReply =
        typeof response.data === "string"
          ? response.data
          : response.data.response || "Sorry, I couldn't understand that.";
      setMessages((msgs) => [...msgs, { sender: "bot", text: botReply }]);
    } catch {
      setMessages((msgs) => [
        ...msgs,
        { sender: "bot", text: "⚠️ Unable to connect. Please try again later." },
      ]);
    } finally {
      setLoading(false);
      setInput("");
    }
  };

  const handleInputKeyDown = (e) => e.key === "Enter" && sendMessage();
  const handleClose = () => {
    onClose();
    navigate("/userhome");
  };

  if (!open) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50">
      <div className="w-[420px] h-[580px] bg-white rounded-3xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex justify-between items-center p-4 bg-[#0A2342] text-white">
          <h2 className="font-light text-lg tracking-wide">Your Personal Assistant</h2>
          <button
            onClick={handleClose}
            className="text-2xl font-light hover:text-blue-200 transition"
          >
            ×
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 bg-gray-50 space-y-3">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`px-4 py-2 rounded-2xl max-w-[80%] shadow-sm ${
                m.sender === "bot"
                  ? "bg-[#0A2342] text-white text-left"
                  : "bg-blue-100 text-blue-900 text-right ml-auto"
              }`}
            >
              {m.sender === "bot" ? <ChatbotMessage response={m.text} /> : m.text}
            </div>
          ))}
          {loading && <p className="text-sm text-gray-500 italic">Bot is typing...</p>}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="flex p-3 gap-2 border-t bg-gray-100">
          <input
            className="flex-1 border border-gray-300 rounded-xl p-2 text-sm outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleInputKeyDown}
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading}
            className="bg-[#0A2342] text-white px-4 py-2 rounded-xl hover:bg-[#132d56] transition disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

// Floating Chatbot Button
export default function FloatingChatbot() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-50 bg-[#0A2342] text-white w-14 h-14 rounded-full shadow-lg flex items-center justify-center text-2xl hover:bg-[#132d56] transition"
        >
          💬
        </button>
      )}
      {open && <ChatbotModal open={open} onClose={() => setOpen(false)} />}
    </>
  );
}
