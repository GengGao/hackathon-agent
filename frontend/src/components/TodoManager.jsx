import { useEffect, useState } from 'react';

export default function TodoManager() {
	const [todos, setTodos] = useState([]);
	const [newItem, setNewItem] = useState('');
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);

	const fetchTodos = async () => {
		setLoading(true); setError(null);
		try {
			const res = await fetch('/api/todos?detailed=true');
			if (!res.ok) throw new Error(res.statusText);
			const data = await res.json();
			setTodos(data.todos || []);
		} catch (e) {
			setError('Failed to load todos');
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => { fetchTodos(); }, []);

	const addTodo = async (e) => {
		e.preventDefault();
		if (!newItem.trim()) return;
		const form = new FormData();
		form.append('item', newItem.trim());
		await fetch('/api/todos', { method: 'POST', body: form });
		setNewItem('');
		fetchTodos();
	};

	const updateTodo = async (id, fields) => {
		const form = new FormData();
		Object.entries(fields).forEach(([k,v]) => { if (v !== undefined && v !== null) form.append(k, v); });
		await fetch(`/api/todos/${id}`, { method: 'PUT', body: form });
		fetchTodos();
	};

	const deleteTodo = async (id) => {
		await fetch(`/api/todos/${id}`, { method: 'DELETE' });
		fetchTodos();
	};

	const clearAll = async () => {
		if (!window.confirm('Clear all todos?')) return;
		await fetch('/api/todos', { method: 'DELETE' });
		fetchTodos();
	};

	const cycleStatus = (s) => {
		if (s === 'pending') return 'in_progress';
		if (s === 'in_progress') return 'done';
		return 'pending';
	};

	return (
		<div className="space-y-4 text-gray-800">
			<form onSubmit={addTodo} className="flex flex-wrap gap-2 items-center bg-white/90 border border-gray-200/70 rounded-lg px-3 py-2 backdrop-blur-sm">
				<div className="flex items-center gap-2 flex-grow min-w-[180px]">
					<i className="fas fa-plus text-green-600 text-sm" />
					<input
						className="flex-grow bg-transparent text-gray-800 placeholder-gray-500 text-sm focus:outline-none px-1 py-1 rounded border border-transparent focus:border-green-500/60 focus:bg-green-50/90 transition"
						placeholder="Add a task and press Enter..."
						value={newItem}
						onChange={(e) => setNewItem(e.target.value)}
					/>
				</div>
				<button className="text-xs font-semibold px-3 py-1.5 rounded-md bg-green-600 text-white shadow hover:bg-green-500 active:scale-95 transition disabled:opacity-40" type="submit" disabled={!newItem.trim()}>Add</button>
				<button type="button" onClick={clearAll} className="text-xs font-semibold px-3 py-1.5 rounded-md bg-gray-200 text-gray-700 hover:bg-gray-300 active:scale-95 transition">Clear</button>
			</form>

			<div className="flex items-center justify-between text-[11px] uppercase tracking-wide text-gray-600">
				<span>{todos.length} tasks</span>
				<span className="flex gap-3">
					<span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-400"></span>Pending</span>
					<span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span>In Progress</span>
					<span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span>Done</span>
				</span>
			</div>

				{loading && <div className="text-xs text-gray-500">Loading...</div>}
				{error && <div className="text-xs text-red-600">{error}</div>}

			<ul className="space-y-2 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
				{todos.map(t => {
					const statusColor = t.status==='pending' ? 'bg-gray-400' : t.status==='in_progress' ? 'bg-blue-500' : 'bg-green-500';
					return (
						<li
							key={t.id}
							className={`group flex items-start gap-3 rounded-lg bg-white border border-gray-200/70 px-3 py-2 backdrop-blur-sm hover:border-gray-400/70 transition relative text-gray-800 ${t.status==='done' ? 'opacity-70' : ''}`}
						>
							{/* Status Button */}
							<button
								type="button"
								onClick={() => updateTodo(t.id, { status: cycleStatus(t.status) })}
								title="Cycle status"
								className={`mt-0.5 w-6 h-6 flex items-center justify-center rounded-full text-[11px] font-bold text-white shadow ring-2 ring-white/20 ${statusColor} ${t.status==='in_progress' ? 'animate-pulse' : ''}`}
							>
								{t.status==='done' ? '✓' : t.status==='in_progress' ? '…' : ''}
							</button>

							{/* Text Input */}
							<div className="flex flex-col flex-grow min-w-0">
								<input
									value={t.item}
									onChange={(e) => updateTodo(t.id, { item: e.target.value })}
									className={`w-full text-sm bg-transparent text-gray-800 border-b border-transparent focus:border-blue-500/70 focus:outline-none pb-0.5 transition placeholder-gray-400 ${t.status==='done' ? 'line-through text-gray-500' : ''}`}
									placeholder="Task description"
								/>
								<div className="flex items-center gap-2 mt-1 opacity-0 group-hover:opacity-100 transition text-[10px] text-gray-500">
									<span className="flex items-center gap-1"><i className="fas fa-flag text-gray-400"></i>Priority</span>
									<select
										value={t.priority ?? 3}
										onChange={(e) => updateTodo(t.id, { priority: e.target.value })}
										className="bg-gray-100 hover:bg-gray-200 text-gray-700 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 text-[10px]"
									>
										{[1,2,3,4,5].map(p => <option key={p} value={p} className="text-black">{p}</option>)}
									</select>
								</div>
							</div>

							{/* Delete */}
								<button
									type="button"
									onClick={() => deleteTodo(t.id)}
									title="Delete task"
									className="opacity-40 hover:opacity-100 text-red-600 hover:text-red-500 transition mt-0.5"
								>
								<i className="fas fa-times"></i>
							</button>

							{/* Accent gradient bar for priority */}
							<span className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-lg ${t.priority<=2 ? 'bg-red-600' : t.priority===3 ? 'bg-amber-400' : t.priority>=4 ? 'bg-green-600' : 'bg-gray-400'}`}></span>
						</li>
					);
				})}
				{todos.length === 0 && !loading && (
					<li className="text-xs italic text-gray-500 bg-white/80 border border-gray-200/70 px-3 py-2 rounded-lg">No tasks yet.</li>
				)}
			</ul>
		</div>
	);
}
