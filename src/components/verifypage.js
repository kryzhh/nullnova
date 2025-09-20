import React, { useState, useEffect } from "react";
import { Link } from 'react-router-dom'; // Make sure to import Link

const VerifyPage = () => {
    // --- LOGIC FROM MY CODE ---
    const [selectedFile, setSelectedFile] = useState(null);
    const [status, setStatus] = useState('');
    const [downloadUrl, setDownloadUrl] = useState('');

    useEffect(() => {
        document.title = "NullNova - Verify Certificate";
    }, []);

    const handleFileChange = (event) => {
        setSelectedFile(event.target.files[0]);
        setStatus('');
        setDownloadUrl('');
    };

    const handleSubmit = () => {
        if (!selectedFile) {
            setStatus('Please select a JSON file to upload.');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            sendToApi(e.target.result);
        };
        reader.readAsText(selectedFile);
    };

    const sendToApi = (jsonData) => {
        setStatus('Generating certificate, please wait...');
        setDownloadUrl('');

        const apiUrl = 'https://doqccaokp7.execute-api.ap-south-1.amazonaws.com/generate-certificate';

        fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: jsonData
        })
        .then(response => {
            if (!response.ok) { throw new Error(`Server error: ${response.status}`); }
            return response.json();
        })
        .then(data => {
            if (data.download_url) {
                setStatus('Certificate generated successfully!');
                setDownloadUrl(data.download_url);
            } else {
                throw new Error('Invalid response from server.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            setStatus('An error occurred. Please try again.');
        });
    };
    // --- END OF LOGIC FROM MY CODE ---

    return (
        <div className="verify-page">
            {/* --- STYLING FROM YOUR FRIEND'S CODE --- */}
            <style>{`
                /* (All of your friend's beautiful CSS goes here) */
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
                :root{ --bg: #02040a; --cyan: #06b6d4; --fuchsia: #d946ef; --glass: rgba(255,255,255,0.06); --glass-border: rgba(255,255,255,0.09); --muted: #9ca3af; }
                * { box-sizing: border-box; }
                body { margin: 0; font-family: 'Inter', sans-serif; background: var(--bg); color: #e6eef3; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
                .verify-page { min-height: 100vh; position: relative; overflow-x: hidden; width: 100%; }
                .verify-page::before, .verify-page::after { content: ''; position: fixed; inset: 0; z-index: 0; pointer-events: none; }
                .verify-page::before { background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAABTElEQVRoQ+2YwQ3DIAxFW1pV9T2v6/2k2o3FQqK2fWAbG6S8W6a3t0mDsoXZ7/0pCFh2ABgBqQ6ABoAJ0oF6gK8gGFdVgQwAZkA6gD6SV5x2g7KqKkPeg8W4u0wB4ApwDOgD9gQv8l7p2ZMf4w6gB7wBdD0KrQ8gB4nE0wQy1/y12kHkE8HvJp3yQByA3k9M3wWgDsR6Bq3k1oA6b0o2k0R8m6qwv4C9c2Dpc1wq3c1xq5TyPxZYpXoVQ6C3cJQqggoq8w3w4Y3v3v9AV6g6k6jvKXqkgbQwQwAMyDpQxQ3H/2h8r6MOF9y8gEwAAAAASUVORK5CYII='); opacity: 0.12; mix-blend-mode: overlay; }
                .verify-page::after { background: radial-gradient(circle at 20% 30%, rgba(6,182,212,0.15), transparent 40%), radial-gradient(circle at 80% 70%, rgba(217,70,239,0.12), transparent 40%); animation: floatVerify 25s ease-in-out infinite alternate; }
                @keyframes floatVerify { from { background: radial-gradient(circle at 20% 30%, rgba(6,182,212,0.15), transparent 40%), radial-gradient(circle at 80% 70%, rgba(217,70,239,0.12), transparent 40%); } to { background: radial-gradient(circle at 30% 20%, rgba(6,182,212,0.12), transparent 40%), radial-gradient(circle at 70% 80%, rgba(217,70,239,0.15), transparent 40%); } }
                .verify-container { position: relative; z-index: 2; max-width: 800px; margin: 0 auto; padding: 40px 20px; text-align: center; }
                .verify-header { text-align: center; margin-bottom: 40px; }
                .verify-title { font-size: 2.5rem; font-weight: 800; margin-bottom: 12px; background: linear-gradient(90deg, var(--cyan), var(--fuchsia)); -webkit-background-clip: text; background-clip: text; color: transparent; text-shadow: 0 8px 50px rgba(255,255,255,0.03); }
                .verify-subtitle { color: var(--muted); font-size: 1.1rem; line-height: 1.6; max-width: 600px; margin: 0 auto; }
                .input-section { background: var(--glass); border: 1px solid var(--glass-border); border-radius: 16px; padding: 24px; backdrop-filter: blur(12px); margin-bottom: 32px; }
                .generate-btn { padding: 14px 24px; border-radius: 12px; background: linear-gradient(90deg, var(--cyan), var(--fuchsia)); border: none; color: #021018; font-weight: 800; font-size: 1.1rem; cursor: pointer; margin-top: 16px; box-shadow: 0 8px 30px rgba(6,182,212,0.15); transition: transform 0.2s ease, box-shadow 0.2s ease; }
                .generate-btn:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(6,182,212,0.2); }
                .status-message { margin-top: 20px; font-weight: bold; color: var(--cyan); }
                .download-link { display: inline-block; margin-top: 20px; padding: 12px 25px; font-size: 1.2em; color: #021018; background-color: var(--cyan); border-radius: 10px; text-decoration: none; font-weight: bold; }
                .back-link { display: block; margin-top: 40px; color: var(--muted); text-decoration: none; }
            `}</style>
            
            {/* --- JSX STRUCTURE MERGED --- */}
            <div className="verify-container">
                <div className="verify-header">
                    <h1 className="verify-title">Generate Your Wipe Certificate</h1>
                    <p className="verify-subtitle">
                        Upload the JSON file generated by the NullNova tool to create your official, tamper-proof certificate of data destruction.
                    </p>
                </div>

                <div className="input-section">
                    <input type="file" onChange={handleFileChange} accept=".json" />
                    <button onClick={handleSubmit} className="generate-btn" style={{ marginLeft: '10px' }}>
                        Generate PDF
                    </button>
                </div>

                {/* Display status and download link */}
                {status && <div className="status-message">{status}</div>}
                {downloadUrl && (
                    <a 
                        href={downloadUrl} 
                        className="download-link"
                        target="_blank" 
                        rel="noopener noreferrer"
                    >
                        Download Your PDF Certificate
                    </a>
                )}
                
                <Link to="/" className="back-link">Go Back to Homepage</Link>
            </div>
        </div>
    );
};

export default VerifyPage;
