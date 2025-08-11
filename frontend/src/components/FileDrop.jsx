import { useState } from "react";

export default function FileDrop({ uploadedFiles, setUploadedFiles }) {
	const [isDragOver, setIsDragOver] = useState(false);

	const handleDrop = (e) => {
		e.preventDefault();
		setIsDragOver(false);
		const files = Array.from(e.dataTransfer.files);
		handleFiles(files);
	};

	const handleDragOver = (e) => {
		e.preventDefault();
		setIsDragOver(true);
	};

	const handleDragLeave = (e) => {
		e.preventDefault();
		setIsDragOver(false);
	};

	const handleChange = (e) => {
		const files = Array.from(e.target.files);
		handleFiles(files);
	};

	const handleFiles = (files) => {
		for (const file of files) {
			if (!uploadedFiles.find((f) => f.name === file.name)) {
				const reader = new FileReader();
				reader.onload = (e) => {
					const newFile = {
						name: file.name,
						type: file.type,
						content: e.target.result,
						raw: file,
					};
					setUploadedFiles((prev) => [...prev, newFile]);
				};
				reader.readAsDataURL(file);
			}
		}
	};

	return (
		<button
			className={`w-full dropzone rounded-xl p-6 text-center flex-grow flex flex-col justify-center items-center border-2 border-dashed ${isDragOver ? "dragover" : ""}`}
			onDrop={handleDrop}
			onDragOver={handleDragOver}
			onDragLeave={handleDragLeave}
			type="button"
			tabIndex={0}
			aria-label="Drag and drop files here or use the browse button"
			onKeyDown={(e) => {
				if (e.key === "Enter" || e.key === " ") {
					const input = e.currentTarget.querySelector("input[type=file]");
					input?.click();
				}
			}}
		>
			<div className="relative mb-4">
				<i className="fas fa-cloud-upload-alt text-5xl gradient-text" />
				<div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full blur-lg opacity-30" />
			</div>
			<p className="font-semibold text-readable-dark mb-1">Drag & Drop Files</p>
			<p className="text-xs text-readable-light mb-2">
				PDF, DOCX, TXT, PNG/JPG
			</p>
			<p className="text-xs text-readable-light my-2">or</p>
			<label className="cursor-pointer btn-gradient text-white text-sm font-bold py-2 px-6 rounded-lg transition-all duration-300 hover:scale-105">
				Browse Files
				<input
					type="file"
					onChange={handleChange}
					className="hidden"
					multiple
					accept=".pdf,.docx,.png,.jpg,.jpeg,.txt"
				/>
			</label>
		</button>
	);
}
