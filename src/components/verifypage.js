import React, { useState, useEffect } from "react";

const VerifyPage = () => {
  const [jsonInput, setJsonInput] = useState("");
  const [certificate, setCertificate] = useState(null);

  useEffect(() => {
    document.title = "NullNova";
  }, []);

  const generateCertificate = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      const cert = {
        title: "NullNova Data Wiping Certificate",
        timestamp: new Date().toLocaleString(),
        details: parsed,
      };
      setCertificate(cert);
    } catch (error) {
      alert("Invalid JSON. Please check your input.");
    }
  };

  return (
    <div className="verify-page">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        :root{
          --bg: #02040a;
          --cyan: #06b6d4;
          --fuchsia: #d946ef;
          --glass: rgba(255,255,255,0.06);
          --glass-border: rgba(255,255,255,0.09);
          --muted: #9ca3af;
        }

        * {
          box-sizing: border-box;
        }

        body {
          margin: 0;
          font-family: 'Inter', sans-serif;
          background: var(--bg);
          color: #e6eef3;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }

        .verify-page {
          min-height: 100vh;
          position: relative;
          overflow-x: hidden;
          width: 100%;
        }

        /* Background / aurora + grain */
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

        .verify-container {
          position: relative;
          z-index: 2;
          max-width: 800px;
          margin: 0 auto;
          padding: 40px 20px;
        }

        .verify-header {
          text-align: center;
          margin-bottom: 40px;
        }

        .verify-title {
          font-size: 2.5rem;
          font-weight: 800;
          margin-bottom: 12px;
          background: linear-gradient(90deg, var(--cyan), var(--fuchsia));
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
          text-shadow: 0 8px 50px rgba(255,255,255,0.03);
        }

        .verify-subtitle {
          color: var(--muted);
          font-size: 1.1rem;
          line-height: 1.6;
          max-width: 600px;
          margin: 0 auto;
        }

        .input-section {
          background: var(--glass);
          border: 1px solid var(--glass-border);
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

        .json-textarea {
          width: 100%;
          min-height: 200px;
          padding: 16px;
          border-radius: 12px;
          border: 1px solid var(--glass-border);
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
          border-color: var(--cyan);
          box-shadow: 0 0 0 2px rgba(6,182,212,0.2);
        }

        .json-textarea::placeholder {
          color: var(--muted);
          opacity: 0.7;
        }

        .generate-btn {
          width: 100%;
          padding: 14px 24px;
          border-radius: 12px;
          background: linear-gradient(90deg, var(--cyan), var(--fuchsia));
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

        .certificate-section {
          background: var(--glass);
          border: 1px solid var(--glass-border);
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
          color: var(--muted);
          margin-bottom: 20px;
          font-weight: 600;
        }

        .certificate-details {
          background: rgba(0,0,0,0.4);
          border: 1px solid var(--glass-border);
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
          background: var(--glass);
          border: 1px solid var(--glass-border);
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
          border-bottom: 1px solid var(--glass-border);
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
          background: linear-gradient(90deg, var(--cyan), var(--fuchsia));
          color: #021018;
          font-weight: 800;
          font-size: 14px;
          flex-shrink: 0;
          margin-top: 2px;
        }

        .instruction-text {
          color: var(--muted);
          line-height: 1.6;
        }

        .instruction-text b {
          color: #e6eef3;
          font-weight: 700;
        }

        /* Responsive */
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
        }
      `}</style>

      <div className="verify-container">
        <div className="verify-header">
          <h1 className="verify-title">Verify Data Wiping</h1>
          <p className="verify-subtitle">
            Paste the JSON log of your wiping process below to verify and
            generate a certificate that proves your data has been securely
            destroyed.
          </p>
        </div>

        <div className="input-section">
          <label className="input-label">JSON Wiping Log</label>
          <textarea
            className="json-textarea"
            rows={10}
            placeholder='Paste JSON here, e.g. { "device": "SSD-Samsung-980", "algorithm": "DoD-5220.22-M", "passes": 3, "status": "complete", "timestamp": "2024-01-15T10:30:00Z" }'
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
          />

          <button className="generate-btn" onClick={generateCertificate}>
            Generate Certificate
          </button>
        </div>

        {certificate && (
          <div className="certificate-section">
            <h2 className="certificate-title">{certificate.title}</h2>
            <p className="certificate-timestamp">
              <strong>Generated:</strong> {certificate.timestamp}
            </p>
            <pre className="certificate-details">
              {JSON.stringify(certificate.details, null, 2)}
            </pre>
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
                Paste the JSON log into the text box above.
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
