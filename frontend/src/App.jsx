import { useCallback, useEffect, useRef, useState } from "react";
import ChatBox from "./components/ChatBox";
import ChatHistory from "./components/ChatHistory";
import ContextPanel from "./components/ContextPanel";
import ExtractionPanel from "./components/ExtractionPanel";
import Header from "./components/Header";
import ProjectDashboard from "./components/ProjectDashboard";
import useChat from "./hooks/useChat";
import useDashboard from "./hooks/useDashboard";
import useOllama from "./hooks/useOllama";
import useRag from "./hooks/useRag";

function App() {
	const [urlText, setUrlText] = useState("");
	const [uploadedFiles, setUploadedFiles] = useState([]);
	const [currentSessionId, setCurrentSessionId] = useState(null);
	const [showChatHistory, setShowChatHistory] = useState(false);
	const [showExtractionModal, setShowExtractionModal] = useState(false);
	const [todosRefreshKey, setTodosRefreshKey] = useState(0);
	const contextScrollRef = useRef(null);
	const previousFilesCountRef = useRef(0);

	const { ollamaStatus, handleModelChange, handleProviderChange } = useOllama();
	const { ragStatus, checkRagStatus } = useRag(currentSessionId);
	const {
		dashboardData,
		isStreamingIdea,
		isStreamingStack,
		isStreamingSummary,
		refreshDashboard,
		generateProjectIdea,
		generateTechStack,
		generateSubmissionNotes,
	} = useDashboard(currentSessionId);
	const {
		messages,
		setMessages,
		isTyping,
		setIsTyping,
		sendMessage,
		stopGeneration,
	} = useChat({
		currentSessionId,
		uploadedFiles,
		urlText,
		setCurrentSessionId,
	});

	// Helper component was extracted to components/SkeletonText

	const generateSessionId = useCallback(
		() =>
			globalThis?.crypto?.randomUUID
				? globalThis.crypto.randomUUID()
				: `session-${Date.now()}`,
		[],
	);

	// Ollama polling handled inside useOllama

	const refreshDashboardWithKey = useCallback(async () => {
		await refreshDashboard();
		setTodosRefreshKey((prev) => prev + 1);
	}, [refreshDashboard]);

	// Ensure a session exists even for a brand-new chat before adding context
	useEffect(() => {
		if (!currentSessionId) {
			setCurrentSessionId(generateSessionId());
		}
	}, [currentSessionId, generateSessionId]);

	// RAG status polling handled inside useRag

	// Auto-refresh dashboard on page load and when session changes
	useEffect(() => {
		if (!currentSessionId) return;
		refreshDashboardWithKey();
	}, [currentSessionId, refreshDashboardWithKey]);

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

	// Model picker handled inside Header

	// Chat streaming handled inside useChat

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

	// Dashboard streaming handled inside useDashboard

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

			// Close extraction modal when switching sessions to prevent layout issues
			setShowExtractionModal(false);

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
			<Header
				ollamaStatus={ollamaStatus}
				onToggleHistory={() => setShowChatHistory(!showChatHistory)}
				onChangeModel={handleModelChange}
				onChangeProvider={handleProviderChange}
			/>

			{/* Main Content */}
			<div className="flex-1 min-h-0 flex flex-col lg:flex-row p-4 gap-4 overflow-hidden">
				{/* Left Panel with glassmorphism */}
				<div className="flex flex-col w-full lg:w-1/4 h-full min-h-0 float-animation gap-4">
					{/* Chat History Sidebar */}
					<div
						className={`flex w-full ${showChatHistory ? "block" : "hidden lg:block"} h-[40%] min-h-0`}
					>
						<ChatHistory
							currentSessionId={currentSessionId}
							onSelectSession={handleSelectSession}
							onNewChat={handleNewChat}
							onDeleteSession={handleDeleteSession}
						/>
					</div>

					{/* Context Panel */}
					<div className="h-[25%] min-h-0">
						<ContextPanel
							ragStatus={ragStatus}
							currentSessionId={currentSessionId}
							uploadedFiles={uploadedFiles}
							setUploadedFiles={setUploadedFiles}
							urlText={urlText}
							setUrlText={setUrlText}
							setContext={setContext}
							contextScrollRef={contextScrollRef}
						/>
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
						onOpenExtractions={() => setShowExtractionModal(true)}
					/>
				</div>

				<ProjectDashboard
					dashboardData={dashboardData}
					isStreamingIdea={isStreamingIdea}
					isStreamingStack={isStreamingStack}
					isStreamingSummary={isStreamingSummary}
					generateProjectIdea={generateProjectIdea}
					generateTechStack={generateTechStack}
					generateSubmissionNotes={generateSubmissionNotes}
					refreshDashboard={refreshDashboardWithKey}
					currentSessionId={currentSessionId}
					todosRefreshKey={todosRefreshKey}
				/>
			</div>

			{/* AI Extractions Floating Modal */}
			{showExtractionModal && (
				<div className="fixed inset-0 bg-white/30 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
					<div className="glass-effect-readable rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-white/20">
						{/* Modal Header */}
						<div className="bg-white/60 flex items-center justify-between p-4 border-b border-white/20">
							<h2 className="text-xl font-semibold gradient-text flex items-center gap-2">
								<i className="fas fa-brain text-purple-500" />
								AI Extractions
							</h2>
							<button
								onClick={() => setShowExtractionModal(false)}
								className="text-readable-light hover:text-white transition-colors p-2 hover:bg-white/10 rounded-lg"
								title="Close"
								type="button"
							>
								<i className="fas fa-times text-xl" />
							</button>
						</div>

						{/* Modal Content */}
						<div className="bg-white/60 flex-1 min-h-0 overflow-hidden">
							<ExtractionPanel currentSessionId={currentSessionId} />
						</div>
					</div>
				</div>
			)}
		</div>
	);
}

export default App;
