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
					text: "Queued",
				};
			case "running":
				return {
					icon: "fas fa-spinner fa-spin",
					color: "text-blue-500",
					bg: "bg-blue-100",
					text: `Running (${Math.round(progress * 100)}%)`,
				};
			case "completed":
				return {
					icon: "fas fa-check-circle",
					color: "text-green-500",
					bg: "bg-green-100",
					text: "Completed",
				};
			case "failed":
				return {
					icon: "fas fa-exclamation-circle",
					color: "text-red-500",
					bg: "bg-red-100",
					text: "Failed",
				};
			default:
				return {
					icon: "fas fa-question-circle",
					color: "text-gray-500",
					bg: "bg-gray-100",
					text: "Unknown",
				};
		}
	};

	const config = getStatusConfig();

	return (
		<span
			className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.color}`}
		>
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
		return taskType === "conversation"
			? "fas fa-comments"
			: "fas fa-chart-line";
	};

	return (
		<div className="glass-effect-readable rounded-lg p-4 hover:bg-white/10 transition-all duration-300 border border-white/10">
			<div className="flex items-center justify-between mb-2">
				<div className="flex items-center gap-2">
					<i className={`${getTaskTypeIcon(task.task_type)} text-blue-400`} />
					<span className="font-medium capitalize gradient-text">
						{task.task_type} Extraction
					</span>
				</div>
				<ExtractionStatusBadge status={task.status} progress={task.progress} />
			</div>

			{task.status === "running" && (
				<div className="mb-3">
					<div className="flex justify-between text-xs text-readable-light mb-2">
						<span className="font-medium">{task.current_step}</span>
						<span className="text-purple-300">
							{task.current_step_num}/{task.total_steps}
						</span>
					</div>
					<div className="w-full bg-white/20 rounded-full h-2">
						<div
							className="bg-gradient-to-r from-blue-400 to-purple-500 h-2 rounded-full transition-all duration-300"
							style={{ width: `${task.progress * 100}%` }}
						/>
					</div>
				</div>
			)}

			<div className="flex items-center justify-between text-xs text-readable-light">
				<span className="font-medium">
					Started: {formatTime(task.started_at)}
				</span>
				<div className="flex gap-2">
					<button
						onClick={() => setShowDetails(!showDetails)}
						className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
						type="button"
					>
						{showDetails ? "Hide" : "Details"}
					</button>
					{task.status === "completed" && (
						<button
							onClick={() => onViewResult(task.task_id)}
							className="text-green-400 hover:text-green-300 font-medium transition-colors"
							type="button"
						>
							View Result
						</button>
					)}
				</div>
			</div>

			{showDetails && (
				<div className="mt-3 pt-3 border-t border-white/20 text-xs space-y-2 glass-effect-readable p-3 rounded-lg">
					<div className="flex justify-between">
						<strong className="text-purple-300">Task ID:</strong>
						<span className="text-readable-light font-mono">
							{task.task_id}
						</span>
					</div>
					<div className="flex justify-between">
						<strong className="text-purple-300">Extractor:</strong>
						<span className="text-readable-light">{task.extractor_type}</span>
					</div>
					<div className="flex justify-between">
						<strong className="text-purple-300">Created:</strong>
						<span className="text-readable-light">
							{formatTime(task.created_at)}
						</span>
					</div>
					{task.completed_at && (
						<div className="flex justify-between">
							<strong className="text-purple-300">Completed:</strong>
							<span className="text-readable-light">
								{formatTime(task.completed_at)}
							</span>
						</div>
					)}
					{task.error && (
						<div className="bg-red-500/20 border border-red-500/30 rounded p-2 mt-2">
							<strong className="text-red-400">Error:</strong>
							<span className="text-red-300 block mt-1">{task.error}</span>
						</div>
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

	const activeTasks = extractions.filter(
		(task) => task.status === "queued" || task.status === "running",
	);

	const completedTasks = extractions.filter(
		(task) => task.status === "completed",
	);
	const failedTasks = extractions.filter((task) => task.status === "failed");

	if (!currentSessionId) {
		return (
			<div className="w-full h-full flex items-center justify-center">
				<div className="text-center">
					<i className="fas fa-comments text-5xl text-purple-400 opacity-80 mb-4" />
					<p className="text-readable-light font-medium text-lg">
						Select a chat session to view extractions
					</p>
					<p className="text-readable-dark text-sm mt-2">
						Start a conversation to enable AI analysis
					</p>
				</div>
			</div>
		);
	}

	return (
		<div className="w-full h-full flex flex-col overflow-hidden">
			{/* Action Buttons */}
			<div className="p-4 glass-effect-readable border-b border-white/20">
				<div className="flex gap-2">
					<button
						onClick={() => startConversationExtraction()}
						className="text-xs px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all duration-300 hover:scale-105 flex items-center gap-1"
						disabled={isLoading}
						type="button"
					>
						<i className="fas fa-comments" />
						Analyze Conversation
					</button>
					<button
						onClick={() => startProgressExtraction()}
						className="text-xs px-3 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-all duration-300 hover:scale-105 flex items-center gap-1"
						disabled={isLoading}
						type="button"
					>
						<i className="fas fa-chart-line" />
						Track Progress
					</button>
					<button
						onClick={refreshExtractions}
						className="text-xs px-3 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-all duration-300 hover:scale-105 flex items-center gap-1"
						disabled={isLoading}
						type="button"
					>
						<i className={`fas fa-sync-alt ${isLoading ? "fa-spin" : ""}`} />
						Refresh
					</button>
				</div>
			</div>

			<div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
				{isLoading && extractions.length === 0 && (
					<div className="flex items-center justify-center py-8">
						<i className="fas fa-spinner fa-spin text-blue-400 mr-3" />
						<span className="text-readable-light font-medium">
							Loading extractions...
						</span>
					</div>
				)}

				{!isLoading && extractions.length === 0 && (
					<div className="text-center py-12">
						<i className="fas fa-brain text-5xl mb-4 text-purple-400 opacity-80" />
						<p className="text-readable-light font-medium text-lg mb-2">
							No extractions yet
						</p>
						<p className="text-readable-dark text-sm">
							Start analyzing your conversation or tracking progress
						</p>
					</div>
				)}

				{activeTasks.length > 0 && (
					<div>
						<h3 className="text-lg font-semibold gradient-text mb-3 flex items-center gap-2">
							<i className="fas fa-clock text-blue-400" />
							Active Tasks ({activeTasks.length})
						</h3>
						<div className="space-y-2">
							{activeTasks.map((task) => (
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
						<h3 className="text-lg font-semibold gradient-text mb-3 flex items-center gap-2">
							<i className="fas fa-check-circle text-green-400" />
							Completed ({completedTasks.length})
						</h3>
						<div className="space-y-3">
							{completedTasks.slice(0, 5).map((task) => (
								<ExtractionTask
									key={task.task_id}
									task={task}
									onViewResult={handleViewResult}
								/>
							))}
							{completedTasks.length > 5 && (
								<p className="text-xs text-readable-light text-center font-medium">
									... and {completedTasks.length - 5} more completed tasks
								</p>
							)}
						</div>
					</div>
				)}

				{failedTasks.length > 0 && (
					<div>
						<h3 className="text-lg font-semibold gradient-text mb-3 flex items-center gap-2">
							<i className="fas fa-exclamation-circle text-red-400" />
							Failed ({failedTasks.length})
						</h3>
						<div className="space-y-2">
							{failedTasks.slice(0, 3).map((task) => (
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
				<div className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm flex items-center justify-center z-50 p-4">
					<div className="glass-effect-readable rounded-lg p-6 max-w-4xl max-h-[80vh] overflow-y-auto">
						<div className="flex justify-between items-center mb-4">
							<h3 className="text-xl font-semibold gradient-text">
								Extraction Result
							</h3>
							<button
								onClick={() => setShowResultModal(false)}
								className="text-readable-light hover:text-white transition-colors p-2 hover:bg-white/10 rounded-lg"
								type="button"
							>
								<i className="fas fa-times text-lg" />
							</button>
						</div>
						<pre className="bg-black/30 border border-white/20 p-4 rounded-lg text-sm overflow-x-auto text-readable-light font-mono">
							{JSON.stringify(selectedResult, null, 2)}
						</pre>
					</div>
				</div>
			)}
		</div>
	);
}
