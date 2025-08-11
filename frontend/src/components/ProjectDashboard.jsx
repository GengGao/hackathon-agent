import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SkeletonText from "./SkeletonText";
import TodoManager from "./TodoManager";

export default function ProjectDashboard({
	dashboardData,
	isStreamingIdea,
	isStreamingStack,
	isStreamingSummary,
	generateProjectIdea,
	generateTechStack,
	generateSubmissionNotes,
	refreshDashboard,
	currentSessionId,
	todosRefreshKey,
}) {
	return (
		<div className="w-full lg:w-1/4 h-full min-h-0 glass-effect-readable rounded-xl shadow-xl flex flex-col overflow-hidden float-animation">
			<div className="section-header shrink-0">
				<h2 className="text-lg font-semibold gradient-text">
					<i className="fas fa-gauge mr-2 text-purple-500" />
					Project Dashboard
				</h2>
			</div>
			<div className="flex-1 min-h-0 overflow-y-auto p-3">
				<div className="space-y-4 text-sm">
					<div className="glass-effect-readable p-3 rounded-lg border border-white/10">
						<div className="flex items-center justify-between mb-2">
							<h3 className="font-semibold text-readable-dark">
								<i className="fas fa-lightbulb mr-2 text-yellow-500" />
								Project Idea
							</h3>
							<button
								onClick={generateProjectIdea}
								className="text-xs bg-yellow-500 hover:bg-yellow-600 text-white px-2 py-1 rounded transition-colors"
								title="Generate from chat history"
								type="button"
							>
								<i className="fas fa-magic mr-1" />
								Generate
							</button>
						</div>
						<p className="text-readable-light italic">
							{isStreamingIdea && !dashboardData.idea ? (
								<SkeletonText lines={4} />
							) : (
								<ReactMarkdown remarkPlugins={[remarkGfm]}>
									{dashboardData.idea}
								</ReactMarkdown>
							)}
						</p>
					</div>

					<div className="glass-effect-readable p-3 rounded-lg border border-white/10">
						<div className="flex items-center justify-between mb-2">
							<h3 className="font-semibold text-readable-dark">
								<i className="fas fa-cogs mr-2 text-blue-500" />
								Tech Stack
							</h3>
							<button
								onClick={generateTechStack}
								className="text-xs bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded transition-colors"
								title="Generate from chat history"
								type="button"
							>
								<i className="fas fa-magic mr-1" />
								Generate
							</button>
						</div>
						<p className="text-readable-light italic">
							{isStreamingStack && !dashboardData.stack ? (
								<SkeletonText lines={4} />
							) : (
								<ReactMarkdown remarkPlugins={[remarkGfm]}>
									{dashboardData.stack}
								</ReactMarkdown>
							)}
						</p>
					</div>

					<div className="glass-effect-readable p-3 rounded-lg border border-white/10">
						<h3 className="font-semibold text-readable-dark mb-2">
							<i className="fas fa-tasks mr-2 text-green-500" />
							To-Do List
						</h3>
						<TodoManager
							currentSessionId={currentSessionId}
							refreshKey={todosRefreshKey}
						/>
					</div>

					<div className="glass-effect-readable p-3 rounded-lg border border-white/10">
						<div className="flex items-center justify-between mb-2">
							<h3 className="font-semibold text-readable-dark">
								<i className="fas fa-file-alt mr-2 text-purple-500" />
								Submission Notes
							</h3>
							<button
								onClick={generateSubmissionNotes}
								className="text-xs bg-purple-500 hover:bg-purple-600 text-white px-2 py-1 rounded transition-colors"
								title="Generate from chat history"
								type="button"
							>
								<i className="fas fa-magic mr-1" />
								Generate
							</button>
						</div>
						<p className="text-readable-light italic">
							{isStreamingSummary && !dashboardData.submission ? (
								<SkeletonText lines={6} />
							) : (
								<ReactMarkdown remarkPlugins={[remarkGfm]}>
									{dashboardData.submission}
								</ReactMarkdown>
							)}
						</p>
					</div>
				</div>
				<div className="pt-3">
					<button
						onClick={refreshDashboard}
						className="mt-2 w-full btn-gradient font-bold py-2 px-4 rounded-lg transition-all duration-300"
						type="button"
					>
						<i className="fas fa-sync-alt mr-2" />
						Update Dashboard
					</button>
				</div>
			</div>
		</div>
	);
}
