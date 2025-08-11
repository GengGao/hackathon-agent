import { useCallback, useState } from "react";

const useChat = ({
	currentSessionId,
	uploadedFiles,
	urlText,
	setCurrentSessionId,
}) => {
	const [messages, setMessages] = useState([]);
	const [isTyping, setIsTyping] = useState(false);
	const [abortController, setAbortController] = useState(null);

	const sendMessage = useCallback(
		async (text) => {
			const form = new FormData();
			form.append("user_input", text);
			if (uploadedFiles && uploadedFiles.length > 0) {
				for (const uf of uploadedFiles) {
					if (uf.raw instanceof File) {
						form.append("files", uf.raw);
					}
				}
			}
			if (urlText) form.append("url_text", urlText);
			if (currentSessionId) form.append("session_id", currentSessionId);

			setMessages((prev) => [...prev, { role: "user", content: text }]);
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

			const controller = new AbortController();
			setAbortController(controller);
			setIsTyping(true);

			try {
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
							setCurrentSessionId?.(data.session_id);
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
					let idx = buffer.indexOf("\n\n");
					while (idx !== -1) {
						const eventBlock = buffer.slice(0, idx);
						buffer = buffer.slice(idx + 2);
						processEvent(eventBlock);
						idx = buffer.indexOf("\n\n");
					}
				}
				if (buffer.trim()) processEvent(buffer);
				setIsTyping(false);
				setAbortController(null);
			} catch (e) {
				if (e.name === "AbortError") {
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
		},
		[currentSessionId, uploadedFiles, urlText, setCurrentSessionId],
	);

	const stopGeneration = useCallback(() => {
		if (abortController) {
			abortController.abort();
			setAbortController(null);
		}
		setIsTyping(false);
	}, [abortController]);

	return {
		messages,
		setMessages,
		isTyping,
		setIsTyping,
		sendMessage,
		stopGeneration,
	};
};

export default useChat;
