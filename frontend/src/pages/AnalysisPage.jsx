import { useEffect, useState } from 'react';
import { FileText, FolderOpen, MessageCircle, Upload } from 'lucide-react';

import { getReviewJob, startReviewJob } from '../api/client.js';

function RiskBadge({ level }) {
  return <span className={`risk-badge ${String(level || '').toLowerCase()}`}>{level || 'UNKNOWN'}</span>;
}

function getProgressLabel(progress = 0, status = '') {
  if (status === 'COMPLETED' || progress >= 100) {
    return '완료';
  }
  if (progress <= 20) {
    return '분석 준비 중';
  }
  if (progress <= 50) {
    return '전문 에이전트 검토 중';
  }
  if (progress <= 75) {
    return '위험도 종합 중';
  }
  return '리포트 작성 중';
}

function normalizeMarkdownLine(line) {
  return line.replace(/\*\*/g, '').trim();
}

function MarkdownReport({ markdown }) {
  const lines = String(markdown || '').split(/\r?\n/);
  const elements = [];
  let listItems = [];
  let listType = 'ul';

  const flushList = () => {
    if (listItems.length === 0) {
      return;
    }
    const ListTag = listType === 'ol' ? 'ol' : 'ul';
    elements.push(
      <ListTag className="markdown-list" key={`list-${elements.length}`}>
        {listItems.map((item, index) => (
          <li key={`${item}-${index}`}>{normalizeMarkdownLine(item)}</li>
        ))}
      </ListTag>
    );
    listItems = [];
    listType = 'ul';
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(<h4 key={index}>{normalizeMarkdownLine(trimmed.slice(4))}</h4>);
      return;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(<h3 key={index}>{normalizeMarkdownLine(trimmed.slice(3))}</h3>);
      return;
    }
    if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(<h2 key={index}>{normalizeMarkdownLine(trimmed.slice(2))}</h2>);
      return;
    }
    if (trimmed.startsWith('- ')) {
      if (listItems.length > 0 && listType !== 'ul') {
        flushList();
      }
      listType = 'ul';
      listItems.push(trimmed.slice(2));
      return;
    }
    if (/^\d+\.\s+/.test(trimmed)) {
      if (listItems.length > 0 && listType !== 'ol') {
        flushList();
      }
      listType = 'ol';
      listItems.push(trimmed.replace(/^\d+\.\s+/, ''));
      return;
    }
    flushList();
    elements.push(<p key={index}>{normalizeMarkdownLine(trimmed)}</p>);
  });
  flushList();

  return <div className="markdown-report">{elements}</div>;
}

function SourcePreview({ source }) {
  const [expanded, setExpanded] = useState(false);
  const text = source.chunkText || '';
  const shouldTruncate = text.length > 300;
  const visibleText = !shouldTruncate || expanded ? text : `${text.slice(0, 300)}...`;

  return (
    <article className="source-item">
      <strong>{source.sourceTitle}</strong>
      <span className="muted">{source.sourceType}</span>
      <p>{visibleText}</p>
      {shouldTruncate && (
        <button className="text-button" type="button" onClick={() => setExpanded((current) => !current)}>
          {expanded ? '접기' : '더 보기'}
        </button>
      )}
    </article>
  );
}

function AgentTrace({ result }) {
  const agentResults = result?.agentResults || {};
  const supervisor = agentResults.supervisor || {};
  const specialistReviews = agentResults.specialistReviews || [];
  const aggregatedRisk = agentResults.aggregatedRisk || {};

  return (
    <details className="agent-trace">
      <summary>에이전트 검토 과정 보기</summary>
      <div className="agent-trace-grid">
        <div>
          <strong>Supervisor Agent</strong>
          <p className="muted">
            {(supervisor.selectedDomains || []).join(', ') || '선택된 검토 영역 정보가 없습니다.'}
          </p>
        </div>
        <div>
          <strong>Specialist Review Agent</strong>
          <ul>
            {specialistReviews.map((review) => (
              <li key={review.domain}>
                {review.domain}: {(review.findings || []).length}개 검토 항목
              </li>
            ))}
          </ul>
        </div>
        <div>
          <strong>Risk Aggregator Agent</strong>
          <p className="muted">
            {aggregatedRisk.overallRiskLevel || result.overallRiskLevel || 'UNKNOWN'}
          </p>
        </div>
        <div>
          <strong>Advisor & Report Agent</strong>
          <p className="muted">종합 검토 결과와 검색 근거를 바탕으로 리포트를 작성했습니다.</p>
        </div>
      </div>
    </details>
  );
}

