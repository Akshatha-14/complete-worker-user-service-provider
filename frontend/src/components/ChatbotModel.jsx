import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

// Component to show bot messages line by line
function ChatbotMessage({ response }) {
  const [displayedLines, setDisplayedLines] = useState([]);

  useEffect(() => {
    const lines = response.split("\n");
    let index = 0;

    const interval = setInterval(() => {
      setDisplayedLines((prev) => [...prev, lines[index]]);
      index++;
      if (index === lines.length) clearInterval(interval);
    }, 500);

    return () => clearInterval(interval);
  }, [response]);

  return (
    <div>
      {displayedLines.map((line, i) => (
        <p key={i} className="my-0.5">{line}</p>
      ))}
    </div>
  );
}

// Main Chatbot Modal
function ChatbotModal({ open, onClose }) {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([
    { sender: "bot", text: "👋 Hello! I’m your Personal Assistant" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Scroll to bottom on new message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    setMessages((msgs) => [...msgs, { sender: "user", text: input }]);
    setLoading(true);

    try {
      const response = await axios.post("http://localhost:8000/api/chatbot/", { message: input });
      let botReply = "";
      if (typeof response.data === "string") botReply = response.data;
      else if (response.data.response) botReply = response.data.response;
      else botReply = "Sorry, I couldn't understand the response from server.";

      setMessages((msgs) => [...msgs, { sender: "bot", text: botReply }]);
    } catch (err) {
      console.error(err);
      setMessages((msgs) => [...msgs, { sender: "bot", text: "Sorry, there was an error connecting to the server." }]);
    } finally {
      setLoading(false);
      setInput("");
    }
  };

  const handleInputKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  const handleClose = () => {
    onClose();
    navigate("/userhome"); // Redirect to homepage
  };

  if (!open) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50">
      <div className="w-[450px] h-[600px] bg-gray-50 rounded-3xl shadow-2xl border border-gray-300 flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-4 rounded-t-3xl text-white"
             style={{ background: "linear-gradient(135deg, #6fddffff, #3813C2)" }}>
          <span className="font-bold text-xl">Your Personal Assistant</span>
          <button
            onClick={handleClose}
            className="text-white text-2xl font-bold hover:text-gray-200"
            aria-label="Close chatbot"
          >
            ×
          </button>
        </div>

        {/* Messages */}
        <div className="overflow-y-auto flex-1 p-4 space-y-2" style={{ maxHeight: "480px", backgroundColor: "rgba(255, 255, 255, 1)" }}>
          {messages.map((m, i) => (
            <div
              key={i}
              className={`px-4 py-2 rounded-2xl max-w-[80%] ${m.sender === "bot" ? "bg-gray text-white-800 text-left shadow-md"
          : "bg-blue-100 text-blue-800 text-right ml-auto shadow-md"}`}
            >
              {m.sender === "bot" ? <ChatbotMessage response={m.text} /> : m.text}
            </div>
          ))}
          <div ref={messagesEndRef} />
          {loading && <div className="text-gray-500 text-left my-1">Typing...</div>}
        </div>

        {/* Input */}
        <div className="flex p-3 gap-2 border-t border-gray-300 bg-gray-100 rounded-b-2xl">
          <input
            className="flex-1 border border-gray-300 rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-400"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder="Ask me anything..."
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
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
          className="fixed bottom-5 right-5 z-50 bg-blue-600 text-white w-14 h-14 rounded-full shadow-xl flex items-center justify-center text-2xl hover:bg-blue-700"
          aria-label="Open chatbot"
        >
          💬
        </button>
      )}
      {open && <ChatbotModal open={open} onClose={() => setOpen(false)} />}
    </>
  );
}