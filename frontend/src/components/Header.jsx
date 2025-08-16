import { useEffect, useState } from "react";

export default function Header({
	ollamaStatus,
	onToggleHistory,
	onChangeModel,
	onChangeProvider,
}) {
	const [showModelPicker, setShowModelPicker] = useState(false);

	useEffect(() => {
		const handleClickOutside = (event) => {
			if (showModelPicker && !event.target.closest(".model-picker-container")) {
				setShowModelPicker(false);
			}
		};
		document.addEventListener("mousedown", handleClickOutside);
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, [showModelPicker]);

	return (
		<header className="bg-white shadow-lg p-4 flex justify-between items-center border-b border-white/20 shrink-0 h-[50px]">
			<div className="flex items-center">
				<div className="relative">
					<i className="fas fa-brain text-2xl gradient-text mr-3" />
					<div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full blur-sm opacity-30" />
				</div>
				<h1 className="text-xl font-bold gradient-text">HackathonHero</h1>
			</div>
			<div className="flex items-center gap-3">
				<button
					onClick={onToggleHistory}
					className="lg:hidden btn-gradient p-2 rounded-lg hover:scale-105 transition-all duration-300"
					type="button"
					title="Chat History"
				>
					<i className="fas fa-history text-white text-sm" />
				</button>

				<div className="relative model-picker-container flex items-center gap-3">
					<button
						onClick={() => setShowModelPicker(!showModelPicker)}
						className={`text-sm font-medium flex items-center glass-effect px-3 py-1 rounded-full transition-all duration-300 hover:scale-105 ${
							ollamaStatus.connected
								? "text-green-600 text-readable-dark"
								: "text-red-600 text-readable-dark"
						}`}
						title="Click to change model"
						type="button"
					>
						<i
							className={`fas fa-circle text-xs mr-2 ${
								ollamaStatus.connected
									? "animate-pulse text-green-500"
									: "text-red-500"
							}`}
						/>
						{ollamaStatus.model} | {ollamaStatus.provider ? ollamaStatus.provider : "Ollama"}
						<i className="fas fa-chevron-down text-xs ml-2" />
					</button>

					{/* Provider switch (accessible) */}
					<div className="flex items-center">
						<label className="flex items-center cursor-pointer select-none">
							<span className="mr-2 text-xs text-gray-600">Ollama</span>
							<button
								type="button"
								role="switch"
								aria-checked={ollamaStatus.provider === 'lmstudio' ? 'true' : 'false'}
								className={`relative inline-flex items-center h-6 w-11 rounded-full transition-colors focus:outline-none ${
									ollamaStatus.provider === 'lmstudio' ? 'bg-blue-600' : 'bg-gray-300'
								}`}
								onClick={() => onChangeProvider && onChangeProvider(ollamaStatus.provider === 'ollama' ? 'lmstudio' : 'ollama')}
							>
								<span className={`transform transition-transform inline-block h-5 w-5 bg-white rounded-full shadow ${ollamaStatus.provider === 'lmstudio' ? 'translate-x-5' : 'translate-x-0'}`} />
							</button>
							<span className="ml-2 text-xs text-gray-600">LMStudio</span>
						</label>
					</div>

					{showModelPicker && (
						<div className="absolute top-full right-0 mt-2 bg-white rounded-lg shadow-xl dropdown-shadow border border-gray-200 py-2 min-w-48 z-50">
							<div className="px-3 py-2 text-xs text-gray-500 border-b border-gray-100">
								Select Model
							</div>
							{ollamaStatus.available_models.length > 0
								? ollamaStatus.available_models.map((model) => (
										<button
											key={model}
											onClick={() => {
												onChangeModel(model);
												setShowModelPicker(false);
											}}
											className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition-colors ${
												ollamaStatus.model === model
													? "bg-blue-50 text-blue-600 font-medium"
													: "text-gray-700"
											}`}
											type="button"
										>
											<i
												className={`fas fa-circle text-xs mr-2 ${
													ollamaStatus.model === model
														? "text-blue-500"
														: "text-gray-300"
												}`}
											/>
											{model}
											{ollamaStatus.model === model && (
												<i className="fas fa-check text-xs ml-auto float-right mt-0.5 text-blue-500" />
											)}
										</button>
									))
								: ["gpt-oss:20b", "gpt-oss:120b"].map((model) => (
										<button
											key={model}
											onClick={() => {
												onChangeModel(model);
												setShowModelPicker(false);
											}}
											className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition-colors ${
												ollamaStatus.model === model
													? "bg-blue-50 text-blue-600 font-medium"
													: "text-gray-700"
											}`}
											type="button"
										>
											<i
												className={`fas fa-circle text-xs mr-2 ${
													ollamaStatus.model === model
														? "text-blue-500"
														: "text-gray-300"
												}`}
											/>
											{model}
											{ollamaStatus.model === model && (
												<i className="fas fa-check text-xs ml-auto float-right mt-0.5 text-blue-500" />
											)}
										</button>
									))}
							<div className="border-t border-gray-100 mt-2 pt-2 px-3">
								<div className="text-xs text-gray-500">
									Status:{" "}
									{ollamaStatus.connected ? (
										<span className="text-green-600 font-medium">
											Connected
										</span>
									) : (
										<span className="text-red-600 font-medium">
											Disconnected
										</span>
									)}
								</div>
							</div>
						</div>
					)}
				</div>
			</div>
		</header>
	);
}
