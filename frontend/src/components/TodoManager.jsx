import { useCallback, useEffect, useRef, useState } from "react";

export default function TodoManager({ currentSessionId, refreshKey }) {
	const [todos, setTodos] = useState([]);
	const [newItem, setNewItem] = useState("");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);
	const [draftItems, setDraftItems] = useState({});

	const fetchTodos = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const url = new URL(`${window.location.origin}/api/todos`);
			url.searchParams.set("detailed", "true");
			if (currentSessionId)
				url.searchParams.set("session_id", currentSessionId);
			const res = await fetch(url.toString());
			if (!res.ok) throw new Error(res.statusText);
			const data = await res.json();
			setTodos(data.todos || []);
		} catch {
			setError("Failed to load todos");
		} finally {
			setLoading(false);
		}
	}, [currentSessionId]);

	const lastRefreshKeyRef = useRef(refreshKey);
	useEffect(() => {
		lastRefreshKeyRef.current = refreshKey;
		fetchTodos();
	}, [refreshKey, fetchTodos]);

	useEffect(() => {
		fetchTodos();
	}, [fetchTodos]);

	const addTodo = async (e) => {
		e.preventDefault();
		if (!newItem.trim()) return;
		const form = new FormData();
		form.append("item", newItem.trim());
		if (currentSessionId) form.append("session_id", currentSessionId);
		await fetch("/api/todos", { method: "POST", body: form });
		setNewItem("");
		fetchTodos();
	};

	const updateTodo = async (id, fields) => {
		const form = new FormData();
		for (const [k, v] of Object.entries(fields)) {
			if (v !== undefined && v !== null) form.append(k, v);
		}
		if (currentSessionId) form.append("session_id", currentSessionId);
		await fetch(`/api/todos/${id}`, { method: "PUT", body: form });
		fetchTodos();
	};

	const deleteTodo = async (id) => {
		const url = new URL(`${window.location.origin}/api/todos/${id}`);
		if (currentSessionId) url.searchParams.set("session_id", currentSessionId);
		await fetch(url.toString(), { method: "DELETE" });
		fetchTodos();
	};

	const clearAll = async () => {
		if (!window.confirm("Clear all todos for this chat session?")) return;
		if (!currentSessionId) {
			alert("Please open or start a chat session first");
			return;
		}
		const url = new URL(`${window.location.origin}/api/todos`);
		url.searchParams.set("session_id", currentSessionId);
		const res = await fetch(url.toString(), { method: "DELETE" });
		if (!res.ok) {
			const data = await res.json().catch(() => ({}));
			alert(data.error || "Failed to clear todos");
			return;
		}
		fetchTodos();
	};

	const cycleStatus = (s) => {
		if (s === "pending") return "in_progress";
		if (s === "in_progress") return "done";
		return "pending";
	};

	const handleItemChange = (id, value) => {
		setDraftItems((prev) => ({ ...prev, [id]: value }));
	};

	const handleItemBlur = async (todo) => {
		const draft = draftItems[todo.id] ?? "";
		const trimmed = draft.trim();
		const original = todo.item;
		if (!trimmed || trimmed === original) {
			setDraftItems((prev) => {
				const { [todo.id]: _omit, ...rest } = prev;
				return rest;
			});
			return;
		}
		await updateTodo(todo.id, { item: trimmed });
		setDraftItems((prev) => {
			const { [todo.id]: _omit, ...rest } = prev;
			return rest;
		});
	};

	return (
		<div className="space-y-4 text-gray-800">
			<form
				onSubmit={addTodo}
				className="flex flex-wrap gap-2 items-center bg-white/90 border border-gray-200/70 rounded-lg px-3 py-2 backdrop-blur-sm"
			>
				<div className="flex items-center gap-2 flex-grow min-w-[180px]">
					<i className="fas fa-plus text-green-600 text-sm" />
					<input
						className="flex-grow bg-transparent text-gray-800 placeholder-gray-500 text-sm focus:outline-none px-1 py-1 rounded border border-transparent focus:border-green-500/60 focus:bg-green-50/90 transition"
						placeholder="Add a task and press Enter..."
						value={newItem}
						onChange={(e) => setNewItem(e.target.value)}
					/>
				</div>
				<button
					className="text-xs font-semibold px-3 py-1.5 rounded-md bg-green-600 text-white shadow hover:bg-green-500 active:scale-95 transition disabled:opacity-40"
					type="submit"
					disabled={!newItem.trim()}
				>
					Add
				</button>
				<button
					type="button"
					onClick={clearAll}
					className="text-xs font-semibold px-3 py-1.5 rounded-md bg-gray-200 text-gray-700 hover:bg-gray-300 active:scale-95 transition"
				>
					Clear
				</button>
			</form>

			<div className="flex items-center justify-between text-[8px] uppercase tracking-wide text-gray-600">
				<span>{todos.length} tasks</span>
				<span className="flex gap-3">
					<span className="flex items-center gap-1">
						<span className="w-2 h-2 rounded-full bg-gray-400" />
						Pending
					</span>
					<span className="flex items-center gap-1">
						<span className="w-2 h-2 rounded-full bg-blue-500" />
						In Progress
					</span>
					<span className="flex items-center gap-1">
						<span className="w-2 h-2 rounded-full bg-green-500" />
						Done
					</span>
				</span>
			</div>

			{loading && <div className="text-xs text-gray-500">Loading...</div>}
			{error && <div className="text-xs text-red-600">{error}</div>}

			<ul className="space-y-2 max-h-60 overflow-y-auto pr-1">
				{todos.map((t) => {
					const statusColor =
						t.status === "pending"
							? "bg-gray-400"
							: t.status === "in_progress"
								? "bg-blue-500"
								: "bg-green-500";
					return (
						<li
							key={t.id}
							className={`group flex items-start gap-3 rounded-lg bg-white border border-gray-200/70 px-3 py-2 backdrop-blur-sm hover:border-gray-400/70 transition relative text-gray-800 ${t.status === "done" ? "opacity-70" : ""}`}
						>
							{/* Status Button */}
							<button
								type="button"
								onClick={() =>
									updateTodo(t.id, { status: cycleStatus(t.status) })
								}
								title="Cycle status"
								className={`mt-0.5 w-6 h-6 flex items-center justify-center rounded-full text-[11px] font-bold text-white shadow ring-2 ring-white/20 ${statusColor} ${t.status === "in_progress" ? "animate-pulse" : ""}`}
							>
								{t.status === "done"
									? "✓"
									: t.status === "in_progress"
										? "…"
										: ""}
							</button>

							{/* Text Input */}
							<div className="flex flex-col flex-grow min-w-0">
								<input
									value={draftItems[t.id] ?? t.item}
									onChange={(e) => handleItemChange(t.id, e.target.value)}
									onBlur={() => handleItemBlur(t)}
									className={`w-full text-sm bg-transparent text-gray-800 border-b border-transparent focus:border-blue-500/70 focus:outline-none transition placeholder-gray-400 ${t.status === "done" ? "line-through text-gray-500" : ""}`}
									placeholder="Task description"
								/>
							</div>

							{/* Delete */}
							<button
								type="button"
								onClick={() => deleteTodo(t.id)}
								title="Delete task"
								className="opacity-40 hover:opacity-100 text-red-600 hover:text-red-500 transition mt-0.5"
							>
								<i className="fas fa-times" />
							</button>

							{/* Accent bar now reflects status only */}
							<span
								className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-lg ${
									t.status === "pending"
										? "bg-gray-400"
										: t.status === "in_progress"
											? "bg-blue-500"
											: "bg-green-600"
								}`}
							/>
						</li>
					);
				})}
				{todos.length === 0 && !loading && (
					<li className="text-xs italic text-gray-500 bg-white/80 border border-gray-200/70 px-3 py-2 rounded-lg">
						No tasks yet.
					</li>
				)}
			</ul>
		</div>
	);
}
