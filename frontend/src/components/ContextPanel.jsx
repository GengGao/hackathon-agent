import FileDrop from "./FileDrop";

export default function ContextPanel({
	ragStatus,
	currentSessionId,
	uploadedFiles,
	setUploadedFiles,
	urlText,
	setUrlText,
	setContext,
	contextScrollRef,
}) {
	return (
		<div className="w-full flex-1 min-h-0 glass-effect-readable rounded-xl shadow-xl flex flex-col overflow-hidden">
			<div className="section-header shrink-0">
				<h2 className="text-lg font-semibold gradient-text">
					<i className="fas fa-layer-group mr-2 text-blue-500" />
					Hackathon Context
				</h2>
				<div
					className="text-xs font-medium flex items-center gap-2"
					aria-live="polite"
					aria-busy={ragStatus.building ? "true" : "false"}
				>
					{ragStatus.building ? (
						<>
							<i className="fas fa-spinner fa-spin text-blue-500" />
							<span className="text-blue-600">
								Indexing
								{currentSessionId
									? ` (session ${currentSessionId.slice(0, 8)}…)`
									: ""}
								...
							</span>
						</>
					) : ragStatus.ready ? (
						<>
							<i className="fas fa-circle text-green-500" />
							<span className="text-green-700">
								Ready ({ragStatus.chunks} chunks)
							</span>
						</>
					) : (
						<>
							<i className="fas fa-exclamation-circle text-gray-400" />
							<span className="text-gray-600">
								No context indexed
								{currentSessionId
									? ` for session ${currentSessionId.slice(0, 8)}…`
									: ""}
							</span>
						</>
					)}
				</div>
			</div>

			<div
				ref={contextScrollRef}
				className="flex-1 min-h-0 overflow-y-auto p-3"
			>
				<p className="text-sm text-readable-light mb-4">
					Paste rules, URLs, or drag & drop files to give the agent context.
				</p>

				<FileDrop
					uploadedFiles={uploadedFiles}
					setUploadedFiles={setUploadedFiles}
				/>

				<textarea
					name="user-context"
					placeholder="Or paste text/URLs here..."
					className="context-textarea w-full mt-4 border border-white/20 text-sm enhanced-input placeholder-gray-500"
					value={urlText}
					onChange={(e) => setUrlText(e.target.value)}
				/>
				<button
					onClick={setContext}
					className="context-button mt-2 btn-gradient font-bold px-4 transition-all duration-300"
					type="button"
					aria-label="Set context for this chat session"
				>
					<i className="fas fa-check-circle mr-2" />
					Set Context
				</button>
				<div className="mt-3 text-sm space-y-1">
					{uploadedFiles.length > 0 && (
						<>
							<p className="font-semibold text-readable-dark">Context Files:</p>
							{uploadedFiles.map((file, index) => (
								<div
									key={`${file.name}-${index}`}
									className="flex items-center justify-between glass-effect-readable p-2 rounded-lg border border-white/10"
								>
									<span className="text-readable-dark">{file.name}</span>
									<button
										onClick={() => {
											const newFiles = uploadedFiles.filter(
												(_, i) => i !== index,
											);
											setUploadedFiles(newFiles);
										}}
										className="ml-2 text-red-500 hover:text-red-600 transition-colors"
										type="button"
									>
										<i className="fas fa-times" />
									</button>
								</div>
							))}
						</>
					)}
				</div>
			</div>
		</div>
	);
}
