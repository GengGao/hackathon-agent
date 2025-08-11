import { useCallback, useState } from "react";

const useDashboard = (currentSessionId) => {
	const [dashboardData, setDashboardData] = useState({
		idea: "Not defined yet.",
		stack: "Not defined yet.",
		todos: ["No tasks yet."],
		submission: "No notes yet.",
	});

	const [isStreamingIdea, setIsStreamingIdea] = useState(false);
	const [isStreamingStack, setIsStreamingStack] = useState(false);
	const [isStreamingSummary, setIsStreamingSummary] = useState(false);

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
				// ignore
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
		} catch (err) {
			console.error(err);
		}
	}, [currentSessionId]);

	const streamHelper = async (url, key) => {
		const controller = new AbortController();
		try {
			setDashboardData((prev) => ({ ...prev, [key]: "" }));
			const res = await fetch(url, {
				method: "POST",
				signal: controller.signal,
				headers: { Accept: "text/event-stream" },
			});
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
								setDashboardData((prev) => ({ ...prev, [key]: content }));
							} else if (payload.type === "end") {
								ended = true;
							}
						} catch {}
					}
					idx = buffer.indexOf("\n\n");
				}
			}
			await refreshDashboard();
		} finally {
			controller.abort();
		}
	};

	const generateProjectIdea = useCallback(async () => {
		if (!currentSessionId) {
			alert("Please start a chat session first");
			return;
		}
		setIsStreamingIdea(true);
		try {
			await streamHelper(
				`/api/chat-sessions/${currentSessionId}/derive-project-idea?stream=true`,
				"idea",
			);
		} catch (error) {
			console.error("Error generating project idea:", error);
			alert("Failed to generate project idea");
		} finally {
			setIsStreamingIdea(false);
		}
	}, [currentSessionId, refreshDashboard]);

	const generateTechStack = useCallback(async () => {
		if (!currentSessionId) {
			alert("Please start a chat session first");
			return;
		}
		setIsStreamingStack(true);
		try {
			await streamHelper(
				`/api/chat-sessions/${currentSessionId}/create-tech-stack?stream=true`,
				"stack",
			);
		} catch (error) {
			console.error("Error generating tech stack:", error);
			alert("Failed to generate tech stack");
		} finally {
			setIsStreamingStack(false);
		}
	}, [currentSessionId, refreshDashboard]);

	const generateSubmissionNotes = useCallback(async () => {
		if (!currentSessionId) {
			alert("Please start a chat session first");
			return;
		}
		setIsStreamingSummary(true);
		try {
			await streamHelper(
				`/api/chat-sessions/${currentSessionId}/summarize-chat-history?stream=true`,
				"submission",
			);
		} catch (error) {
			console.error("Error generating submission notes:", error);
			alert("Failed to generate submission notes");
		} finally {
			setIsStreamingSummary(false);
		}
	}, [currentSessionId, refreshDashboard]);

	return {
		dashboardData,
		setDashboardData,
		isStreamingIdea,
		isStreamingStack,
		isStreamingSummary,
		refreshDashboard,
		generateProjectIdea,
		generateTechStack,
		generateSubmissionNotes,
	};
};

export default useDashboard;
