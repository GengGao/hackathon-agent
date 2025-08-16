import { useCallback, useEffect, useState } from "react";

export default function ChatHistory({
	currentSessionId,
	onSelectSession,
	onNewChat,
	onDeleteSession,
}) {
	const [sessions, setSessions] = useState([]);
	const [loading, setLoading] = useState(false);
	const [editingSessionId, setEditingSessionId] = useState(null);
	const [editTitle, setEditTitle] = useState("");

	const loadSessions = useCallback(async () => {
		try {
			setLoading(true);
			const res = await fetch("/api/chat-sessions");
			if (!res.ok) throw new Error(res.statusText);
			const data = await res.json();
			const items = (data.sessions || []).slice().sort((a, b) => {
				const ad = new Date(a.updated_at || a.created_at || 0).getTime();
				const bd = new Date(b.updated_at || b.created_at || 0).getTime();
				return bd - ad; // newest first
			});
			setSessions(items);
		} catch (error) {
			console.error("Failed to load chat sessions:", error);
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		loadSessions();
	}, [loadSessions]);

	const handleEditTitle = async (sessionId, newTitle) => {
		try {
			const formData = new FormData();
			formData.append("title", newTitle);
			const res = await fetch(`/api/chat-sessions/${sessionId}/title`, {
				method: "PUT",
				body: formData,
			});
			if (!res.ok) throw new Error(res.statusText);
			await loadSessions();
			setEditingSessionId(null);
			setEditTitle("");
		} catch (error) {
			console.error("Failed to update session title:", error);
		}
	};

	const handleDeleteSession = async (sessionId) => {
		if (!confirm("Are you sure you want to delete this chat session?")) return;
		try {
			const res = await fetch(`/api/chat-sessions/${sessionId}`, {
				method: "DELETE",
			});
			if (!res.ok) throw new Error(res.statusText);
			await loadSessions();
			onDeleteSession?.(sessionId);
		} catch (error) {
			console.error("Failed to delete session:", error);
		}
	};

	const startEditing = (session) => {
		setEditingSessionId(session.session_id);
		setEditTitle(
			session.title ||
				`Chat ${new Date(session.created_at).toLocaleDateString()}`,
		);
	};

	const cancelEditing = () => {
		setEditingSessionId(null);
		setEditTitle("");
	};

	const formatDate = (dateString) => {
		const date = new Date(dateString);
		const now = new Date();
		const diffInHours = (now - date) / (1000 * 60 * 60);

		if (diffInHours < 24) {
			return date.toLocaleTimeString([], {
				hour: "2-digit",
				minute: "2-digit",
			});
		}
		if (diffInHours < 24 * 7) {
			return date.toLocaleDateString([], {
				weekday: "short",
				hour: "2-digit",
				minute: "2-digit",
			});
		}
		return date.toLocaleDateString([], { month: "short", day: "numeric" });
	};

	const getSessionTitle = (session) => {
		return session.title || `Chat ${formatDate(session.created_at)}`;
	};

	return (
		<div className="w-full glass-effect-readable rounded-xl shadow-xl flex flex-col h-full">
			<div className="section-header">
				<h2 className="text-lg font-semibold gradient-text">
					<i className="fas fa-history mr-2" />
					Chat History
				</h2>
				<button
					onClick={onNewChat}
					className="btn-gradient p-2 rounded-lg hover:scale-105 transition-all duration-300"
					title="New Chat"
					type="button"
				>
					<i className="fas fa-plus text-white text-sm" />
				</button>
			</div>

			{loading ? (
				<div className="flex items-center justify-center py-8">
					<div className="loader" />
				</div>
			) : (
				<div className="flex-grow overflow-y-auto space-y-2 p-3">
					{sessions.length === 0 ? (
						<div className="text-center py-8 text-readable-light">
							<i className="fas fa-comments text-2xl mb-2 opacity-50" />
							<p className="text-sm">No chat history yet</p>
						</div>
					) : (
						sessions.map((session) => (
							<div
								key={session.session_id}
								className={`group p-3 rounded-lg transition-all duration-200 border ${
									currentSessionId === session.session_id
										? "bg-blue-50 border-blue-200 shadow-md"
										: "glass-effect-readable border-white/10 hover:border-white/20 hover:shadow-md"
								}`}
							>
								<div className="flex items-center justify-between">
									<div className="flex-grow min-w-0">
										{editingSessionId === session.session_id ? (
											<input
												type="text"
												value={editTitle}
												onChange={(e) => setEditTitle(e.target.value)}
												onBlur={() =>
													handleEditTitle(session.session_id, editTitle)
												}
												onKeyDown={(e) => {
													if (e.key === "Enter") {
														handleEditTitle(session.session_id, editTitle);
													} else if (e.key === "Escape") {
														cancelEditing();
													}
												}}
												className="w-full bg-transparent border-none text-sm font-medium text-readable-dark focus:outline-none"
											/>
										) : (
											<button
												type="button"
												className="w-full text-left"
												onClick={() => onSelectSession(session.session_id)}
												title="Open session"
											>
												<h3 className="text-sm font-medium text-readable-dark truncate">
													{getSessionTitle(session)}
												</h3>
												<p className="text-xs text-readable-light mt-1">
													{formatDate(session.updated_at || session.created_at)}
												</p>
											</button>
										)}
									</div>

									<div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
										<button
											onClick={() => startEditing(session)}
											className="p-1 rounded hover:bg-white/20 transition-colors"
											title="Edit title"
											type="button"
										>
											<i className="fas fa-edit text-xs text-readable-light hover:text-readable-dark" />
										</button>
										<button
											onClick={() => handleDeleteSession(session.session_id)}
											className="p-1 rounded hover:bg-red-100 transition-colors"
											title="Delete session"
											type="button"
										>
											<i className="fas fa-trash text-xs text-red-500 hover:text-red-600" />
										</button>
									</div>
								</div>
							</div>
						))
					)}
				</div>
			)}

			<div className="pt-4 border-t border-white/20">
				<button
					onClick={loadSessions}
					className="w-full text-sm text-readable-light hover:text-readable-dark transition-colors flex items-center justify-center py-2"
					type="button"
				>
					<i className="fas fa-sync-alt mr-2" />
					Refresh
				</button>
			</div>
		</div>
	);
}
