import { ArrowLeft, Upload } from 'lucide-react';
import { useState } from 'react';

import { uploadContract } from '../api/client.js';
import { useAnonymousSession } from '../hooks/useAnonymousSession.js';

export default function ContractUploadPage({ navigate, onUploadSuccess }) {
  const { anonymousSessionId, loading: sessionLoading, error: sessionError } = useAnonymousSession();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file) {
      setError('Select a PDF or TXT file first.');
      return;
    }

    setUploading(true);
    setError('');
    try {
      const result = await uploadContract(file);
      onUploadSuccess(result);
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <section className="page">
      <header className="page-header">
        <button className="text-button" type="button" onClick={() => navigate('home')}>
          <ArrowLeft size={16} />
          Back
        </button>
        <h1>Upload contract</h1>
        <p>Use a TXT or text-based PDF file. The analysis uses extracted contract text and RAG sources.</p>
      </header>

      <form className="panel stack" onSubmit={handleSubmit}>
        <div className="status-line">
          <span>Anonymous session:</span>
          <code>{sessionLoading ? 'creating...' : anonymousSessionId}</code>
        </div>
        {sessionError && <p className="error-text">{sessionError}</p>}

        <label className="upload-box">
          <Upload size={28} />
          <span>{file ? file.name : 'Choose PDF or TXT file'}</span>
          <input
            type="file"
            accept=".pdf,.txt"
            disabled={sessionLoading || uploading}
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </label>

        {error && <p className="error-text">{error}</p>}
        <button className="primary-button" type="submit" disabled={sessionLoading || uploading}>
          {uploading ? 'Uploading and analyzing...' : 'Upload and analyze'}
        </button>
      </form>
    </section>
  );
}
