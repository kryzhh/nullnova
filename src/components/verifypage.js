import React, { useState, useEffect } from "react";
import { Link } from 'react-router-dom';

// SVG Icons
const IconUpload = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
  </svg>
);

const IconText = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M5,4V7H10.5V19H13.5V7H19V4H5Z" />
  </svg>
);

const VerifyPage = () => {
  const [jsonInput, setJsonInput] = useState("");
  const [inputMode, setInputMode] = useState("text");
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    document.title = "NullNova";
  }, []);

  const sendToApi = (jsonData) => {
    setStatus("Generating certificate, please wait...");
    setDownloadUrl("");
    setIsGenerating(true);

    const apiUrl =
      "https://doqccaokp7.execute-api.ap-south-1.amazonaws.com/generate-certificate";

    fetch(apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: jsonData,
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        setStatus("Certificate generated successfully!");
        setIsGenerating(false);

        if (data.download_url) {
          setDownloadUrl(data.download_url);
        }
      })
      .catch((error) => {
        console.error("Error generating certificate:", error);
        setStatus("Error generating certificate. Please try again.");
        setIsGenerating(false);

        alert(`Failed to generate certificate: ${error.message}`);
      });
  };

  const handleFileUpload = (file) => {
    if (file && file.type === "application/json") {
      const reader = new FileReader();
      reader.onload = (e) => {
        setJsonInput(e.target.result);
        setStatus(""); // Clear any previous status
      };
      reader.readAsText(file);
    } else {
      alert("Please upload a valid JSON file.");
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const generateCertificate = () => {
    if (!jsonInput.trim()) {
      alert("Please provide JSON data first.");
      return;
    }

    try {
      JSON.parse(jsonInput);
      sendToApi(jsonInput);
    } catch (error) {
      alert("Invalid JSON. Please check your input.");
      setStatus("");
    }
  };

  const styles = `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: 'Inter', sans-serif;
      background: #02040a;
      color: #e6eef3;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    .verify-page {
      min-height: 100vh;
      position: relative;
      overflow-x: hidden;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .verify-page::before {
      content: '';
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
      background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAABTElEQVRoQ+2YwQ3DIAxFW1pV9T2v6/2k2o3FQqK2fWAbG6S8W6a3t0mDsoXZ7/0pCFh2ABgBqQ6ABoAJ0oF6gK8gGFdVgQwAZkA6gD6SV5x2g7KqKkPeg8W4u0wB4ApwDOgD9gQv8l7p2ZMf4w6gB7wBdD0KrQ8gB4nE0wQy1/y12kHkE8HvJp3yQByA3k9M3wWgDsR6Bq3k1oA6b0o2k0R8m6qwv4C9c2Dpc1wq3c1xq5TyPxZYpXoVQ6C3cJQqggoq8w3w4Y3v3v9AV6g6k6jvKXqkgbQwQwAMyDpQxQ3H/2h8r6MOF9y8gEwAAAAASUVORK5CYII=');
      opacity: 0.12;
      mix-blend-mode: overlay;
    }

    .verify-page::after {
      content: '';
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at 20% 30%, rgba(6,182,212,0.15), transparent 40%),
        radial-gradient(circle at 80% 70%, rgba(217,70,239,0.12), transparent 40%);
      animation: floatVerify 25s ease-in-out infinite alternate;
    }

    @keyframes floatVerify {
      from {
        background:
          radial-gradient(circle at 20% 30%, rgba(6,182,212,0.15), transparent 40%),
          radial-gradient(circle at 80% 70%, rgba(217,70,239,0.12), transparent 40%);
      }
      to {
        background:
          radial-gradient(circle at 30% 20%, rgba(6,182,212,0.12), transparent 40%),
          radial-gradient(circle at 70% 80%, rgba(217,70,239,0.15), transparent 40%);
      }
    }

    .navbar {
      position: sticky;
      top: 0;
      z-index: 100;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 20px;
      border-radius: 12px;
      background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
      border: 1px solid rgba(255,255,255,0.09);
      backdrop-filter: blur(8px);
      margin: 20px 20px 0 20px;
      max-width: 800px;
      margin-left: auto;
      margin-right: auto;
    }

    .navbar-logo {
      font-weight: 800;
      font-size: 1.25rem;
      background: linear-gradient(90deg, #06b6d4, #d946ef);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      text-decoration: none;
      cursor: pointer;
      transition: transform 0.2s ease;
    }

    .navbar-logo:hover {
      transform: scale(1.05);
    }

    .navbar-links {
      display: flex;
      gap: 16px;
      align-items: center;
    }

    .navbar-link {
      color: #9ca3af;
      text-decoration: none;
      font-weight: 600;
      font-size: 0.95rem;
      transition: color 0.2s ease;
    }

    .navbar-link:hover {
      color: #fff;
    }

    .verify-container {
      position: relative;
      z-index: 2;
      max-width: 800px;
      margin: 0 auto;
      padding: 20px 20px 60px 20px;
    }

    .verify-header {
      text-align: center;
      margin-bottom: 32px;
    }

    .verify-title {
      font-size: 2.5rem;
      font-weight: 800;
      margin-bottom: 12px;
      background: linear-gradient(90deg, #06b6d4, #d946ef);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      text-shadow: 0 8px 50px rgba(255,255,255,0.03);
    }

    .verify-subtitle {
      color: #9ca3af;
      font-size: 1.1rem;
      line-height: 1.6;
      max-width: 600px;
      margin: 0 auto;
    }

    .input-section {
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.09);
      border-radius: 16px;
      padding: 24px;
      backdrop-filter: blur(12px);
      margin-bottom: 32px;
    }

    .input-label {
      font-size: 1.1rem;
      font-weight: 700;
      margin-bottom: 12px;
      display: block;
    }

    .input-mode-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
    }

    .mode-tab {
      padding: 8px 16px;
      border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.09);
      background: rgba(255,255,255,0.02);
      color: #9ca3af;
      cursor: pointer;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
    }

    .mode-tab.active {
      background: linear-gradient(90deg, #06b6d4, #d946ef);
      color: #021018;
      border-color: transparent;
    }

    .file-upload-zone {
      border: 2px dashed rgba(255,255,255,0.09);
      border-radius: 12px;
      padding: 40px;
      text-align: center;
      background: rgba(0,0,0,0.2);
      transition: all 0.3s ease;
      cursor: pointer;
    }

    .file-upload-zone.dragging {
      border-color: #06b6d4;
      background: rgba(6,182,212,0.05);
      transform: scale(1.02);
    }

    .file-upload-zone:hover {
      border-color: #06b6d4;
      background: rgba(6,182,212,0.02);
    }

    .upload-icon {
      width: 48px;
      height: 48px;
      margin: 0 auto 16px;
      color: #06b6d4;
    }

    .upload-text {
      color: #9ca3af;
      margin-bottom: 8px;
    }

    .upload-hint {
      color: #9ca3af;
      font-size: 0.9rem;
      opacity: 0.7;
    }

    .hidden-file-input {
      display: none;
    }

    .json-textarea {
      width: 100%;
      min-height: 200px;
      padding: 16px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.09);
      background: rgba(0,0,0,0.3);
      color: #e6eef3;
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
      font-size: 14px;
      line-height: 1.5;
      resize: vertical;
      backdrop-filter: blur(8px);
    }

    .json-textarea:focus {
      outline: none;
      border-color: #06b6d4;
      box-shadow: 0 0 0 2px rgba(6,182,212,0.2);
    }

    .json-textarea::placeholder {
      color: #9ca3af;
      opacity: 0.7;
    }

    .generate-btn {
      width: 100%;
      padding: 14px 24px;
      border-radius: 12px;
      background: linear-gradient(90deg, #06b6d4, #d946ef);
      border: none;
      color: #021018;
      font-weight: 800;
      font-size: 1.1rem;
      cursor: pointer;
      margin-top: 16px;
      box-shadow: 0 8px 30px rgba(6,182,212,0.15);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .generate-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 40px rgba(6,182,212,0.2);
    }

    .generate-btn:disabled,
    .generate-btn.generating {
      opacity: 0.7;
      cursor: not-allowed;
      transform: none;
    }

    .status-message {
      margin-top: 16px;
      padding: 12px;
      border-radius: 8px;
      font-weight: 600;
      text-align: center;
    }

    .status-message.success {
      background: rgba(16, 185, 129, 0.1);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.2);
    }

    .status-message.error {
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
      border: 1px solid rgba(239, 68, 68, 0.2);
    }

    .certificate-id {
      color: #9ca3af;
      margin-bottom: 20px;
      font-weight: 600;
    }

    .download-section {
      margin-bottom: 20px;
    }

    .download-certificate-btn {
      display: inline-block;
      padding: 12px 24px;
      background: linear-gradient(90deg, #10b981, #34d399);
      color: white;
      text-decoration: none;
      border-radius: 8px;
      font-weight: 700;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);
    }

    .download-certificate-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3);
    }

    .certificate-section {
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.09);
      border-radius: 16px;
      padding: 24px;
      backdrop-filter: blur(12px);
      margin-bottom: 40px;
      animation: slideIn 0.5s ease-out;
    }

    @keyframes slideIn {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .certificate-title {
      font-size: 1.5rem;
      font-weight: 700;
      margin-bottom: 12px;
      color: #e6eef3;
    }

    .certificate-timestamp {
      color: #9ca3af;
      margin-bottom: 20px;
      font-weight: 600;
    }

    .certificate-details {
      background: rgba(0,0,0,0.4);
      border: 1px solid rgba(255,255,255,0.09);
      border-radius: 8px;
      padding: 16px;
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
      font-size: 14px;
      line-height: 1.6;
      overflow-x: auto;
      white-space: pre-wrap;
      color: #10b981;
    }

    .instructions-section {
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.09);
      border-radius: 16px;
      padding: 24px;
      backdrop-filter: blur(12px);
    }

    .instructions-title {
      font-size: 1.3rem;
      font-weight: 700;
      margin-bottom: 16px;
      color: #e6eef3;
    }

    .instructions-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .instruction-item {
      padding: 12px 0;
      border-bottom: 1px solid rgba(255,255,255,0.09);
      display: flex;
      align-items: flex-start;
      gap: 12px;
    }

    .instruction-item:last-child {
      border-bottom: none;
    }

    .instruction-number {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: linear-gradient(90deg, #06b6d4, #d946ef);
      color: #021018;
      font-weight: 800;
      font-size: 14px;
      flex-shrink: 0;
      margin-top: 2px;
    }

    .instruction-text {
      color: #9ca3af;
      line-height: 1.6;
    }

    .instruction-text b {
      color: #e6eef3;
      font-weight: 700;
    }

    @media (max-width: 768px) {
      .verify-title {
        font-size: 2rem;
      }
      
      .verify-container {
        padding: 20px 16px;
      }
      
      .input-section,
      .certificate-section,
      .instructions-section {
        padding: 20px;
      }

      .navbar {
        margin: 16px;
        margin-bottom: 0;
        padding: 12px 16px;
      }

      .navbar-links {
        gap: 12px;
      }

      .navbar-link {
        font-size: 0.9rem;
      }
    }
  `;

  return (
    <div className="verify-page">
      <style>{styles}</style>

      <nav className="navbar">
        <a href="/" className="navbar-logo">
          NullNova
        </a>
        <div className="navbar-links">
          <a className="navbar-link" href="/#features">
            Features
          </a>
          <a className="navbar-link" href="/#tools">
            Tools
          </a>
          <a className="navbar-link" href="/#about">
            About
          </a>
        </div>
      </nav>

      <div className="verify-container">
        <div className="verify-header">
          <h1 className="verify-title">Verify Data Wiping</h1>
          <p className="verify-subtitle">
            Upload a JSON file or paste the log of your wiping process to verify
            and generate a certificate that proves your data has been securely
            destroyed.
          </p>
        </div>

        <div className="input-section">
          <label className="input-label">JSON Wiping Log</label>

          <div className="input-mode-tabs">
            <button
              className={`mode-tab ${inputMode === "file" ? "active" : ""}`}
              onClick={() => setInputMode("file")}>
              <IconUpload size={16} />
              Upload File
            </button>
            <button
              className={`mode-tab ${inputMode === "text" ? "active" : ""}`}
              onClick={() => setInputMode("text")}>
              <IconText size={16} />
              Paste Text
            </button>
          </div>

          {inputMode === "file" && (
            <>
              <div
                className={`file-upload-zone ${isDragging ? "dragging" : ""}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => document.getElementById("file-input").click()}>
                <IconUpload className="upload-icon" />
                <div className="upload-text">
                  {jsonInput
                    ? "File loaded successfully! Click to change file."
                    : "Drag & drop your JSON file here"}
                </div>
                <div className="upload-hint">
                  {jsonInput ? "" : "Or click to browse files"}
                </div>
              </div>
              <input
                id="file-input"
                type="file"
                accept=".json"
                onChange={(e) => {
                  if (e.target.files[0]) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
                className="hidden-file-input"
              />
            </>
          )}

          {inputMode === "text" && (
            <textarea
              className="json-textarea"
              rows={10}
              placeholder='Paste JSON here, e.g. { "device": "SSD-Samsung-980", "algorithm": "DoD-5220.22-M", "passes": 3, "status": "complete", "timestamp": "2024-01-15T10:30:00Z" }'
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
            />
          )}

          <button
            className={`generate-btn ${isGenerating ? "generating" : ""}`}
            onClick={generateCertificate}
            disabled={isGenerating}>
            {isGenerating
              ? "Generating Certificate..."
              : "Generate Certificate"}
          </button>

          {status && (
            <div
              className={`status-message ${
                status.includes("Error") || status.includes("Failed")
                  ? "error"
                  : "success"
              }`}>
              {status}
            </div>
          )}
        </div>

        {downloadUrl && (
          <div className="certificate-section">
            <div className="download-section">
                <a
                  href={downloadUrl}
                  download
                  className="download-certificate-btn"
                  target="_blank"
                  rel="noopener noreferrer">
                  Download Certificate PDF
                </a>
              </div>
          </div>
        )}

        <div className="instructions-section">
          <h3 className="instructions-title">How to Verify</h3>
          <ol className="instructions-list">
            <li className="instruction-item">
              <span className="instruction-number">1</span>
              <span className="instruction-text">
                Run the NullNova wiping tool on your device.
              </span>
            </li>
            <li className="instruction-item">
              <span className="instruction-number">2</span>
              <span className="instruction-text">
                Save or copy the generated JSON log after wiping completes.
              </span>
            </li>
            <li className="instruction-item">
              <span className="instruction-number">3</span>
              <span className="instruction-text">
                Upload the JSON file or paste the log into the input above.
              </span>
            </li>
            <li className="instruction-item">
              <span className="instruction-number">4</span>
              <span className="instruction-text">
                Click <b>Generate Certificate</b> to verify and receive your
                wiping certificate.
              </span>
            </li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default VerifyPage;
