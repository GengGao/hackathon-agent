import { useState } from "react";
import useExtractions from "../hooks/useExtractions";

const ExtractionStatusBadge = ({ status, progress }) => {
	const getStatusConfig = () => {
		switch (status) {
			case "queued":
				return {
					icon: "fas fa-clock",
					color: "text-yellow-500",
					bg: "bg-yellow-100",
					text: "Queued"
				};
			case "running":
				return {
					icon: "fas fa-spinner fa-spin",
					color: "text-blue-500",
					bg: "bg-blue-100",
					text: `Running (${Math.round(progress * 100)}%)`
				};
			case "completed":
				return {
					icon: "fas fa-check-circle",
					color: "text-green-500",
					bg: "bg-green-100",
					text: "Completed"
				};
			case "failed":
				return {
					icon: "fas fa-exclamation-circle",
					color: "text-red-500",
					bg: "bg-red-100",
					text: "Failed"
				};
			default:
				return {
					icon: "fas fa-question-circle",
					color: "text-gray-500",
					bg: "bg-gray-100",
					text: "Unknown"
				};
		}
	};

	const config = getStatusConfig();

	return (
		<span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.color}`}>
			<i className={`${config.icon} mr-1`} />
			{config.text}
		</span>
	);
};

const ExtractionTask = ({ task, onViewResult }) => {
	const [showDetails, setShowDetails] = useState(false);

	const formatTime = (isoString) => {
		if (!isoString) return "N/A";
		return new Date(isoString).toLocaleTimeString();
	};

	const getTaskTypeIcon = (taskType) => {
		return taskType === "conversation" ? "fas fa-comments" : "fas fa-chart-line";
	};

	return (
		<div className="border border-white/20 rounded-lg p-3 glass-effect-readable">
			<div className="flex items-center justify-between mb-2">
				<div className="flex items-center gap-2">
					<i className={`${getTaskTypeIcon(task.task_type)} text-blue-500`} />
					<span className="font-medium capitalize">
						{task.task_type} Extraction
					</span>
				</div>
				<ExtractionStatusBadge status={task.status} progress={task.progress} />
			</div>

			{task.status === "running" && (
				<div className="mb-2">
					<div className="flex justify-between text-xs text-gray-600 mb-1">
						<span>{task.current_step}</span>
						<span>{task.current_step_num}/{task.total_steps}</span>
					</div>
					<div className="w-full bg-gray-200 rounded-full h-2">
						<div
							className="bg-blue-500 h-2 rounded-full transition-all duration-300"
							style={{ width: `${task.progress * 100}%` }}
						/>
					</div>
				</div>
			)}

			<div className="flex items-center justify-between text-xs text-gray-500">
				<span>Started: {formatTime(task.started_at)}</span>
				<div className="flex gap-2">
					<button
						onClick={() => setShowDetails(!showDetails)}
						className="text-blue-500 hover:text-blue-600"
					>
						{showDetails ? "Hide" : "Details"}
					</button>
					{task.status === "completed" && (
						<button
							onClick={() => onViewResult(task.task_id)}
							className="text-green-500 hover:text-green-600"
						>
							View Result
						</button>
					)}
				</div>
			</div>

			{showDetails && (
				<div className="mt-2 pt-2 border-t border-white/10 text-xs space-y-1">
					<div><strong>Task ID:</strong> {task.task_id}</div>
					<div><strong>Extractor:</strong> {task.extractor_type}</div>
					<div><strong>Created:</strong> {formatTime(task.created_at)}</div>
					{task.completed_at && (
						<div><strong>Completed:</strong> {formatTime(task.completed_at)}</div>
					)}
					{task.error && (
						<div className="text-red-500"><strong>Error:</strong> {task.error}</div>
					)}
				</div>
			)}
		</div>
	);
};

export default function ExtractionPanel({ currentSessionId }) {
	const {
		extractions,
		isLoading,
		startConversationExtraction,
		startProgressExtraction,
		getTaskResult,
		refreshExtractions,
	} = useExtractions(currentSessionId);

	const [selectedResult, setSelectedResult] = useState(null);
	const [showResultModal, setShowResultModal] = useState(false);

	const handleViewResult = async (taskId) => {
		const result = await getTaskResult(taskId);
		setSelectedResult(result);
		setShowResultModal(true);
	};

	const activeTasks = extractions.filter(task =>
		task.status === "queued" || task.status === "running"
	);

	const completedTasks = extractions.filter(task => task.status === "completed");
	const failedTasks = extractions.filter(task => task.status === "failed");

	if (!currentSessionId) {
		return (
			<div className="w-full flex-1 min-h-0 glass-effect-readable rounded-xl shadow-xl flex flex-col overflow-hidden">
				<div className="section-header shrink-0">
					<h2 className="text-lg font-semibold gradient-text">
						<i className="fas fa-brain mr-2 text-purple-500" />
						AI Extractions
					</h2>
				</div>
				<div className="flex-1 flex items-center justify-center text-gray-500">
					<p>Select a chat session to view extractions</p>
				</div>
			</div>
		);
	}

	return (
		<div className="w-full flex-1 min-h-0 glass-effect-readable rounded-xl shadow-xl flex flex-col overflow-hidden">
			<div className="section-header shrink-0">
				<h2 className="text-lg font-semibold gradient-text">
					<i className="fas fa-brain mr-2 text-purple-500" />
					AI Extractions
				</h2>
				<div className="flex gap-2">
					<button
						onClick={() => startConversationExtraction()}
						className="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
						disabled={isLoading}
					>
						<i className="fas fa-comments mr-1" />
						Analyze Conversation
					</button>
					<button
						onClick={() => startProgressExtraction()}
						className="text-xs px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
						disabled={isLoading}
					>
						<i className="fas fa-chart-line mr-1" />
						Track Progress
					</button>
					<button
						onClick={refreshExtractions}
						className="text-xs px-2 py-1 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
						disabled={isLoading}
					>
						<i className={`fas fa-sync-alt ${isLoading ? "fa-spin" : ""} mr-1`} />
						Refresh
					</button>
				</div>
			</div>

			<div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-3">
				{isLoading && extractions.length === 0 && (
					<div className="flex items-center justify-center py-8">
						<i className="fas fa-spinner fa-spin text-blue-500 mr-2" />
						<span>Loading extractions...</span>
					</div>
				)}

				{!isLoading && extractions.length === 0 && (
					<div className="text-center py-8 text-gray-500">
						<i className="fas fa-brain text-4xl mb-4 opacity-50" />
						<p>No extractions yet</p>
						<p className="text-sm">Start analyzing your conversation or tracking progress</p>
					</div>
				)}

				{activeTasks.length > 0 && (
					<div>
						<h3 className="text-sm font-semibold text-gray-700 mb-2">
							<i className="fas fa-clock mr-1" />
							Active Tasks ({activeTasks.length})
						</h3>
						<div className="space-y-2">
							{activeTasks.map(task => (
								<ExtractionTask
									key={task.task_id}
									task={task}
									onViewResult={handleViewResult}
								/>
							))}
						</div>
					</div>
				)}

				{completedTasks.length > 0 && (
					<div>
						<h3 className="text-sm font-semibold text-gray-700 mb-2">
							<i className="fas fa-check-circle mr-1" />
							Completed ({completedTasks.length})
						</h3>
						<div className="space-y-2">
							{completedTasks.slice(0, 5).map(task => (
								<ExtractionTask
									key={task.task_id}
									task={task}
									onViewResult={handleViewResult}
								/>
							))}
							{completedTasks.length > 5 && (
								<p className="text-xs text-gray-500 text-center">
									... and {completedTasks.length - 5} more
								</p>
							)}
						</div>
					</div>
				)}

				{failedTasks.length > 0 && (
					<div>
						<h3 className="text-sm font-semibold text-gray-700 mb-2">
							<i className="fas fa-exclamation-circle mr-1" />
							Failed ({failedTasks.length})
						</h3>
						<div className="space-y-2">
							{failedTasks.slice(0, 3).map(task => (
								<ExtractionTask
									key={task.task_id}
									task={task}
									onViewResult={handleViewResult}
								/>
							))}
						</div>
					</div>
				)}
			</div>

			{/* Result Modal */}
			{showResultModal && selectedResult && (
				<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
					<div className="bg-white rounded-lg p-6 max-w-4xl max-h-[80vh] overflow-y-auto">
						<div className="flex justify-between items-center mb-4">
							<h3 className="text-lg font-semibold">Extraction Result</h3>
							<button
								onClick={() => setShowResultModal(false)}
								className="text-gray-500 hover:text-gray-700"
							>
								<i className="fas fa-times" />
							</button>
						</div>
						<pre className="bg-gray-100 p-4 rounded text-sm overflow-x-auto">
							{JSON.stringify(selectedResult, null, 2)}
						</pre>
					</div>
				</div>
			)}
		</div>
	);
}