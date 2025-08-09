import { useEffect, useState } from "react";
import ChatBox from "./components/ChatBox";
import ChatHistory from "./components/ChatHistory";
import FileDrop from "./components/FileDrop";
import TodoManager from "./components/TodoManager";

// All network requests use native fetch (axios removed)

function App() {
  const [messages, setMessages] = useState([]);
  const [urlText, setUrlText] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [abortController, setAbortController] = useState(null);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [showChatHistory, setShowChatHistory] = useState(false);
  const [dashboardData, setDashboardData] = useState({
    idea: "Not defined yet.",
    stack: "Not defined yet.",
    todos: ["No tasks yet."],
    submission: "No notes yet.",
  });
  const [ollamaStatus, setOllamaStatus] = useState({
    connected: false,
    model: "gpt-oss:20b",
    available_models: []
  });
  const [showModelPicker, setShowModelPicker] = useState(false);

  // Check Ollama status
  const checkOllamaStatus = async () => {
    try {
      const res = await fetch('/api/ollama/status');
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      setOllamaStatus(data);
    } catch (error) {
      console.error("Failed to check Ollama status:", error);
      setOllamaStatus({ connected: false, model: "gpt-oss:20b", available_models: [] });
    }
  };

  // Handle model change
  const handleModelChange = async (model) => {
    try {
      const formData = new FormData();
      formData.append("model", model);
      const res = await fetch('/api/ollama/model', { method: 'POST', body: formData });
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      if (data.ok) {
        setOllamaStatus(prev => ({ ...prev, model: data.model }));
        setShowModelPicker(false);
      } else {
        console.warn('Model change rejected', data);
      }
    } catch (error) {
      console.error("Failed to change model:", error);
    }
  };

  // Periodic status checking
  useEffect(() => {
    checkOllamaStatus(); // Initial check
    const interval = setInterval(checkOllamaStatus, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, []);

  // Close model picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showModelPicker && !event.target.closest('.model-picker-container')) {
        setShowModelPicker(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showModelPicker]);

  const sendMessage = async (text) => {
    const form = new FormData();
    form.append("user_input", text);
    // Multi-file support: append each uploaded raw File under 'files'
    if (uploadedFiles && uploadedFiles.length > 0) {
      uploadedFiles.forEach((uf) => {
        if (uf.raw instanceof File) {
          form.append('files', uf.raw);
        }
      });
    }
    if (urlText) form.append("url_text", urlText);
    if (currentSessionId) form.append("session_id", currentSessionId);

    // Add user message immediately
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    // Add assistant message placeholder
    setMessages((prev) => [
      ...prev,
  { role: "assistant", content: "", thinking: "", rule_chunks: [], tool_calls: [] },
    ]);

    // Create abort controller for this request
    const controller = new AbortController();
    setAbortController(controller);
    setIsTyping(true); // ensure typing state on

    try {
      // Use native fetch directly for SSE streaming (axios buffers, so avoid it)
      const response = await fetch('/api/chat-stream', {
        method: 'POST',
        body: form,
        signal: controller.signal,
        headers: { 'Accept': 'text/event-stream' }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentContent = '';
      let currentThinking = '';

      const processEvent = (rawEvent) => {
        // Remove any leading colon heartbeat lines
        if (!rawEvent.trim()) return;
        const dataLines = rawEvent.split('\n').filter(l => l.startsWith('data:'));
        if (dataLines.length === 0) return;
        const jsonStr = dataLines.map(l => l.replace(/^data:\s?/, '')).join('\n');
        try {
          const data = JSON.parse(jsonStr);
          if (data.type === 'session_info') {
            setCurrentSessionId(data.session_id);
          } else if (data.type === 'rule_chunks') {
            setMessages(prev => { const nm=[...prev]; const i=nm.length-1; if(nm[i]?.role==='assistant') nm[i].rule_chunks=data.rule_chunks; return nm; });
          } else if (data.type === 'thinking') {
            currentThinking += data.content || '';
            setMessages(prev => { const nm=[...prev]; const i=nm.length-1; if(nm[i]?.role==='assistant') nm[i].thinking=currentThinking; return nm; });
          } else if (data.type === 'tool_calls') {
            setMessages(prev => { const nm=[...prev]; const i=nm.length-1; if(nm[i]?.role==='assistant'){ const existing=nm[i].tool_calls||[]; const merged=[...existing]; for(const tc of data.tool_calls||[]){ const dup=merged.some(e=> (tc.id && e.id===tc.id) || (e.name===tc.name && e.arguments===tc.arguments)); if(!dup) merged.push(tc);} nm[i].tool_calls=merged; } return nm; });
          } else if (data.type === 'token') {
            currentContent += data.token || '';
            setMessages(prev => { const nm=[...prev]; const i=nm.length-1; if(nm[i]?.role==='assistant') nm[i].content=currentContent; return nm; });
          } else if (data.type === 'end') {
            setIsTyping(false);
          }
        } catch(err){
          console.error('Failed to parse SSE event', err, rawEvent);
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // SSE events separated by double newlines
        let idx;
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const eventBlock = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
            processEvent(eventBlock);
        }
      }
      // Flush remaining (if any)
      if (buffer.trim()) processEvent(buffer);
      setIsTyping(false);
      setAbortController(null);
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
    if (!navigator.onLine) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'You are offline. Context will be used locally, but API calls may fail until you reconnect.' }
      ])
    }
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
  // Get todos
  const todosRes = await fetch(`/api/todos`);
  const todosData = todosRes.ok ? await todosRes.json() : { todos: [] };

      // Get project artifacts if we have a session
      let artifacts = {};
      if (currentSessionId) {
        try {
          const artifactsRes = await fetch(`/api/chat-sessions/${currentSessionId}/project-artifacts`);
          if (artifactsRes.ok) {
            const artifactsData = await artifactsRes.json();
            artifacts = (artifactsData.artifacts || []).reduce((acc, artifact) => { acc[artifact.artifact_type] = artifact; return acc; }, {});
          } else {
            console.log('Artifacts fetch failed', artifactsRes.status);
          }
        } catch (artifactError) {
          console.log("No artifacts found yet:", artifactError);
        }
      }

      setDashboardData({
        idea: artifacts.project_idea?.content || "Generate a project idea from your chat history using the tools below.",
        stack: artifacts.tech_stack?.content || "Generate a tech stack recommendation from your conversation.",
        todos: (todosData.todos && todosData.todos.length > 0) ? todosData.todos : ["No tasks yet."],
        submission: artifacts.submission_summary?.content || "Generate submission notes from your chat history when ready.",
      });
    } catch (e) {
      console.error(e);
    }
  };

  const generateProjectIdea = async () => {
    if (!currentSessionId) {
      alert("Please start a chat session first");
      return;
    }

    try {
  const response = await fetch(`/api/chat-sessions/${currentSessionId}/derive-project-idea`, { method: 'POST' });
      const data = await response.json();
      if (data.ok) {
        updateDashboard(); // Refresh dashboard with new data
      } else {
        alert("Failed to generate project idea: " + (data.error || "Unknown error"));
      }
    } catch (error) {
      console.error("Error generating project idea:", error);
      alert("Failed to generate project idea");
    }
  };

  const generateTechStack = async () => {
    if (!currentSessionId) {
      alert("Please start a chat session first");
      return;
    }

    try {
  const response = await fetch(`/api/chat-sessions/${currentSessionId}/create-tech-stack`, { method: 'POST' });
      const data = await response.json();
      if (data.ok) {
        updateDashboard(); // Refresh dashboard with new data
      } else {
        alert("Failed to generate tech stack: " + (data.error || "Unknown error"));
      }
    } catch (error) {
      console.error("Error generating tech stack:", error);
      alert("Failed to generate tech stack");
    }
  };

  const generateSubmissionNotes = async () => {
    if (!currentSessionId) {
      alert("Please start a chat session first");
      return;
    }

    try {
  const response = await fetch(`/api/chat-sessions/${currentSessionId}/summarize-chat-history`, { method: 'POST' });
      const data = await response.json();
      if (data.ok) {
        updateDashboard(); // Refresh dashboard with new data
      } else {
        alert("Failed to generate submission notes: " + (data.error || "Unknown error"));
      }
    } catch (error) {
      console.error("Error generating submission notes:", error);
      alert("Failed to generate submission notes");
    }
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setUrlText("");
    setUploadedFiles([]);
  };

  const handleSelectSession = async (sessionId) => {
    try {
  const response = await fetch(`/api/chat-sessions/${sessionId}`);
      if (!response.ok) throw new Error(response.statusText);
      const { session, messages: chatMessages } = await response.json();

      setCurrentSessionId(sessionId);
      setMessages(chatMessages.map(msg => ({
        role: msg.role,
        content: msg.content,
        rule_chunks: [],
        thinking: ""
      })));

      // Clear file and URL context when switching sessions
      setUrlText("");
      setUploadedFiles([]);

      // Update dashboard with session-specific data
      setTimeout(updateDashboard, 100); // Small delay to ensure session is set
    } catch (error) {
      console.error("Failed to load session:", error);
    }
  };

  const handleDeleteSession = (sessionId) => {
    if (currentSessionId === sessionId) {
      handleNewChat();
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
          <button
            onClick={() => setShowChatHistory(!showChatHistory)}
            className="lg:hidden btn-gradient p-2 rounded-lg hover:scale-105 transition-all duration-300"
            title="Chat History"
          >
            <i className="fas fa-history text-white text-sm"></i>
          </button>

          {/* Live Ollama Status and Model Picker */}
          <div className="relative model-picker-container">
            <button
              onClick={() => setShowModelPicker(!showModelPicker)}
              className={`text-sm font-medium flex items-center glass-effect px-3 py-1 rounded-full transition-all duration-300 hover:scale-105 ${
                ollamaStatus.connected
                  ? 'text-green-600 text-readable-dark'
                  : 'text-red-600 text-readable-dark'
              }`}
              title="Click to change model"
            >
              <i className={`fas fa-circle text-xs mr-2 ${
                ollamaStatus.connected
                  ? 'animate-pulse text-green-500'
                  : 'text-red-500'
              }`}></i>
              {ollamaStatus.model} | Ollama
              <i className="fas fa-chevron-down text-xs ml-2"></i>
            </button>

            {/* Model Picker Dropdown */}
            {showModelPicker && (
              <div className="absolute top-full right-0 mt-2 bg-white rounded-lg shadow-xl border border-gray-200 py-2 min-w-48 z-50">
                <div className="px-3 py-2 text-xs text-gray-500 border-b border-gray-100">
                  Select Model
                </div>
                {ollamaStatus.available_models.length > 0 ?
                  ollamaStatus.available_models.map((model) => (
                  <button
                    key={model}
                    onClick={() => handleModelChange(model)}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition-colors ${
                      ollamaStatus.model === model
                        ? 'bg-blue-50 text-blue-600 font-medium'
                        : 'text-gray-700'
                    }`}
                  >
                    <i className={`fas fa-circle text-xs mr-2 ${
                      ollamaStatus.model === model ? 'text-blue-500' : 'text-gray-300'
                    }`}></i>
                    {model}
                    {ollamaStatus.model === model && (
                      <i className="fas fa-check text-xs ml-auto float-right mt-0.5 text-blue-500"></i>
                    )}
                  </button>
                )) :
                  // Fallback to hardcoded models if none available
                  ["gpt-oss:20b", "gpt-oss:120b"].map((model) => (
                    <button
                      key={model}
                      onClick={() => handleModelChange(model)}
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition-colors ${
                        ollamaStatus.model === model
                          ? 'bg-blue-50 text-blue-600 font-medium'
                          : 'text-gray-700'
                      }`}
                    >
                      <i className={`fas fa-circle text-xs mr-2 ${
                        ollamaStatus.model === model ? 'text-blue-500' : 'text-gray-300'
                      }`}></i>
                      {model}
                      {ollamaStatus.model === model && (
                        <i className="fas fa-check text-xs ml-auto float-right mt-0.5 text-blue-500"></i>
                      )}
                    </button>
                  ))
                }
                <div className="border-t border-gray-100 mt-2 pt-2 px-3">
                  <div className="text-xs text-gray-500">
                    Status: {ollamaStatus.connected ?
                      <span className="text-green-600 font-medium">Connected</span> :
                      <span className="text-red-600 font-medium">Disconnected</span>
                    }
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-grow flex flex-col lg:flex-row p-4 gap-4 overflow-hidden">

        {/* Left Panel with glassmorphism */}
        <div className="flex flex-col w-full lg:w-1/4 float-animation">
          {/* Chat History Sidebar */}
        <div className={`flex w-full ${showChatHistory ? 'block' : 'hidden lg:block'} mb-6 h-[50%]`}>
          <ChatHistory
            currentSessionId={currentSessionId}
            onSelectSession={handleSelectSession}
            onNewChat={handleNewChat}
            onDeleteSession={handleDeleteSession}
          />
        </div>

        {/* Context & Rules */}
        <div className="w-full glass-effect-readable rounded-xl shadow-xl p-4 flex flex-col ">
          <h2 className="text-lg font-semibold mb-3 border-b border-white/20 pb-2 gradient-text">
            Hackathon Context
          </h2>
          <p className="text-sm text-readable-light mb-4">
            Paste rules, URLs, or drag & drop files to give the agent context.
          </p>

          <FileDrop
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
        </div>


        {/* Center Panel: Chat Interface with glassmorphism */}
        <div className="w-full lg:w-1/2 glass-effect-readable rounded-xl shadow-xl flex flex-col">
          <ChatBox
            messages={messages}
            onSend={sendMessage}
            isTyping={isTyping}
            setIsTyping={setIsTyping}
            onStop={stopGeneration}
            currentSessionId={currentSessionId}
          />
        </div>

        {/* Right Panel: Project Dashboard with glassmorphism */}
        <div className="w-full lg:w-1/4 glass-effect-readable rounded-xl shadow-xl p-4 flex flex-col float-animation">
          <h2 className="text-lg font-semibold mb-3 border-b border-white/20 pb-2 gradient-text">
            Project Dashboard
          </h2>
          <div className="space-y-4 text-sm">
            <div className="glass-effect-readable p-3 rounded-lg border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-readable-dark">
                  <i className="fas fa-lightbulb mr-2 text-yellow-500"></i>Project
                  Idea
                </h3>
                <button
                  onClick={generateProjectIdea}
                  className="text-xs bg-yellow-500 hover:bg-yellow-600 text-white px-2 py-1 rounded transition-colors"
                  title="Generate from chat history"
                >
                  <i className="fas fa-magic mr-1"></i>Generate
                </button>
              </div>
              <p className="text-readable-light italic">{dashboardData.idea}</p>
            </div>
            <div className="glass-effect-readable p-3 rounded-lg border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-readable-dark">
                  <i className="fas fa-cogs mr-2 text-blue-500"></i>Tech Stack
                </h3>
                <button
                  onClick={generateTechStack}
                  className="text-xs bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded transition-colors"
                  title="Generate from chat history"
                >
                  <i className="fas fa-magic mr-1"></i>Generate
                </button>
              </div>
              <p className="text-readable-light italic">
                {dashboardData.stack}
              </p>
            </div>
            <div className="glass-effect-readable p-3 rounded-lg border border-white/10">
              <h3 className="font-semibold text-readable-dark mb-2">
                <i className="fas fa-tasks mr-2 text-green-500"></i>To-Do List
              </h3>
              <TodoManager />
            </div>
            <div className="glass-effect-readable p-3 rounded-lg border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-readable-dark">
                  <i className="fas fa-file-alt mr-2 text-purple-500"></i>
                  Submission Notes
                </h3>
                <button
                  onClick={generateSubmissionNotes}
                  className="text-xs bg-purple-500 hover:bg-purple-600 text-white px-2 py-1 rounded transition-colors"
                  title="Generate from chat history"
                >
                  <i className="fas fa-magic mr-1"></i>Generate
                </button>
              </div>
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
