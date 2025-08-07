import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ChatBox({
  messages,
  onSend,
  isTyping,
  setIsTyping,
  onStop,
}) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    setIsTyping(true);
    onSend(input);
    setInput("");
  };

  return (
    <>
      <div className="flex-grow p-4 overflow-y-auto scrollbar">
        {messages.length === 0 && (
          <div className="flex justify-start mb-4">
            <div className="chat-bubble chat-bubble-agent p-4 rounded-xl max-w-md">
              <p className="font-bold mb-2 gradient-text">Hackathon Agent</p>
              <p className="text-readable-dark">
                Hello! I'm your local hackathon assistant. To get started,
                please add the hackathon rules or your initial ideas in the
                context panel on the left. Then, let's start brainstorming!
              </p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex mb-4 ${
              msg.role === "assistant" ? "justify-start" : "justify-end"
            }`}
          >
            <div
              className={`chat-bubble p-4 rounded-xl max-w-md ${
                msg.role === "assistant"
                  ? "chat-bubble-agent"
                  : "chat-bubble-user"
              }`}
            >
              {msg.role === "assistant" && (
                <p className="font-bold mb-2 gradient-text">Hackathon Agent</p>
              )}
              {msg.role === "assistant" && msg.thinking && (
                <div className="dropzone mb-3 p-3 rounded-lg">
                  <div className="flex items-center mb-2">
                    <i className="fas fa-brain text-purple-600 mr-2"></i>
                    <span className="text-xs font-semibold text-purple-600">
                      Thinking...
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 italic font-mono leading-relaxed">
                    {msg.thinking}
                  </p>
                </div>
              )}
              <div className="message-content">
                {msg.role === "assistant" ? (
                  <div className="text-readable-dark">
                    {/* Show raw text while streaming, markdown when complete */}
                    {i === messages.length - 1 && isTyping ? (
                      <div className="whitespace-pre-wrap">
                        {msg.content}
                        <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse"></span>
                      </div>
                    ) : (
                      <ReactMarkdown children={msg.content} remarkPlugins={[remarkGfm]} />
                    )}
                  </div>
                ) : (
                  <p className="text-white">{msg.content}</p>
                )}
              </div>
              {msg.role === "assistant" &&
                msg.rule_chunks &&
                msg.rule_chunks.length > 0 && (
                  <div className="rule-chunks mt-3 text-xs text-readable-light glass-effect-readable p-2 rounded-lg border border-white/10">
                    📋 Referenced rules: {msg.rule_chunks.join(", ")}
                  </div>
                )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {isTyping && (
        <div className="p-4 text-sm text-readable-dark flex items-center glass-effect-readable mx-4 mb-4 rounded-lg border border-white/10">
          <div className="loader mr-3"></div>
          <span>Agent is thinking...</span>
        </div>
      )}

      <div className="p-4 border-t border-white/20">
        <form
          onSubmit={handleSubmit}
          className="flex items-center glass-effect-readable rounded-xl p-3 border border-white/20"
        >
          <input
            type="text"
            className="flex-grow bg-transparent border-none focus:ring-0 text-readable-dark placeholder-gray-500 enhanced-input rounded-lg px-3 py-2"
            placeholder="Type your message here..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isTyping}
          />
          {isTyping ? (
            <button
              type="button"
              onClick={onStop}
              className="ml-3 bg-red-500 hover:bg-red-600 p-2 rounded-full w-10 h-10 flex items-center justify-center transition-all duration-300 hover:scale-110"
            >
              <i className="fas fa-stop text-white"></i>
            </button>
          ) : (
            <button
              type="submit"
              className="ml-3 btn-gradient p-2 rounded-full w-10 h-10 flex items-center justify-center transition-all duration-300 hover:scale-110"
            >
              <i className="fas fa-paper-plane text-white"></i>
            </button>
          )}
        </form>
      </div>
    </>
  );
}
