import { useState } from "react";

export default function ChatBox({ messages, onSend }) {
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input);
    setInput("");
  };

  return (
    <>
      <div className="flex-grow p-4 overflow-y-auto">
        {messages.length === 0 && (
          <div className="flex justify-start mb-4">
            <div className="chat-bubble chat-bubble-agent p-3 rounded-lg">
              <p className="font-bold mb-1">Hackathon Agent</p>
              <p>Hello! I'm your local hackathon assistant. To get started, please add the hackathon rules or your initial ideas in the context panel on the left. Then, let's start brainstorming!</p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex mb-4 ${msg.role === "assistant" ? "justify-start" : "justify-end"}`}>
            <div className={`chat-bubble p-3 rounded-lg ${msg.role === "assistant" ? "chat-bubble-agent" : "chat-bubble-user"}`}>
              {msg.role === "assistant" && (
                <p className="font-bold mb-1">Hackathon Agent</p>
              )}
              <div className="message-content">
                {msg.content}
              </div>
              {msg.role === "assistant" && msg.rule_chunks && (
                <div className="rule-chunks mt-2 text-xs text-gray-600">
                  📋 Referenced rules: {msg.rule_chunks.join(", ")}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {isTyping && (
        <div className="p-4 text-sm text-gray-500 flex items-center">
          <div className="loader mr-3"></div>
          <span>Agent is thinking...</span>
        </div>
      )}

      <div className="p-4 border-t">
        <form onSubmit={handleSubmit} className="flex items-center bg-gray-100 rounded-lg p-2">
          <input
            type="text"
            className="flex-grow bg-transparent border-none focus:ring-0"
            placeholder="Type your message here..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button
            type="submit"
            className="ml-3 bg-blue-500 text-white p-2 rounded-full w-10 h-10 flex items-center justify-center hover:bg-blue-600 transition"
          >
            <i className="fas fa-paper-plane"></i>
          </button>
        </form>
      </div>
    </>
  );
}