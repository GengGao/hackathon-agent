import { useState } from "react";

export default function FileDrop({ setFile, uploadedFiles, setUploadedFiles }) {
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
    files.forEach(file => {
      if (!uploadedFiles.find(f => f.name === file.name)) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const newFile = {
            name: file.name,
            type: file.type,
            content: e.target.result // Base64 encoded content
          };
          setUploadedFiles(prev => [...prev, newFile]);
          setFile(file); // Keep the original file for backward compatibility
        };
        reader.readAsDataURL(file);
      }
    });
  };

  return (
    <div
      className={`dropzone rounded-lg p-4 text-center flex-grow flex flex-col justify-center items-center ${isDragOver ? 'dragover' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <i className="fas fa-cloud-upload-alt text-4xl text-gray-400 mb-2"></i>
      <p className="font-semibold">Drag & Drop Files</p>
      <p className="text-xs text-gray-500">IMG, PDF, DOCX, TXT</p>
      <p className="text-xs text-gray-500 my-2">or</p>
      <label className="cursor-pointer bg-blue-500 text-white text-sm font-bold py-2 px-4 rounded-lg hover:bg-blue-600 transition">
        Browse Files
        <input
          type="file"
          onChange={handleChange}
          className="hidden"
          multiple
          accept=".pdf,.docx,.doc,.png,.jpg,.jpeg,.gif,.txt"
        />
      </label>
    </div>
  );
}