import { useCallback, useEffect, useState } from "react";

const useOllama = () => {
	const [ollamaStatus, setOllamaStatus] = useState({
		connected: false,
		model: "gpt-oss:20b",
		available_models: [],
	});

	const checkOllamaStatus = useCallback(async () => {
		try {
			const res = await fetch("/api/ollama/status");
			if (!res.ok) throw new Error(res.statusText);
			const data = await res.json();
			setOllamaStatus(data);
		} catch (error) {
			console.error("Failed to check Ollama status:", error);
			setOllamaStatus({
				connected: false,
				model: "gpt-oss:20b",
				available_models: [],
			});
		}
	}, []);

	const handleModelChange = useCallback(async (model) => {
		try {
			const formData = new FormData();
			formData.append("model", model);
			const res = await fetch("/api/ollama/model", {
				method: "POST",
				body: formData,
			});
			if (!res.ok) throw new Error(res.statusText);
			const data = await res.json();
			if (data.ok) {
				setOllamaStatus((prev) => ({ ...prev, model: data.model }));
			} else {
				console.warn("Model change rejected", data);
			}
		} catch (error) {
			console.error("Failed to change model:", error);
		}
	}, []);

	useEffect(() => {
		checkOllamaStatus();
		const intervalId = setInterval(checkOllamaStatus, 10000);
		return () => clearInterval(intervalId);
	}, [checkOllamaStatus]);

	return { ollamaStatus, checkOllamaStatus, handleModelChange };
};

export default useOllama;
