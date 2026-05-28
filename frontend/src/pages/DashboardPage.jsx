import { FileText, MessageCircle, RefreshCw, RotateCcw, Trash2, Upload } from 'lucide-react';
import { useEffect, useState } from 'react';

import { deleteContract, getContracts } from '../api/client.js';
import { useAnonymousSession } from '../hooks/useAnonymousSession.js';

const RESET_MESSAGE =
  '현재 브라우저의 익명 세션을 초기화합니다. 이전 계약서 목록은 이 브라우저에서 더 이상 보이지 않습니다.';

export default function DashboardPage({ navigate, onOpenAnalysis, onOpenChat, onResetSession }) {
  const { anonymousSessionId, loading: sessionLoading, error: sessionError } = useAnonymousSession();
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deletingContractId, setDeletingContractId] = useState(null);
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

  const handleDelete = async (contract) => {
    const confirmed = window.confirm(`"${contract.originalFileName}" 계약서를 삭제할까요?`);
    if (!confirmed) {
      return;
    }

    setDeletingContractId(contract.contractId);
    setError('');
    try {
      await deleteContract(contract.contractId);
      setContracts((current) => current.filter((item) => item.contractId !== contract.contractId));
    } catch (deleteError) {
      setError(deleteError.message);
    } finally {
      setDeletingContractId(null);
    }
  };

  const handleResetSession = () => {
    if (window.confirm(RESET_MESSAGE)) {
      onResetSession();
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

        {contracts.map((contract) => {
          const deleting = deletingContractId === contract.contractId;
          return (
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
                <button
                  className="danger-button"
                  type="button"
                  disabled={deleting}
                  onClick={() => handleDelete(contract)}
                >
                  <Trash2 size={18} />
                  {deleting ? '삭제 중...' : '삭제'}
                </button>
              </div>
            </article>
          );
        })}
      </section>

      <section className="panel stack subtle-panel">
        <h2>Session</h2>
        <p className="muted">{RESET_MESSAGE}</p>
        <button className="danger-outline-button" type="button" onClick={handleResetSession}>
          <RotateCcw size={18} />
          세션 초기화
        </button>
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
