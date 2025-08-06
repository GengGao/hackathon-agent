import axios from "axios";
import { useState } from "react";
import ChatBox from "./components/ChatBox";
import FileDrop from "./components/FileDrop";

function App() {
  const [messages, setMessages] = useState([]);
  const [file, setFile] = useState(null);
  const [urlText, setUrlText] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [dashboardData, setDashboardData] = useState({
    idea: "Not defined yet.",
    stack: "Not defined yet.",
    todos: ["No tasks yet."],
    submission: "No notes yet."
  });

  const sendMessage = async (text) => {
    const form = new FormData();
    form.append("user_input", text);
    if (file) form.append("file", file);
    if (urlText) form.append("url_text", urlText);
    try {
      const res = await axios.post("/api/chat", form);
      const { response, rule_chunks } = res.data;
      setMessages((prev) => [
        ...prev,
        { role: "user", content: text },
        { role: "assistant", content: response, rule_chunks },
      ]);
    } catch (e) {
      console.error(e);
    }
  };

  const setContext = async () => {
    if (!urlText.trim() && uploadedFiles.length === 0) {
      setMessages(prev => [...prev, { role: "assistant", content: "Please provide some context first by pasting text or dropping a file." }]);
      return;
    }

    setMessages(prev => [...prev, { role: "assistant", content: "Context updated! I'm ready to help with your hackathon project." }]);
  };

  const updateDashboard = async () => {
    setDashboardData({
      idea: "Sample project idea based on conversation",
      stack: "React, Node.js, Python",
      todos: ["Set up development environment", "Create wireframes", "Implement core features"],
      submission: "Project notes and submission guidelines"
    });
  };

  return (
    <div className="text-gray-800 flex flex-col h-screen">
      {/* Header */}
      <header className="bg-white shadow-md p-4 flex justify-between items-center">
        <div className="flex items-center">
          <i className="fas fa-brain text-2xl text-blue-500 mr-3"></i>
          <h1 className="text-xl font-bold">Local Hackathon Agent</h1>
        </div>
        <span className="text-sm font-medium text-green-600 flex items-center">
          <i className="fas fa-circle text-xs mr-2 animate-pulse"></i>
          gpt-oss-20b | Local & Offline
        </span>
      </header>

      {/* Main Content */}
      <div className="flex-grow flex flex-col md:flex-row p-4 gap-4 overflow-hidden">
        {/* Left Panel: Context & Rules */}
        <div className="w-full md:w-1/4 bg-white rounded-lg shadow p-4 flex flex-col">
          <h2 className="text-lg font-semibold mb-3 border-b pb-2">Hackathon Context</h2>
          <p className="text-sm text-gray-500 mb-4">Paste rules, URLs, or drag & drop files to give the agent context.</p>

          <FileDrop setFile={setFile} uploadedFiles={uploadedFiles} setUploadedFiles={setUploadedFiles} />

          <textarea
            placeholder="Or paste text/URLs here..."
            className="w-full mt-4 p-2 border rounded-lg h-32 text-sm"
            value={urlText}
            onChange={(e) => setUrlText(e.target.value)}
          />
          <button
            onClick={setContext}
            className="mt-2 w-full bg-blue-500 text-white font-bold py-2 px-4 rounded-lg hover:bg-blue-600 transition"
          >
            <i className="fas fa-check-circle mr-2"></i>Set Context
          </button>
          <div className="mt-3 text-sm space-y-1">
            {uploadedFiles.length > 0 && (
              <>
                <p className="font-semibold">Context Files:</p>
                {uploadedFiles.map((file, index) => (
                  <div key={index} className="flex items-center justify-between bg-gray-100 p-1 rounded">
                    <span>{file.name}</span>
                    <button
                      onClick={() => {
                        const newFiles = uploadedFiles.filter((_, i) => i !== index);
                        setUploadedFiles(newFiles);
                      }}
                      className="ml-2"
                    >
                      <i className="fas fa-times text-red-500"></i>
                    </button>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        {/* Center Panel: Chat Interface */}
        <div className="w-full md:w-1/2 bg-white rounded-lg shadow flex flex-col">
          <ChatBox messages={messages} onSend={sendMessage} />
        </div>

        {/* Right Panel: Project Dashboard */}
        <div className="w-full md:w-1/4 bg-white rounded-lg shadow p-4 flex flex-col">
          <h2 className="text-lg font-semibold mb-3 border-b pb-2">Project Dashboard</h2>
          <div className="space-y-4 text-sm">
            <div>
              <h3 className="font-semibold text-gray-600 mb-1">
                <i className="fas fa-lightbulb mr-2 text-yellow-500"></i>Project Idea
              </h3>
              <p className="text-gray-500 italic">{dashboardData.idea}</p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-600 mb-1">
                <i className="fas fa-cogs mr-2 text-blue-500"></i>Tech Stack
              </h3>
              <p className="text-gray-500 italic">{dashboardData.stack}</p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-600 mb-1">
                <i className="fas fa-tasks mr-2 text-green-500"></i>To-Do List
              </h3>
              <ul className="list-disc list-inside text-gray-500 space-y-1">
                {dashboardData.todos.map((todo, index) => (
                  <li key={index} className={todo === "No tasks yet." ? "italic" : ""}>{todo}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-gray-600 mb-1">
                <i className="fas fa-file-alt mr-2 text-purple-500"></i>Submission Notes
              </h3>
              <p className="text-gray-500 italic">{dashboardData.submission}</p>
            </div>
          </div>
          <div className="mt-auto pt-4">
            <button
              onClick={updateDashboard}
              className="mt-2 w-full bg-gray-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-gray-700 transition"
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