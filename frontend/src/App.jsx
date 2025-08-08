import axios from "axios";
import { useState } from "react";
import ChatBox from "./components/ChatBox";
import FileDrop from "./components/FileDrop";

axios.defaults.baseURL = "http://localhost:8000";

function App() {
  const [messages, setMessages] = useState([]);
  const [file, setFile] = useState(null);
  const [urlText, setUrlText] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [abortController, setAbortController] = useState(null);
  const [dashboardData, setDashboardData] = useState({
    idea: "Not defined yet.",
    stack: "Not defined yet.",
    todos: ["No tasks yet."],
    submission: "No notes yet.",
  });

  const sendMessage = async (text) => {
    const form = new FormData();
    form.append("user_input", text);
    if (file) form.append("file", file);
    if (urlText) form.append("url_text", urlText);

    // Add user message immediately
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    // Add assistant message placeholder
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", thinking: "", rule_chunks: [] },
    ]);

    // Create abort controller for this request
    const controller = new AbortController();
    setAbortController(controller);

    try {
      {
        const response = await fetch(
          `${axios.defaults.baseURL}/api/chat-stream`,
          {
            method: "POST",
            body: form,
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let currentContent = "";
        let currentThinking = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.trim() && line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.type === "rule_chunks") {
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const assistantMessageIndex = newMessages.length - 1;
                    if (
                      newMessages[assistantMessageIndex] &&
                      newMessages[assistantMessageIndex].role === "assistant"
                    ) {
                      newMessages[assistantMessageIndex].rule_chunks =
                        data.rule_chunks;
                    }
                    return newMessages;
                  });
                } else if (data.type === "thinking") {
                  currentThinking += data.content;
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const assistantMessageIndex = newMessages.length - 1;
                    if (
                      newMessages[assistantMessageIndex] &&
                      newMessages[assistantMessageIndex].role === "assistant"
                    ) {
                      newMessages[assistantMessageIndex].thinking =
                        currentThinking;
                    }
                    return newMessages;
                  });
                } else if (data.type === "token") {
                  currentContent += data.token;
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const assistantMessageIndex = newMessages.length - 1;
                    if (
                      newMessages[assistantMessageIndex] &&
                      newMessages[assistantMessageIndex].role === "assistant"
                    ) {
                      newMessages[assistantMessageIndex].content = currentContent;
                    }
                    return newMessages;
                  });
                } else if (data.type === "end") {
                  setIsTyping(false);
                  break;
                }
              } catch (e) {
                console.error("Error parsing SSE data:", e, "Line:", line);
              }
            }
          }
        }
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        // Request was aborted
        setMessages((prev) => {
          const newMessages = [...prev];
          const assistantMessageIndex = newMessages.length - 1;
          if (
            newMessages[assistantMessageIndex] &&
            newMessages[assistantMessageIndex].role === "assistant"
          ) {
            newMessages[assistantMessageIndex].content = " [Stopped by user]";
          }
          return newMessages;
        });
      } else {
        console.error(e);
        // Update the assistant message with error
        setMessages((prev) => {
          const newMessages = [...prev];
          const assistantMessageIndex = newMessages.length - 1;
          if (
            newMessages[assistantMessageIndex] &&
            newMessages[assistantMessageIndex].role === "assistant"
          ) {
            newMessages[assistantMessageIndex].content =
              "Sorry, there was an error processing your request.";
          }
          return newMessages;
        });
      }
      setIsTyping(false);
      setAbortController(null);
    }
  };

  const stopGeneration = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
    setIsTyping(false);
  };

  const setContext = async () => {
    if (!urlText.trim() && uploadedFiles.length === 0) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Please provide some context first by pasting text or dropping a file.",
        },
      ]);
      return;
    }

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content:
          "Context updated! I'm ready to help with your hackathon project.",
      },
    ]);
  };

  const updateDashboard = async () => {
    try {
      const res = await fetch(`${axios.defaults.baseURL}/api/todos`);
      const data = await res.json();
      setDashboardData({
        idea: "Derived from your latest chat.",
        stack: "React, FastAPI, Ollama",
        todos: (data.todos && data.todos.length > 0) ? data.todos : ["No tasks yet."],
        submission: "Use the chat to build your submission.",
      });
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="text-gray-800 flex flex-col h-screen">
      {/* Header */}
      <header className="bg-white shadow-lg p-4 flex justify-between items-center border-b border-white/20">
        <div className="flex items-center">
          <div className="relative">
            <i className="fas fa-brain text-2xl gradient-text mr-3"></i>
            <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full blur-sm opacity-30"></div>
          </div>
          <h1 className="text-xl font-bold gradient-text">
            HackathonHero
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-green-600 flex items-center glass-effect px-3 py-1 rounded-full text-readable-dark">
            <i className="fas fa-circle text-xs mr-2 animate-pulse text-green-500"></i>
            gpt-oss-20b | Local & Offline
          </span>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-grow flex flex-col md:flex-row p-4 gap-4 overflow-hidden">
        {/* Left Panel: Context & Rules with glassmorphism */}
        <div className="w-full md:w-1/4 glass-effect-readable rounded-xl shadow-xl p-4 flex flex-col float-animation">
          <h2 className="text-lg font-semibold mb-3 border-b border-white/20 pb-2 gradient-text">
            Hackathon Context
          </h2>
          <p className="text-sm text-readable-light mb-4">
            Paste rules, URLs, or drag & drop files to give the agent context.
          </p>

          <FileDrop
            setFile={setFile}
            uploadedFiles={uploadedFiles}
            setUploadedFiles={setUploadedFiles}
          />

          <textarea
            placeholder="Or paste text/URLs here..."
            className="w-full mt-4 p-2 border border-white/20 rounded-lg h-32 text-sm enhanced-input placeholder-gray-500"
            value={urlText}
            onChange={(e) => setUrlText(e.target.value)}
          />
          <button
            onClick={setContext}
            className="mt-2 w-full btn-gradient font-bold py-2 px-4 rounded-lg transition-all duration-300"
          >
            <i className="fas fa-check-circle mr-2"></i>Set Context
          </button>
          <div className="mt-3 text-sm space-y-1">
            {uploadedFiles.length > 0 && (
              <>
                <p className="font-semibold text-readable-dark">
                  Context Files:
                </p>
                {uploadedFiles.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between glass-effect-readable p-2 rounded-lg border border-white/10"
                  >
                    <span className="text-readable-dark">{file.name}</span>
                    <button
                      onClick={() => {
                        const newFiles = uploadedFiles.filter(
                          (_, i) => i !== index
                        );
                        setUploadedFiles(newFiles);
                      }}
                      className="ml-2 text-red-500 hover:text-red-600 transition-colors"
                    >
                      <i className="fas fa-times"></i>
                    </button>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        {/* Center Panel: Chat Interface with glassmorphism */}
        <div className="w-full md:w-1/2 glass-effect-readable rounded-xl shadow-xl flex flex-col">
          <ChatBox
            messages={messages}
            onSend={sendMessage}
            isTyping={isTyping}
            setIsTyping={setIsTyping}
            onStop={stopGeneration}
          />
        </div>

        {/* Right Panel: Project Dashboard with glassmorphism */}
        <div className="w-full md:w-1/4 glass-effect-readable rounded-xl shadow-xl p-4 flex flex-col float-animation">
          <h2 className="text-lg font-semibold mb-3 border-b border-white/20 pb-2 gradient-text">
            Project Dashboard
          </h2>
          <div className="space-y-4 text-sm">
            <div className="glass-effect-readable p-3 rounded-lg border border-white/10">
              <h3 className="font-semibold text-readable-dark mb-1">
                <i className="fas fa-lightbulb mr-2 text-yellow-500"></i>Project
                Idea
              </h3>
              <p className="text-readable-light italic">{dashboardData.idea}</p>
            </div>
            <div className="glass-effect-readable p-3 rounded-lg border border-white/10">
              <h3 className="font-semibold text-readable-dark mb-1">
                <i className="fas fa-cogs mr-2 text-blue-500"></i>Tech Stack
              </h3>
              <p className="text-readable-light italic">
                {dashboardData.stack}
              </p>
            </div>
            <div className="glass-effect-readable p-3 rounded-lg border border-white/10">
              <h3 className="font-semibold text-readable-dark mb-1">
                <i className="fas fa-tasks mr-2 text-green-500"></i>To-Do List
              </h3>
              <ul className="list-disc list-inside text-readable-light space-y-1">
                {dashboardData.todos.map((todo, index) => (
                  <li
                    key={index}
                    className={todo === "No tasks yet." ? "italic" : ""}
                  >
                    {todo}
                  </li>
                ))}
              </ul>
            </div>
            <div className="glass-effect-readable p-3 rounded-lg border border-white/10">
              <h3 className="font-semibold text-readable-dark mb-1">
                <i className="fas fa-file-alt mr-2 text-purple-500"></i>
                Submission Notes
              </h3>
              <p className="text-readable-light italic">
                {dashboardData.submission}
              </p>
            </div>
          </div>
          <div className="mt-auto pt-4">
            <button
              onClick={updateDashboard}
              className="mt-2 w-full btn-gradient font-bold py-2 px-4 rounded-lg transition-all duration-300"
            >
              <i className="fas fa-sync-alt mr-2"></i>Update Dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
