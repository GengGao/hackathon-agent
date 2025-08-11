import { useCallback, useEffect, useRef, useState } from "react";

const initialStatus = { ready: false, building: true, chunks: 0 };

const useRag = (currentSessionId) => {
	const [ragStatus, setRagStatus] = useState(initialStatus);
	const pollRef = useRef(null);

	const checkRagStatus = useCallback(
		async (sessionIdOverride) => {
			const sid = sessionIdOverride ?? currentSessionId;
			try {
				const res = await fetch(
					`/api/context/status${sid ? `?session_id=${encodeURIComponent(sid)}` : ""}`,
				);
				if (!res.ok) throw new Error(res.statusText);
				const data = await res.json();
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

	useEffect(() => {
		if (!currentSessionId) return;
		checkRagStatus(currentSessionId);
	}, [currentSessionId, checkRagStatus]);

	useEffect(() => {
		if (!currentSessionId) return;
		const shouldPoll = !ragStatus.ready || ragStatus.building;
		if (shouldPoll) {
			if (pollRef.current) clearInterval(pollRef.current);
			pollRef.current = setInterval(() => {
				checkRagStatus(currentSessionId);
			}, 1500);
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
	}, [ragStatus.ready, ragStatus.building, currentSessionId, checkRagStatus]);

	return { ragStatus, setRagStatus, checkRagStatus };
};

export default useRag;
