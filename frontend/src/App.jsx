import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ChatBox from "./components/ChatBox";
import ChatHistory from "./components/ChatHistory";
import FileDrop from "./components/FileDrop";
import TodoManager from "./components/TodoManager";

// Network requests use native fetch

function App() {
	const [messages, setMessages] = useState([]);
	const [urlText, setUrlText] = useState("");
	const [uploadedFiles, setUploadedFiles] = useState([]);
	const [isTyping, setIsTyping] = useState(false);
	const [abortController, setAbortController] = useState(null);
	const [currentSessionId, setCurrentSessionId] = useState(null);
	const [showChatHistory, setShowChatHistory] = useState(false);
	const [ragStatus, setRagStatus] = useState({
		ready: false,
		building: true,
		chunks: 0,
	});
	const [dashboardData, setDashboardData] = useState({
		idea: "Not defined yet.",
		stack: "Not defined yet.",
		todos: ["No tasks yet."],
		submission: "No notes yet.",
	});
	const [ollamaStatus, setOllamaStatus] = useState({
		connected: false,
		model: "gpt-oss:20b",
		available_models: [],
	});
	const [showModelPicker, setShowModelPicker] = useState(false);
	const [todosRefreshKey, setTodosRefreshKey] = useState(0);
	const ragStatusPollRef = useRef(null);
	const contextScrollRef = useRef(null);
	const previousFilesCountRef = useRef(0);

	// Streaming state for artifact generators
	const [isStreamingIdea, setIsStreamingIdea] = useState(false);
	const [isStreamingStack, setIsStreamingStack] = useState(false);
	const [isStreamingSummary, setIsStreamingSummary] = useState(false);

	// Simple skeleton text block used while streaming
	const SkeletonText = ({ lines = 3 }) => {
		const widths = ["w-5/6", "w-4/6", "w-3/6", "w-2/3", "w-1/2"];
		const [skeletonId] = useState(() => Math.random().toString(36).slice(2));
		const keys = useMemo(
			() =>
				Array.from({ length: lines }).map(
					() => `${skeletonId}-${Math.random().toString(36).slice(2)}`,
				),
			[lines, skeletonId],
		);
		return (
			<ul className="skeleton-text animate-pulse space-y-2" aria-live="polite">
				{keys.map((key, i) => (
					<li
						key={key}
						className={`h-3 rounded ${widths[i % widths.length]}`}
					/>
				))}
			</ul>
		);
	};
	// Helper component for streaming placeholders

	const generateSessionId = useCallback(
		() =>
			globalThis?.crypto?.randomUUID
				? globalThis.crypto.randomUUID()
				: `session-${Date.now()}`,
		[],
	);

	// Check Ollama status
	const checkOllamaStatus = useCallback(async () => {
		try {
			const res = await fetch("/api/ollama/status");
			if (!res.ok) throw new Error(res.statusText);
			const data = await res.json();
			setOllamaStatus(data);
		} catch (error) {
			console.error("Failed to check Ollama status:", error);
			setOllamaStatus({
				connected: false,
				model: "gpt-oss:20b",
				available_models: [],
			});
		}
	}, []);

	// Handle model change
	const handleModelChange = async (model) => {
		try {
			const formData = new FormData();
			formData.append("model", model);
			const res = await fetch("/api/ollama/model", {
				method: "POST",
				body: formData,
			});
			if (!res.ok) throw new Error(res.statusText);
			const data = await res.json();
			if (data.ok) {
				setOllamaStatus((prev) => ({ ...prev, model: data.model }));
				setShowModelPicker(false);
			} else {
				console.warn("Model change rejected", data);
			}
		} catch (error) {
			console.error("Failed to change model:", error);
		}
	};

	// Check RAG indexing status (no polling). Accepts optional session id for precise checks.
	const checkRagStatus = useCallback(
		async (sessionIdOverride) => {
			const sid = sessionIdOverride ?? currentSessionId;
			try {
				const res = await fetch(
					`/api/context/status${sid ? `?session_id=${encodeURIComponent(sid)}` : ""}`,
				);
				if (!res.ok) throw new Error(res.statusText);
				const data = await res.json();
				// Only accept status for the session we requested to avoid cross-session races
				const statusSession =
					typeof data.session_id === "string" ? data.session_id : sid;
				if (sid && statusSession && statusSession !== sid) return;
				setRagStatus(data);
			} catch (error) {
				console.error("Failed to check RAG status:", error);
				setRagStatus((prev) => ({ ...prev, ready: false, building: false }));
			}
		},
		[currentSessionId],
	);

	// Status checking: Ollama polling; RAG checked on session/context changes
	useEffect(() => {
		checkOllamaStatus(); // Initial Ollama check
		const interval1 = setInterval(checkOllamaStatus, 10000); // every 10s
		return () => {
			clearInterval(interval1);
		};
	}, [checkOllamaStatus]);

	const refreshDashboard = useCallback(async () => {
		try {
			if (!currentSessionId) return;
			const todosRes = await fetch(
				`/api/todos?session_id=${encodeURIComponent(currentSessionId)}`,
			);
			const todosData = todosRes.ok ? await todosRes.json() : { todos: [] };
			let artifacts = {};
			try {
				const artifactsRes = await fetch(
					`/api/chat-sessions/${currentSessionId}/project-artifacts`,
				);
				if (artifactsRes.ok) {
					const artifactsData = await artifactsRes.json();
					artifacts = (artifactsData.artifacts || []).reduce(
						(acc, artifact) => {
							acc[artifact.artifact_type] = artifact;
							return acc;
						},
						{},
					);
				}
			} catch {
				// ignore artifact fetch errors; dashboard will show defaults
			}
			setDashboardData({
				idea:
					artifacts.project_idea?.content ||
					"Generate a project idea from your chat history using the tools below.",
				stack:
					artifacts.tech_stack?.content ||
					"Generate a tech stack recommendation from your conversation.",
				todos:
					todosData.todos && todosData.todos.length > 0
						? todosData.todos
						: ["No tasks yet."],
				submission:
					artifacts.submission_summary?.content ||
					"Generate submission notes from your chat history when ready.",
			});
			// Force TodoManager to refetch so UI reflects latest state
			setTodosRefreshKey((prev) => prev + 1);
		} catch (err) {
			console.error(err);
		}
	}, [currentSessionId]);

	// Ensure a session exists even for a brand-new chat before adding context
	useEffect(() => {
		if (!currentSessionId) {
			setCurrentSessionId(generateSessionId());
		}
	}, [currentSessionId, generateSessionId]);

	// Check RAG status once when session becomes available or changes (initial load and chat switch)
	useEffect(() => {
		if (!currentSessionId) return;
		checkRagStatus(currentSessionId);
	}, [currentSessionId, checkRagStatus]);

	// While not ready (or building), poll status for the active session so UI reflects correct session readiness
	useEffect(() => {
		if (!currentSessionId) return;
		const shouldPoll = !ragStatus.ready || ragStatus.building;
		if (shouldPoll) {
			if (ragStatusPollRef.current) clearInterval(ragStatusPollRef.current);
			ragStatusPollRef.current = setInterval(() => {
				checkRagStatus(currentSessionId);
			}, 1500);
		} else if (ragStatusPollRef.current) {
			clearInterval(ragStatusPollRef.current);
			ragStatusPollRef.current = null;
		}
		return () => {
			if (ragStatusPollRef.current) {
				clearInterval(ragStatusPollRef.current);
				ragStatusPollRef.current = null;
			}
		};
	}, [ragStatus.ready, ragStatus.building, currentSessionId, checkRagStatus]);

	// Auto-refresh dashboard on page load and when session changes
	useEffect(() => {
		if (!currentSessionId) return;
		refreshDashboard();
	}, [currentSessionId, refreshDashboard]);

	useEffect(() => {
		const added = uploadedFiles.length > previousFilesCountRef.current;
		previousFilesCountRef.current = uploadedFiles.length;
		if (!added || uploadedFiles.length === 0) return;
		requestAnimationFrame(() => {
			if (contextScrollRef.current) {
				contextScrollRef.current.scrollTop =
					contextScrollRef.current.scrollHeight;
			}
		});
	}, [uploadedFiles]);

	// Close model picker when clicking outside
	useEffect(() => {
		const handleClickOutside = (event) => {
			if (showModelPicker && !event.target.closest(".model-picker-container")) {
				setShowModelPicker(false);
			}
		};

		document.addEventListener("mousedown", handleClickOutside);
		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
		};
	}, [showModelPicker]);

	const sendMessage = async (text) => {
		const form = new FormData();
		form.append("user_input", text);
		// Multi-file support: append each uploaded raw File under 'files'
		if (uploadedFiles && uploadedFiles.length > 0) {
			for (const uf of uploadedFiles) {
				if (uf.raw instanceof File) {
					form.append("files", uf.raw);
				}
			}
		}
		if (urlText) form.append("url_text", urlText);
		if (currentSessionId) form.append("session_id", currentSessionId);

		// Add user message immediately
		setMessages((prev) => [...prev, { role: "user", content: text }]);

		// Add assistant message placeholder
		setMessages((prev) => [
			...prev,
			{
				role: "assistant",
				content: "",
				thinking: "",
				rule_chunks: [],
				tool_calls: [],
			},
		]);

		// Create abort controller for this request
		const controller = new AbortController();
		setAbortController(controller);
		setIsTyping(true); // ensure typing state on

		try {
			// Use native fetch directly for SSE streaming (axios buffers, so avoid it)
			const response = await fetch("/api/chat-stream", {
				method: "POST",
				body: form,
				signal: controller.signal,
				headers: { Accept: "text/event-stream" },
			});
			if (!response.ok) throw new Error(`HTTP ${response.status}`);

			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let buffer = "";
			let currentContent = "";
			let currentThinking = "";

			const processEvent = (rawEvent) => {
				// Remove any leading colon heartbeat lines
				if (!rawEvent.trim()) return;
				const dataLines = rawEvent
					.split("\n")
					.filter((l) => l.startsWith("data:"));
				if (dataLines.length === 0) return;
				const jsonStr = dataLines
					.map((l) => l.replace(/^data:\s?/, ""))
					.join("\n");
				try {
					const data = JSON.parse(jsonStr);
					if (data.type === "session_info") {
						setCurrentSessionId(data.session_id);
					} else if (data.type === "rule_chunks") {
						setMessages((prev) => {
							const nm = [...prev];
							const i = nm.length - 1;
							if (nm[i] && nm[i].role === "assistant") {
								nm[i].rule_chunks = data.rule_chunks;
							}
							return nm;
						});
					} else if (data.type === "thinking") {
						currentThinking += data.content || "";
						setMessages((prev) => {
							const nm = [...prev];
							const i = nm.length - 1;
							if (nm[i] && nm[i].role === "assistant") {
								nm[i].thinking = currentThinking;
							}
							return nm;
						});
					} else if (data.type === "tool_calls") {
						setMessages((prev) => {
							const nm = [...prev];
							const i = nm.length - 1;
							if (nm[i] && nm[i].role === "assistant") {
								const existing = nm[i].tool_calls || [];
								const merged = [...existing];
								for (const tc of data.tool_calls || []) {
									const dup = merged.some(
										(e) =>
											(tc.id && e.id === tc.id) ||
											(e.name === tc.name && e.arguments === tc.arguments),
									);
									if (!dup) merged.push(tc);
								}
								nm[i].tool_calls = merged;
							}
							return nm;
						});
					} else if (data.type === "token") {
						currentContent += data.token || "";
						setMessages((prev) => {
							const nm = [...prev];
							const i = nm.length - 1;
							if (nm[i] && nm[i].role === "assistant") {
								nm[i].content = currentContent;
							}
							return nm;
						});
					} else if (data.type === "end") {
						setIsTyping(false);
					}
				} catch (err) {
					console.error("Failed to parse SSE event", err, rawEvent);
				}
			};

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				buffer += decoder.decode(value, { stream: true });
				// SSE events separated by double newlines
				let idx = buffer.indexOf("\n\n");
				while (idx !== -1) {
					const eventBlock = buffer.slice(0, idx);
					buffer = buffer.slice(idx + 2);
					processEvent(eventBlock);
					idx = buffer.indexOf("\n\n");
				}
			}
			// Flush remaining (if any)
			if (buffer.trim()) processEvent(buffer);
			setIsTyping(false);
			setAbortController(null);
		} catch (e) {
			if (e.name === "AbortError") {
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
					const i = newMessages.length - 1;
					if (newMessages[i] && newMessages[i].role === "assistant") {
						newMessages[i].content =
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
				{
					role: "assistant",
					content:
						"You are offline. Context will be used locally, but API calls may fail until you reconnect.",
				},
			]);
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

		try {
			// Ensure we have a session to associate context with
			let sid = currentSessionId;
			if (!sid) {
				sid = globalThis?.crypto?.randomUUID
					? globalThis.crypto.randomUUID()
					: `session-${Date.now()}`;
				setCurrentSessionId(sid);
			}
			// Upload files (if any)
			for (const f of uploadedFiles) {
				if (f.raw) {
					const formData = new FormData();
					formData.append("file", f.raw, f.name);
					if (sid) formData.append("session_id", sid);
					await fetch("/api/context/rules", { method: "POST", body: formData });
				}
			}
			// Add pasted text (if any)
			if (urlText.trim()) {
				const formData = new FormData();
				formData.append("text", urlText);
				if (sid) formData.append("session_id", sid);
				await fetch("/api/context/add-text", {
					method: "POST",
					body: formData,
				});
			}
			// Refresh RAG status immediately after context change
			await checkRagStatus(sid);
			setMessages((prev) => [
				...prev,
				{
					role: "assistant",
					content:
						"Context stored. Building the index... Chat will unlock once ready.",
				},
			]);
			// Clear local selections after upload
			setUploadedFiles([]);
			setUrlText("");
		} catch (e) {
			console.error("Failed to set context", e);
			setMessages((prev) => [
				...prev,
				{ role: "assistant", content: `Failed to store context: ${e.message}` },
			]);
		}
	};

	const generateProjectIdea = async () => {
		if (!currentSessionId) {
			alert("Please start a chat session first");
			return;
		}

		const controller = new AbortController();
		setIsStreamingIdea(true);
		try {
			setDashboardData((prev) => ({ ...prev, idea: "" }));
			const res = await fetch(
				`/api/chat-sessions/${currentSessionId}/derive-project-idea?stream=true`,
				{
					method: "POST",
					signal: controller.signal,
					headers: { Accept: "text/event-stream" },
				},
			);
			if (!res.ok) throw new Error(res.statusText);
			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let buffer = "";
			let content = "";
			let ended = false;
			while (true) {
				const { done, value } = await reader.read();
				if (done || ended) break;
				buffer += decoder.decode(value, { stream: true });
				let idx = buffer.indexOf("\n\n");
				while (idx !== -1) {
					const block = buffer.slice(0, idx);
					buffer = buffer.slice(idx + 2);
					const lines = block.split("\n").filter((l) => l.startsWith("data:"));
					if (lines.length) {
						try {
							const payload = JSON.parse(
								lines.map((l) => l.replace(/^data:\s?/, "")).join("\n"),
							);
							if (payload.type === "token") {
								content += payload.token || "";
								setDashboardData((prev) => ({ ...prev, idea: content }));
							} else if (payload.type === "end") {
								ended = true;
							}
						} catch {
							// ignore malformed lines
						}
					}
					idx = buffer.indexOf("\n\n");
				}
			}
			refreshDashboard();
		} catch (error) {
			console.error("Error generating project idea:", error);
			alert("Failed to generate project idea");
		} finally {
			setIsStreamingIdea(false);
		}
	};

	const generateTechStack = async () => {
		if (!currentSessionId) {
			alert("Please start a chat session first");
			return;
		}

		const controller = new AbortController();
		setIsStreamingStack(true);
		try {
			setDashboardData((prev) => ({ ...prev, stack: "" }));
			const res = await fetch(
				`/api/chat-sessions/${currentSessionId}/create-tech-stack?stream=true`,
				{
					method: "POST",
					signal: controller.signal,
					headers: { Accept: "text/event-stream" },
				},
			);
			if (!res.ok) throw new Error(res.statusText);
			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let buffer = "";
			let content = "";
			let ended = false;
			while (true) {
				const { done, value } = await reader.read();
				if (done || ended) break;
				buffer += decoder.decode(value, { stream: true });
				let idx = buffer.indexOf("\n\n");
				while (idx !== -1) {
					const block = buffer.slice(0, idx);
					buffer = buffer.slice(idx + 2);
					const lines = block.split("\n").filter((l) => l.startsWith("data:"));
					if (lines.length) {
						try {
							const payload = JSON.parse(
								lines.map((l) => l.replace(/^data:\s?/, "")).join("\n"),
							);
							if (payload.type === "token") {
								content += payload.token || "";
								setDashboardData((prev) => ({ ...prev, stack: content }));
							} else if (payload.type === "end") {
								ended = true;
							}
						} catch {
							// ignore malformed lines
						}
					}
					idx = buffer.indexOf("\n\n");
				}
			}
			refreshDashboard();
		} catch (error) {
			console.error("Error generating tech stack:", error);
			alert("Failed to generate tech stack");
		} finally {
			setIsStreamingStack(false);
		}
	};

	const generateSubmissionNotes = async () => {
		if (!currentSessionId) {
			alert("Please start a chat session first");
			return;
		}

		const controller = new AbortController();
		setIsStreamingSummary(true);
		try {
			setDashboardData((prev) => ({ ...prev, submission: "" }));
			const res = await fetch(
				`/api/chat-sessions/${currentSessionId}/summarize-chat-history?stream=true`,
				{
					method: "POST",
					signal: controller.signal,
					headers: { Accept: "text/event-stream" },
				},
			);
			if (!res.ok) throw new Error(res.statusText);
			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let buffer = "";
			let content = "";
			let ended = false;
			while (true) {
				const { done, value } = await reader.read();
				if (done || ended) break;
				buffer += decoder.decode(value, { stream: true });
				let idx = buffer.indexOf("\n\n");
				while (idx !== -1) {
					const block = buffer.slice(0, idx);
					buffer = buffer.slice(idx + 2);
					const lines = block.split("\n").filter((l) => l.startsWith("data:"));
					if (lines.length) {
						try {
							const payload = JSON.parse(
								lines.map((l) => l.replace(/^data:\s?/, "")).join("\n"),
							);
							if (payload.type === "token") {
								content += payload.token || "";
								setDashboardData((prev) => ({ ...prev, submission: content }));
							} else if (payload.type === "end") {
								ended = true;
							}
						} catch {
							// ignore malformed lines
						}
					}
					idx = buffer.indexOf("\n\n");
				}
			}
			refreshDashboard();
		} catch (error) {
			console.error("Error generating submission notes:", error);
			alert("Failed to generate submission notes");
		} finally {
			setIsStreamingSummary(false);
		}
	};

	const handleNewChat = () => {
		const sid = generateSessionId();
		setCurrentSessionId(sid);
		setMessages([]);
		setUrlText("");
		setUploadedFiles([]);
	};

	const handleSelectSession = async (sessionId) => {
		try {
			const response = await fetch(`/api/chat-sessions/${sessionId}`);
			if (!response.ok) throw new Error(response.statusText);
			const { messages: chatMessages } = await response.json();

			setCurrentSessionId(sessionId);
			setMessages(
				chatMessages.map((msg) => ({
					role: msg.role,
					content: msg.content,
					rule_chunks: [],
					thinking: msg.metadata?.thinking || "",
					tool_calls: msg.metadata?.tool_calls || [],
				})),
			);

			// Clear file and URL context when switching sessions
			setUrlText("");
			setUploadedFiles([]);

			// Dashboard will auto-refresh on session change via effect
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
		<div className="text-gray-800 flex flex-col h-screen overflow-hidden">
			{/* Header */}
			<header className="bg-white shadow-lg p-4 flex justify-between items-center border-b border-white/20 shrink-0 h-[50px]">
				<div className="flex items-center">
					<div className="relative">
						<i className="fas fa-brain text-2xl gradient-text mr-3" />
						<div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full blur-sm opacity-30" />
					</div>
					<h1 className="text-xl font-bold gradient-text">HackathonHero</h1>
				</div>
				<div className="flex items-center gap-3">
					<button
						onClick={() => setShowChatHistory(!showChatHistory)}
						className="lg:hidden btn-gradient p-2 rounded-lg hover:scale-105 transition-all duration-300"
						type="button"
						title="Chat History"
					>
						<i className="fas fa-history text-white text-sm" />
					</button>

					{/* Live Ollama Status and Model Picker */}
					<div className="relative model-picker-container">
						<button
							onClick={() => setShowModelPicker(!showModelPicker)}
							className={`text-sm font-medium flex items-center glass-effect px-3 py-1 rounded-full transition-all duration-300 hover:scale-105 ${
								ollamaStatus.connected
									? "text-green-600 text-readable-dark"
									: "text-red-600 text-readable-dark"
							}`}
							title="Click to change model"
							type="button"
						>
							<i
								className={`fas fa-circle text-xs mr-2 ${
									ollamaStatus.connected
										? "animate-pulse text-green-500"
										: "text-red-500"
								}`}
							/>
							{ollamaStatus.model} | Ollama
							<i className="fas fa-chevron-down text-xs ml-2" />
						</button>

						{/* Model Picker Dropdown */}
						{showModelPicker && (
							<div className="absolute top-full right-0 mt-2 bg-white rounded-lg shadow-xl dropdown-shadow border border-gray-200 py-2 min-w-48 z-50">
								<div className="px-3 py-2 text-xs text-gray-500 border-b border-gray-100">
									Select Model
								</div>
								{ollamaStatus.available_models.length > 0
									? ollamaStatus.available_models.map((model) => (
											<button
												key={model}
												onClick={() => handleModelChange(model)}
												className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition-colors ${
													ollamaStatus.model === model
														? "bg-blue-50 text-blue-600 font-medium"
														: "text-gray-700"
												}`}
												type="button"
											>
												<i
													className={`fas fa-circle text-xs mr-2 ${
														ollamaStatus.model === model
															? "text-blue-500"
															: "text-gray-300"
													}`}
												/>
												{model}
												{ollamaStatus.model === model && (
													<i className="fas fa-check text-xs ml-auto float-right mt-0.5 text-blue-500" />
												)}
											</button>
										))
									: // Fallback to hardcoded models if none available
										["gpt-oss:20b", "gpt-oss:120b"].map((model) => (
											<button
												key={model}
												onClick={() => handleModelChange(model)}
												className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition-colors ${
													ollamaStatus.model === model
														? "bg-blue-50 text-blue-600 font-medium"
														: "text-gray-700"
												}`}
												type="button"
											>
												<i
													className={`fas fa-circle text-xs mr-2 ${
														ollamaStatus.model === model
															? "text-blue-500"
															: "text-gray-300"
													}`}
												/>
												{model}
												{ollamaStatus.model === model && (
													<i className="fas fa-check text-xs ml-auto float-right mt-0.5 text-blue-500" />
												)}
											</button>
										))}
								<div className="border-t border-gray-100 mt-2 pt-2 px-3">
									<div className="text-xs text-gray-500">
										Status:{" "}
										{ollamaStatus.connected ? (
											<span className="text-green-600 font-medium">
												Connected
											</span>
										) : (
											<span className="text-red-600 font-medium">
												Disconnected
											</span>
										)}
									</div>
								</div>
							</div>
						)}
					</div>
				</div>
			</header>

			{/* Main Content */}
			<div className="flex-1 min-h-0 flex flex-col lg:flex-row p-4 gap-4 overflow-hidden">
				{/* Left Panel with glassmorphism */}
				<div className="flex flex-col w-full lg:w-1/4 h-full min-h-0 float-animation">
					{/* Chat History Sidebar */}
					<div
						className={`flex w-full ${showChatHistory ? "block" : "hidden lg:block"} mb-6 h-[50%] min-h-0`}
					>
						<ChatHistory
							currentSessionId={currentSessionId}
							onSelectSession={handleSelectSession}
							onNewChat={handleNewChat}
							onDeleteSession={handleDeleteSession}
						/>
					</div>

					{/* Context & Rules */}
					<div className="w-full flex-1 min-h-0 glass-effect-readable rounded-xl shadow-xl flex flex-col overflow-hidden">
						{/* Fixed header */}
						<div className="section-header shrink-0">
							<h2 className="text-lg font-semibold gradient-text">
								<i className="fas fa-layer-group mr-2 text-blue-500" />
								Hackathon Context
							</h2>
							{/* Context status indicator */}
							<div
								className="text-xs font-medium flex items-center gap-2"
								aria-live="polite"
								aria-busy={ragStatus.building ? "true" : "false"}
							>
								{ragStatus.building ? (
									<>
										<i className="fas fa-spinner fa-spin text-blue-500" />
										<span className="text-blue-600">
											Indexing
											{currentSessionId
												? ` (session ${currentSessionId.slice(0, 8)}…)`
												: ""}
											...
										</span>
									</>
								) : ragStatus.ready ? (
									<>
										<i className="fas fa-circle text-green-500" />
										<span className="text-green-700">
											Ready ({ragStatus.chunks} chunks)
										</span>
									</>
								) : (
									<>
										<i className="fas fa-exclamation-circle text-gray-400" />
										<span className="text-gray-600">
											No context indexed
											{currentSessionId
												? ` for session ${currentSessionId.slice(0, 8)}…`
												: ""}
										</span>
									</>
								)}
							</div>
						</div>
						{/* Scrollable content */}
						<div
							ref={contextScrollRef}
							className="flex-1 min-h-0 overflow-y-auto p-3"
						>
							<p className="text-sm text-readable-light mb-4">
								Paste rules, URLs, or drag & drop files to give the agent
								context.
							</p>

							<FileDrop
								uploadedFiles={uploadedFiles}
								setUploadedFiles={setUploadedFiles}
							/>

							<textarea
								name="user-context"
								placeholder="Or paste text/URLs here..."
								className="context-textarea w-full mt-4 border border-white/20 text-sm enhanced-input placeholder-gray-500"
								value={urlText}
								onChange={(e) => setUrlText(e.target.value)}
							/>
							<button
								onClick={setContext}
								className="context-button mt-2 btn-gradient font-bold px-4 transition-all duration-300"
								type="button"
								aria-label="Set context for this chat session"
							>
								<i className="fas fa-check-circle mr-2" />
								Set Context
							</button>
							<div className="mt-3 text-sm space-y-1">
								{uploadedFiles.length > 0 && (
									<>
										<p className="font-semibold text-readable-dark">
											Context Files:
										</p>
										{uploadedFiles.map((file, index) => (
											<div
												key={`${file.name}-${index}`}
												className="flex items-center justify-between glass-effect-readable p-2 rounded-lg border border-white/10"
											>
												<span className="text-readable-dark">{file.name}</span>
												<button
													onClick={() => {
														const newFiles = uploadedFiles.filter(
															(_, i) => i !== index,
														);
														setUploadedFiles(newFiles);
													}}
													className="ml-2 text-red-500 hover:text-red-600 transition-colors"
													type="button"
												>
													<i className="fas fa-times" />
												</button>
											</div>
										))}
									</>
								)}
							</div>
						</div>
					</div>
				</div>

				{/* Center Panel: Chat Interface with glassmorphism */}
				<div className="w-full lg:w-1/2 h-full min-h-0 glass-effect-readable rounded-xl shadow-xl flex flex-col overflow-hidden">
					<ChatBox
						messages={messages}
						onSend={sendMessage}
						isTyping={isTyping}
						setIsTyping={setIsTyping}
						onStop={stopGeneration}
						currentSessionId={currentSessionId}
						ragReady={ragStatus.ready && !ragStatus.building}
					/>
				</div>

				{/* Right Panel: Project Dashboard with glassmorphism */}
				<div className="w-full lg:w-1/4 h-full min-h-0 glass-effect-readable rounded-xl shadow-xl flex flex-col overflow-hidden float-animation">
					{/* Fixed header */}
					<div className="section-header shrink-0">
						<h2 className="text-lg font-semibold gradient-text">
							<i className="fas fa-gauge mr-2 text-purple-500" />
							Project Dashboard
						</h2>
					</div>
					{/* Scrollable content */}
					<div className="flex-1 min-h-0 overflow-y-auto p-3">
						<div className="space-y-4 text-sm">
							<div className="glass-effect-readable p-3 rounded-lg border border-white/10">
								<div className="flex items-center justify-between mb-2">
									<h3 className="font-semibold text-readable-dark">
										<i className="fas fa-lightbulb mr-2 text-yellow-500" />
										Project Idea
									</h3>
									<button
										onClick={generateProjectIdea}
										className="text-xs bg-yellow-500 hover:bg-yellow-600 text-white px-2 py-1 rounded transition-colors"
										title="Generate from chat history"
										type="button"
									>
										<i className="fas fa-magic mr-1" />
										Generate
									</button>
								</div>
								<p className="text-readable-light italic">
									{isStreamingIdea && !dashboardData.idea ? (
										<SkeletonText lines={4} />
									) : (
										dashboardData.idea
									)}
								</p>
							</div>
							<div className="glass-effect-readable p-3 rounded-lg border border-white/10">
								<div className="flex items-center justify-between mb-2">
									<h3 className="font-semibold text-readable-dark">
										<i className="fas fa-cogs mr-2 text-blue-500" />
										Tech Stack
									</h3>
									<button
										onClick={generateTechStack}
										className="text-xs bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded transition-colors"
										title="Generate from chat history"
										type="button"
									>
										<i className="fas fa-magic mr-1" />
										Generate
									</button>
								</div>
								<p className="text-readable-light italic">
									{isStreamingStack && !dashboardData.stack ? (
										<SkeletonText lines={4} />
									) : (
										dashboardData.stack
									)}
								</p>
							</div>
							<div className="glass-effect-readable p-3 rounded-lg border border-white/10">
								<h3 className="font-semibold text-readable-dark mb-2">
									<i className="fas fa-tasks mr-2 text-green-500" />
									To-Do List
								</h3>
								<TodoManager
									currentSessionId={currentSessionId}
									refreshKey={todosRefreshKey}
								/>
							</div>
							<div className="glass-effect-readable p-3 rounded-lg border border-white/10">
								<div className="flex items-center justify-between mb-2">
									<h3 className="font-semibold text-readable-dark">
										<i className="fas fa-file-alt mr-2 text-purple-500" />
										Submission Notes
									</h3>
									<button
										onClick={generateSubmissionNotes}
										className="text-xs bg-purple-500 hover:bg-purple-600 text-white px-2 py-1 rounded transition-colors"
										title="Generate from chat history"
										type="button"
									>
										<i className="fas fa-magic mr-1" />
										Generate
									</button>
								</div>
								<p className="text-readable-light italic">
									{isStreamingSummary && !dashboardData.submission ? (
										<SkeletonText lines={6} />
									) : (
										dashboardData.submission
									)}
								</p>
							</div>
						</div>
						<div className="pt-3">
							<button
								onClick={refreshDashboard}
								className="mt-2 w-full btn-gradient font-bold py-2 px-4 rounded-lg transition-all duration-300"
								type="button"
							>
								<i className="fas fa-sync-alt mr-2" />
								Update Dashboard
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}

export default App;
