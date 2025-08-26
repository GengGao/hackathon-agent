import { Streamdown } from "streamdown";
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
	const handleDownloadPack = async () => {
		if (!currentSessionId) {
			alert("Please start a chat session first");
			return;
		}
		try {
			const url = new URL(
				"/api/export/submission-pack",
				window.location.origin,
			);
			url.searchParams.set("session_id", currentSessionId);
			const res = await fetch(url.toString(), { method: "POST" });
			if (!res.ok) {
				const msg = await res.text().catch(() => "");
				let userMsg = "Failed to download submission pack";
				let parsed = null;
				try {
					parsed = JSON.parse(msg);
				} catch {
					parsed = null;
				}
				if (parsed?.error) userMsg = parsed.error;
				throw new Error(userMsg);
			}
			const blob = await res.blob();
			const a = document.createElement("a");
			const objectUrl = URL.createObjectURL(blob);
			a.href = objectUrl;
			a.download = `submission_pack_${currentSessionId?.slice(0, 8) ?? "session"}.zip`;
			document.body.appendChild(a);
			a.click();
			a.remove();
			setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
		} catch (e) {
			console.error("Failed to download pack", e);
			alert(e?.message || "Failed to download submission pack");
		}
	};
	return (
		<div className="w-full lg:w-1/4 h-full min-h-0 glass-effect-readable rounded-xl shadow-xl flex flex-col overflow-hidden float-animation">
			<div className="section-header shrink-0">
				<h2 className="text-lg font-semibold gradient-text">
					<i className="fas fa-gauge mr-2 text-purple-500" />
					Project Dashboard
				</h2>
				<button
					onClick={handleDownloadPack}
					className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 rounded transition-colors"
					title="Export submission pack (ZIP)"
					type="button"
					aria-label="Export submission pack"
				>
					<i className="fas fa-download mr-1" />
					Export
				</button>
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
							{isStreamingIdea && !dashboardData?.idea ? (
								<SkeletonText lines={4} />
							) : (
								<Streamdown
									parseIncompleteMarkdown={true}
									className="text-readable-light"
									allowedImagePrefixes={["*"]}
									allowedLinkPrefixes={["*"]}
									shikiTheme={["github-light", "github-dark"]}
								>
									{dashboardData?.idea}
								</Streamdown>
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
							{isStreamingStack && !dashboardData?.stack ? (
								<SkeletonText lines={4} />
							) : (
								<Streamdown
									parseIncompleteMarkdown={true}
									className="text-readable-light"
									allowedImagePrefixes={["*"]}
									allowedLinkPrefixes={["*"]}
									shikiTheme={["github-light", "github-dark"]}
								>
									{dashboardData?.stack}
								</Streamdown>
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
							{isStreamingSummary && !dashboardData?.submission ? (
								<SkeletonText lines={6} />
							) : (
								<Streamdown
									parseIncompleteMarkdown={true}
									className="text-readable-light"
									allowedImagePrefixes={["*"]}
									allowedLinkPrefixes={["*"]}
									shikiTheme={["github-light", "github-dark"]}
								>
									{dashboardData?.submission}
								</Streamdown>
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
