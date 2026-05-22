import { FileCheck } from 'lucide-react';

import { useAnonymousSession } from '../hooks/useAnonymousSession.js';

export default function HomePage({ navigate }) {
  const { anonymousSessionId, loading, error } = useAnonymousSession();

  return (
    <section className="page intro-page">
      <div className="stack">
        <p className="eyebrow">Lease contract risk check MVP</p>
        <h1>LeaseGuard AI</h1>
        <p className="lead">
          Upload a contract, store an anonymous session, call the Spring Boot API,
          and verify the FastAPI stub integration flow.
        </p>
        <div className="status-line">
          <span>Session:</span>
          <code>{loading ? 'creating...' : anonymousSessionId || 'not created'}</code>
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="primary-button" type="button" onClick={() => navigate('upload')}>
          <FileCheck size={18} />
          Start upload
        </button>
      </div>
    </section>
  );
}
