import { useCallback, useEffect, useRef, useState } from "react";

const useExtractions = (currentSessionId) => {
	const [extractions, setExtractions] = useState([]);
	const [isLoading, setIsLoading] = useState(false);
	const pollRef = useRef(null);

	const fetchSessionExtractions = useCallback(async () => {
		if (!currentSessionId) return;

		try {
			setIsLoading(true);
			const res = await fetch(`/api/extractions/session/${encodeURIComponent(currentSessionId)}`);
			if (!res.ok) throw new Error(res.statusText);
			const data = await res.json();
			setExtractions(data.tasks || []);
		} catch (error) {
			console.error("Failed to fetch extractions:", error);
			setExtractions([]);
		} finally {
			setIsLoading(false);
		}
	}, [currentSessionId]);

	const startConversationExtraction = useCallback(async (messageLimit = 50) => {
		if (!currentSessionId) return null;

		try {
			const res = await fetch("/api/extractions/conversation/start", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					session_id: currentSessionId,
					message_limit: messageLimit,
				}),
			});

			if (!res.ok) throw new Error(res.statusText);
			const data = await res.json();

			// Refresh extractions list
			fetchSessionExtractions();

			return data.task_id;
		} catch (error) {
			console.error("Failed to start conversation extraction:", error);
			return null;
		}
	}, [currentSessionId, fetchSessionExtractions]);

	const startProgressExtraction = useCallback(async (messageLimit = 50) => {
		if (!currentSessionId) return null;

		try {
			const res = await fetch("/api/extractions/progress/start", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					session_id: currentSessionId,
					message_limit: messageLimit,
				}),
			});

			if (!res.ok) throw new Error(res.statusText);
			const data = await res.json();

			// Refresh extractions list
			fetchSessionExtractions();

			return data.task_id;
		} catch (error) {
			console.error("Failed to start progress extraction:", error);
			return null;
		}
	}, [currentSessionId, fetchSessionExtractions]);

	const getTaskResult = useCallback(async (taskId) => {
		try {
			const res = await fetch(`/api/extractions/task/${encodeURIComponent(taskId)}/result`);
			if (!res.ok) {
				if (res.status === 202) {
					return { ok: false, error: "Task not yet completed" };
				}
				throw new Error(res.statusText);
			}
			return await res.json();
		} catch (error) {
			console.error("Failed to get task result:", error);
			return { ok: false, error: error.message };
		}
	}, []);

	// Auto-refresh extractions when session changes
	useEffect(() => {
		if (currentSessionId) {
			fetchSessionExtractions();
		} else {
			setExtractions([]);
		}
	}, [currentSessionId, fetchSessionExtractions]);

	// Poll for updates when there are active tasks
	useEffect(() => {
		const activeTasks = extractions.filter(task =>
			task.status === "queued" || task.status === "running"
		);

		if (activeTasks.length > 0) {
			if (pollRef.current) clearInterval(pollRef.current);
			pollRef.current = setInterval(() => {
				fetchSessionExtractions();
			}, 2000); // Poll every 2 seconds
		} else if (pollRef.current) {
			clearInterval(pollRef.current);
			pollRef.current = null;
		}

		return () => {
			if (pollRef.current) {
				clearInterval(pollRef.current);
				pollRef.current = null;
			}
		};
	}, [extractions, fetchSessionExtractions]);

	return {
		extractions,
		isLoading,
		startConversationExtraction,
		startProgressExtraction,
		getTaskResult,
		refreshExtractions: fetchSessionExtractions,
	};
};

export default useExtractions;