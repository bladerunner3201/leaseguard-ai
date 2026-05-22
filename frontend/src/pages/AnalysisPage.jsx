import { MessageCircle, Upload } from 'lucide-react';

function RiskBadge({ level }) {
  return <span className={`risk-badge ${String(level || '').toLowerCase()}`}>{level || 'UNKNOWN'}</span>;
}

export default function AnalysisPage({ navigate, contractResult }) {
  if (!contractResult) {
    return (
      <section className="page">
        <header className="page-header">
          <h1>No analysis yet</h1>
          <p>Upload a contract first to view the stub analysis response.</p>
        </header>
        <button className="primary-button" type="button" onClick={() => navigate('upload')}>
          <Upload size={18} />
          Go to upload
        </button>
      </section>
    );
  }

  const { contract, analysis } = contractResult;

  return (
    <section className="page stack">
      <header className="page-header">
        <h1>Analysis result</h1>
        <p>Contract upload and FastAPI stub analysis completed.</p>
      </header>

      <section className="panel stack">
        <h2>Contract</h2>
        <dl className="detail-grid">
          <dt>ID</dt>
          <dd>{contract.contractId}</dd>
          <dt>File</dt>
          <dd>{contract.originalFileName}</dd>
          <dt>Status</dt>
          <dd>{contract.status}</dd>
        </dl>
      </section>

      <section className="panel stack">
        <div className="section-title">
          <h2>Risk summary</h2>
          <RiskBadge level={analysis.overallRiskLevel} />
        </div>
        <p>{analysis.summary}</p>
      </section>

      <section className="stack">
        <h2>Risk items</h2>
        {(analysis.riskItems || []).map((item, index) => (
          <article className="item-card" key={`${item.category}-${index}`}>
            <div className="section-title">
              <h3>{item.title}</h3>
              <RiskBadge level={item.riskLevel} />
            </div>
            <p className="muted">{item.category}</p>
            <p>{item.description}</p>
            <blockquote>{item.evidence}</blockquote>
          </article>
        ))}
      </section>

      <div className="action-row">
        <button className="secondary-button" type="button" onClick={() => navigate('upload')}>
          <Upload size={18} />
          Upload another
        </button>
        <button className="primary-button" type="button" onClick={() => navigate('chat')}>
          <MessageCircle size={18} />
          Ask about this contract
        </button>
      </div>
    </section>
  );
}
