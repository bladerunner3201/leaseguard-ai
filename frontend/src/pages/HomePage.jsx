import { FileCheck, FolderOpen } from 'lucide-react';

import { useAnonymousSession } from '../hooks/useAnonymousSession.js';

export default function HomePage({ navigate }) {
  const { anonymousSessionId, loading, error } = useAnonymousSession();

  return (
    <section className="page intro-page">
      <div className="stack">
        <p className="eyebrow">Lease contract risk check MVP</p>
        <h1>LeaseGuard AI</h1>
        <p className="lead">
          Upload a lease contract and check risk points using the uploaded contract,
          saved chat history, and lease reference documents.
        </p>
        <div className="status-line">
          <span>Session:</span>
          <code>{loading ? 'creating...' : anonymousSessionId || 'not created'}</code>
        </div>
        {error && <p className="error-text">{error}</p>}
        <div className="action-row left">
          <button className="primary-button" type="button" onClick={() => navigate('upload')}>
            <FileCheck size={18} />
            Start upload
          </button>
          <button className="secondary-button" type="button" onClick={() => navigate('dashboard')}>
            <FolderOpen size={18} />
            My contracts
          </button>
        </div>
      </div>
    </section>
  );
}
