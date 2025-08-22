import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import remarkGfm from "remark-gfm";

export default function ChatBox({
	messages,
	onSend,
	isTyping,
	setIsTyping,
	onStop,
	currentSessionId,
	ragReady,
	onOpenExtractions,
}) {
	const [input, setInput] = useState("");
	const messagesEndRef = useRef(null);

	const scrollToBottom = useCallback(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
	}, []);

	useEffect(() => {
		const lastMessage = messages[messages.length - 1];
		if (lastMessage) {
			scrollToBottom();
		}
	}, [messages, scrollToBottom]);

	const handleSubmit = (e) => {
		e.preventDefault();
		if (!input.trim()) return;
		if (!ragReady) return; // guard if indexing not ready
		setIsTyping(true);
		onSend(input);
		setInput("");
	};

	const handleKeyDown = (e) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			handleSubmit(e);
		}
	};

	return (
		<>
			<div className="section-header">
				<h3 className="text-lg font-semibold gradient-text">
					<i className="fas fa-comments mr-2" />
					Chat Assistant
				</h3>
				<div className="flex items-center gap-2">
					{currentSessionId ? (
						<span className="text-xs text-readable-light bg-white/10 px-2 py-1 rounded-full">
							Session: {currentSessionId.slice(0, 8)}...
						</span>
					) : null}
					{onOpenExtractions && (
						<button
							onClick={onOpenExtractions}
							className="text-xs px-3 py-1 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors flex items-center gap-1"
							title="Open AI Extractions"
						>
							<i className="fas fa-brain" />
							Extractions
						</button>
					)}
				</div>
			</div>

			<div className="flex-grow p-4 overflow-y-auto">
				{messages.length === 0 ? (
					<div className="flex justify-start mb-4">
						<div className="chat-bubble chat-bubble-agent p-4 rounded-xl max-w-md">
							<p className="font-bold mb-2 gradient-text">HackathonHero</p>
							<p className="text-readable-dark">
								Hello! I'm your local hackathon assistant. To get started,
								please add the hackathon rules or your initial ideas in the
								context panel on the left. Then, let's start brainstorming!
							</p>
						</div>
					</div>
				) : null}
				{messages.map((msg, i) => (
					<div
						key={`${currentSessionId || "no-session"}-msg-${i}-${msg.role}-${(
							msg.content || ""
						).slice(0, 10)}`}
						className={`flex mb-4 ${
							msg.role === "assistant" ? "justify-start" : "justify-end"
						}`}
					>
						<div
							className={`chat-bubble p-4 rounded-xl max-w-md ${
								msg.role === "assistant"
									? "chat-bubble-agent"
									: "chat-bubble-user"
							}`}
						>
							{msg.role === "assistant" && (
								<p className="font-bold mb-2 gradient-text">HackathonHero</p>
							)}
							{msg.role === "assistant" && msg.thinking && (
								<div className="dropzone mb-3 p-3 rounded-lg">
									<div className="flex items-center mb-2">
										<i className="fas fa-brain text-purple-600 mr-2" />
										<span className="text-xs font-semibold text-purple-600">
											Thinking...
										</span>
									</div>
									<p className="text-xs text-gray-600 italic font-mono leading-relaxed">
										{msg.thinking}
									</p>
								</div>
							)}
							{msg.role === "assistant" &&
								msg.tool_calls &&
								msg.tool_calls.length > 0 && (
									<div className="mb-3 p-3 rounded-lg bg-blue-50 border border-blue-200">
										<div className="flex items-center mb-2">
											<i className="fas fa-tools text-blue-500 mr-2" />
											<span className="text-xs font-semibold text-blue-600">
												Tool Calls
											</span>
										</div>
										<ul className="text-xs text-blue-700 space-y-1">
											{msg.tool_calls.map((tc, idx) => (
												<li
													key={`tool-call-${idx}-${tc.name}-${(
														tc.arguments || ""
													).slice(0, 10)}`}
													className="font-mono truncate"
												>
													{`${tc.name}(${
														tc.arguments && tc.arguments.length > 80
															? `${tc.arguments.slice(0, 80)}…`
															: tc.arguments
													})`}
												</li>
											))}
										</ul>
									</div>
								)}
							<div className="message-content">
								{msg.role === "assistant" ? (
									<div className="text-readable-dark">
										{i === messages.length - 1 && isTyping ? (
											<div className="whitespace-pre-wrap">
												{msg.content}
												<span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse" />
											</div>
										) : (
											<ReactMarkdown
												remarkPlugins={[remarkGfm]}
												components={{
													code({ inline, className, children, ...props }) {
														const match = /language-(\w+)/.exec(
															className || "",
														);
														return !inline && match ? (
															<SyntaxHighlighter
																language={match[1]}
																PreTag="div"
																{...props}
															>
																{String(children).replace(/\n$/, "")}
															</SyntaxHighlighter>
														) : (
															<code className={className} {...props}>
																{children}
															</code>
														);
													},
												}}
											>
												{msg.content}
											</ReactMarkdown>
										)}
									</div>
								) : (
									<p className="text-white">{msg.content}</p>
								)}
							</div>
							{msg.role === "assistant" &&
								msg.rule_chunks &&
								msg.rule_chunks.length > 0 && (
									<div className="rule-chunks mt-3 text-xs text-readable-light glass-effect-readable p-2 rounded-lg border border-white/10">
										📋 Referenced rules: {msg.rule_chunks.join(", ")}
									</div>
								)}
						</div>
					</div>
				))}
				<div ref={messagesEndRef} />
			</div>

			{isTyping ? (
				<div className="p-4 text-sm text-readable-dark flex items-center glass-effect-readable mx-4 mb-4 rounded-lg border border-white/10">
					<div className="loader mr-3" />
					<span>Agent is thinking...</span>
				</div>
			) : null}

			<div className="p-4 border-t border-white/20">
				<form
					onSubmit={handleSubmit}
					className="flex items-end glass-effect-readable rounded-xl p-3 border border-white/20"
				>
					<textarea
						className="flex-grow bg-transparent border-none focus:ring-0 text-readable-dark placeholder-gray-500 enhanced-input rounded-lg px-3 py-2 resize-none min-h-[40px] max-h-[120px] overflow-y-auto"
						placeholder="Type your message here... (Shift+Enter for new line, Enter to send)"
						value={input}
						onChange={(e) => setInput(e.target.value)}
						onKeyDown={handleKeyDown}
						disabled={isTyping || !ragReady}
						aria-label="Chat input"
						aria-disabled={isTyping || !ragReady}
						rows={1}
						style={{
							height: "auto",
							minHeight: "40px",
							maxHeight: "120px",
						}}
						onInput={(e) => {
							e.target.style.height = "auto";
							e.target.style.height =
								Math.min(e.target.scrollHeight, 120) + "px";
						}}
					/>
					{isTyping ? (
						<button
							type="button"
							onClick={onStop}
							className="ml-3 bg-red-500 hover:bg-red-600 p-2 rounded-full w-10 h-10 flex items-center justify-center transition-all duration-300 hover:scale-110"
						>
							<i className="fas fa-stop text-white" />
						</button>
					) : (
						<button
							type="submit"
							className={`ml-3 p-2 rounded-full w-10 h-10 flex items-center justify-center transition-all duration-300 hover:scale-110 ${
								ragReady ? "btn-gradient" : "bg-gray-300 cursor-not-allowed"
							}`}
							aria-disabled={!ragReady}
							title={
								!ragReady
									? "Indexing... Please wait until context is ready"
									: "Send message"
							}
						>
							<i className="fas fa-paper-plane text-white" />
						</button>
					)}
				</form>
			</div>
		</>
	);
}