export default function AnalysisPage({ navigate, contractResult, onOpenChat }) {
  const [reviewJob, setReviewJob] = useState(null);
  const [reviewError, setReviewError] = useState('');
  const [startingReview, setStartingReview] = useState(false);

  useEffect(() => {
    setReviewJob(null);
    setReviewError('');
  }, [contractResult?.contract?.contractId]);

  useEffect(() => {
    if (!reviewJob?.jobId || !contractResult?.contract?.contractId) {
      return undefined;
    }
    if (reviewJob.status !== 'PENDING' && reviewJob.status !== 'RUNNING') {
      return undefined;
    }

    const contractId = contractResult.contract.contractId;
    const intervalId = window.setInterval(async () => {
      try {
        const nextJob = await getReviewJob(contractId, reviewJob.jobId);
        setReviewJob(nextJob);
        if (nextJob.status === 'FAILED') {
          setReviewError(nextJob.error || '리포트 생성 중 오류가 발생했습니다.');
        }
      } catch (error) {
        setReviewError(error.message);
        window.clearInterval(intervalId);
      }
    }, 2000);

    return () => window.clearInterval(intervalId);
  }, [contractResult?.contract?.contractId, reviewJob?.jobId, reviewJob?.status]);

  if (!contractResult) {
    return (
      <section className="page">
        <header className="page-header">
          <h1>No analysis yet</h1>
          <p>Upload a contract or choose one from your saved contract list.</p>
        </header>
        <div className="action-row left">
          <button className="primary-button" type="button" onClick={() => navigate('upload')}>
            <Upload size={18} />
            Go to upload
          </button>
          <button className="secondary-button" type="button" onClick={() => navigate('dashboard')}>
            <FolderOpen size={18} />
            My contracts
          </button>
        </div>
      </section>
    );
  }

  const { contract, analysis } = contractResult;
  const reviewResult = reviewJob?.result;
  const progress = reviewJob?.progress || 0;
  const isReviewRunning = startingReview || reviewJob?.status === 'PENDING' || reviewJob?.status === 'RUNNING';

  const handleStartReviewJob = async () => {
    setReviewError('');
    setStartingReview(true);
    try {
      const startedJob = await startReviewJob(contract.contractId);
      setReviewJob({
        ...startedJob,
        progress: 0,
        result: null,
        error: null,
      });
    } catch (error) {
      setReviewError(error.message);
    } finally {
      setStartingReview(false);
    }
  };

  return (
    <section className="page stack">
      <header className="page-header">
        <h1>Analysis result</h1>
        <p>확인 필요 항목과 계약서에서 발견된 근거 문장을 함께 보여줍니다.</p>
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

      <section className="panel stack">
        <div className="section-title">
          <div>
            <h2>Hybrid Multi-Agent Report</h2>
            <p className="muted">전문 검토 에이전트가 계약서와 reference source를 종합해 리포트를 생성합니다.</p>
          </div>
          <button
            className="primary-button"
            type="button"
            onClick={handleStartReviewJob}
            disabled={isReviewRunning}
          >
            <FileText size={18} />
            {isReviewRunning ? '리포트 생성 중' : 'AI 종합 검토 리포트 생성'}
          </button>
        </div>

        {reviewJob && (
          <div className="review-progress">
            <div className="section-title">
              <strong>{getProgressLabel(progress, reviewJob.status)}</strong>
              <span className="muted">{reviewJob.status}</span>
            </div>
            <div className="progress-bar" aria-label="Review progress">
              <span style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
            </div>
            <p className="muted">{progress}%</p>
          </div>
        )}

        {reviewError && <p className="error-text">{reviewError}</p>}

        {reviewResult && (
          <article className="review-report stack">
            <div className="section-title">
              <h3>종합 리포트 결과</h3>
              <RiskBadge level={reviewResult.overallRiskLevel} />
            </div>
            <p>{reviewResult.summary}</p>
            <MarkdownReport markdown={reviewResult.reportMarkdown} />
            <AgentTrace result={reviewResult} />
            {(reviewResult.sources || []).length > 0 && (
              <details className="sources sources-collapsible">
                <summary>근거 sources 보기</summary>
                <div className="sources-list">
                  {(reviewResult.sources || []).slice(0, 6).map((source, index) => (
                    <SourcePreview source={source} key={`${source.sourceTitle}-${index}`} />
                  ))}
                </div>
              </details>
            )}
          </article>
        )}
      </section>

      <div className="action-row">
        <button className="secondary-button" type="button" onClick={() => navigate('upload')}>
          <Upload size={18} />
          Upload another
        </button>
        <button className="secondary-button" type="button" onClick={() => navigate('dashboard')}>
          <FolderOpen size={18} />
          My contracts
        </button>
        <button className="primary-button" type="button" onClick={onOpenChat}>
          <MessageCircle size={18} />
          Ask about this contract
        </button>
      </div>
    </section>
  );
}
