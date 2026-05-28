import { FileText, MessageCircle, RefreshCw, Upload } from 'lucide-react';
import { useEffect, useState } from 'react';

import { getContracts } from '../api/client.js';
import { useAnonymousSession } from '../hooks/useAnonymousSession.js';

export default function DashboardPage({ navigate, onOpenAnalysis, onOpenChat }) {
  const { anonymousSessionId, loading: sessionLoading, error: sessionError } = useAnonymousSession();
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadContracts = async () => {
    setLoading(true);
    setError('');
    try {
      setContracts(await getContracts());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!sessionLoading && anonymousSessionId) {
      loadContracts();
    }
  }, [sessionLoading, anonymousSessionId]);

  return (
    <section className="page stack">
      <header className="page-header">
        <p className="eyebrow">Anonymous contract workspace</p>
        <h1>My contracts</h1>
        <p>익명 세션에 저장된 계약서를 다시 열어 분석 결과와 채팅으로 돌아갈 수 있습니다.</p>
        <div className="status-line">
          <span>Session:</span>
          <code>{sessionLoading ? 'creating...' : anonymousSessionId || 'not created'}</code>
        </div>
      </header>

      <div className="action-row">
        <button className="primary-button" type="button" onClick={() => navigate('upload')}>
          <Upload size={18} />
          Upload contract
        </button>
        <button className="secondary-button" type="button" onClick={loadContracts} disabled={loading || sessionLoading}>
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      {sessionError && <p className="error-text">{sessionError}</p>}
      {error && <p className="error-text">{error}</p>}

      <section className="contract-list">
        {loading && <p className="muted">Loading contracts...</p>}
        {!loading && contracts.length === 0 && (
          <article className="panel stack">
            <h2>No contracts yet</h2>
            <p className="muted">Upload a TXT or text-based PDF contract to start risk checking.</p>
          </article>
        )}

        {contracts.map((contract) => (
          <article className="item-card contract-card" key={contract.contractId}>
            <div className="section-title">
              <div className="card-title">
                <FileText size={18} />
                <h2>{contract.originalFileName}</h2>
              </div>
              <span className="risk-badge">{contract.status}</span>
            </div>
            <dl className="detail-grid compact">
              <dt>ID</dt>
              <dd>{contract.contractId}</dd>
              <dt>Uploaded</dt>
              <dd>{formatDate(contract.createdAt)}</dd>
            </dl>
            <div className="action-row">
              <button className="secondary-button" type="button" onClick={() => onOpenAnalysis(contract)}>
                <FileText size={18} />
                분석 결과 보기
              </button>
              <button className="primary-button" type="button" onClick={() => onOpenChat(contract)}>
                <MessageCircle size={18} />
                질문하기
              </button>
            </div>
          </article>
        ))}
      </section>
    </section>
  );
}

function formatDate(value) {
  if (!value) {
    return '-';
  }
  return new Date(value).toLocaleString();
}
