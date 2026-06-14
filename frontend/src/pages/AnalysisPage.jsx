import { useEffect, useState } from 'react';
import { Download, FileText, FolderOpen, MessageCircle, Upload } from 'lucide-react';

import { getReviewJob, getReviewReport, REVIEW_JOB_STORAGE_PREFIX, startReviewJob } from '../api/client.js';

const REPORT_CAUTION_TEXT = '본 리포트는 법률 자문이 아니라 참고용 위험 점검입니다.';

function RiskBadge({ level }) {
  return <span className={`risk-badge ${String(level || '').toLowerCase()}`}>{level || 'UNKNOWN'}</span>;
}

function getReviewJobStorageKey(contractId) {
  return `${REVIEW_JOB_STORAGE_PREFIX}${contractId}`;
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

function stripMarkdown(markdown) {
  return String(markdown || '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*[-*]\s+/gm, '- ')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
    .trim();
}

function downloadTextFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function buildReportDownloadContent({ contract, result, format }) {
  const generatedAt = new Date().toLocaleString('ko-KR');
  const header = [
    '# LeaseGuard AI 멀티에이전트 종합 검토 리포트',
    '',
    `- 생성일시: ${generatedAt}`,
    `- 계약서 파일명: ${contract?.originalFileName || '알 수 없음'}`,
    `- 계약서 ID: ${contract?.contractId || '알 수 없음'}`,
    `- 전체 위험도: ${result?.overallRiskLevel || 'UNKNOWN'}`,
    result?.createdAt ? `- 저장일시: ${new Date(result.createdAt).toLocaleString('ko-KR')}` : null,
    result?.updatedAt ? `- 마지막 갱신: ${new Date(result.updatedAt).toLocaleString('ko-KR')}` : null,
    '',
    '## 요약',
    result?.summary || '',
    '',
    '## 리포트 본문',
    result?.reportMarkdown || '',
    '',
    '## 주의 문구',
    REPORT_CAUTION_TEXT,
    '',
  ].filter((line) => line !== null).join('\n');

  return format === 'txt' ? stripMarkdown(header) : header;
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

function ReportDownloadPanel({ contract, result }) {
  const [format, setFormat] = useState('markdown');

  const handleDownload = () => {
    if (!result) {
      return;
    }
    const contractId = contract?.contractId || 'unknown';
    if (format === 'pdf') {
      window.print();
      return;
    }
    if (format === 'txt') {
      const content = buildReportDownloadContent({ contract, result, format: 'txt' });
      downloadTextFile(`leaseguard-review-contract-${contractId}.txt`, content, 'text/plain');
      return;
    }
    const content = buildReportDownloadContent({ contract, result, format: 'markdown' });
    downloadTextFile(`leaseguard-review-contract-${contractId}.md`, content, 'text/markdown');
  };

  return (
    <section className="report-download no-print">
      <div>
        <h3>리포트 다운로드</h3>
        <p className="muted">저장된 종합 리포트를 Markdown, TXT, PDF 형식으로 저장할 수 있습니다.</p>
      </div>
      <div className="download-controls">
        <label>
          <span className="sr-only">다운로드 형식</span>
          <select value={format} onChange={(event) => setFormat(event.target.value)}>
            <option value="markdown">Markdown</option>
            <option value="txt">TXT</option>
            <option value="pdf">PDF</option>
          </select>
        </label>
        <button className="secondary-button" type="button" onClick={handleDownload}>
          <Download size={18} />
          다운로드
        </button>
      </div>
    </section>
  );
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
    <details className="agent-trace no-print">
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
  const [savedReviewReport, setSavedReviewReport] = useState(null);
  const [reviewJob, setReviewJob] = useState(null);
  const [reviewError, setReviewError] = useState('');
  const [loadingSavedReport, setLoadingSavedReport] = useState(false);
  const [startingReview, setStartingReview] = useState(false);

  const contractId = contractResult?.contract?.contractId;

  useEffect(() => {
    setSavedReviewReport(null);
    setReviewJob(null);
    setReviewError('');

    if (!contractId) {
      return;
    }

    let cancelled = false;
    const loadSavedReport = async () => {
      setLoadingSavedReport(true);
      try {
        const report = await getReviewReport(contractId);
        if (!cancelled) {
          setSavedReviewReport(report);
        }
      } catch {
        if (!cancelled) {
          setSavedReviewReport(null);
        }
      } finally {
        if (!cancelled) {
          setLoadingSavedReport(false);
        }
      }
    };

    loadSavedReport();

    const storedJobId = localStorage.getItem(`${REVIEW_JOB_STORAGE_PREFIX}${contractId}`);
    if (storedJobId) {
      setReviewJob({
        jobId: storedJobId,
        status: 'RUNNING',
        progress: 0,
        result: null,
        savedReviewReport: null,
        error: null,
      });
    }

    return () => {
      cancelled = true;
    };
  }, [contractId]);

  useEffect(() => {
    if (!reviewJob?.jobId || !contractId) {
      return undefined;
    }
    if (reviewJob.status !== 'PENDING' && reviewJob.status !== 'RUNNING') {
      return undefined;
    }

    const storageKey = `${REVIEW_JOB_STORAGE_PREFIX}${contractId}`;
    const intervalId = window.setInterval(async () => {
      try {
        const nextJob = await getReviewJob(contractId, reviewJob.jobId);
        setReviewJob(nextJob);

        if (nextJob.savedReviewReport) {
          setSavedReviewReport(nextJob.savedReviewReport);
        }

        if (nextJob.status === 'COMPLETED') {
          localStorage.removeItem(storageKey);
        }

        if (nextJob.status === 'FAILED') {
          localStorage.removeItem(storageKey);
          setReviewError(nextJob.error || '새 리포트 생성에 실패했습니다. 기존 리포트를 계속 표시합니다.');
          if (nextJob.savedReviewReport) {
            setSavedReviewReport(nextJob.savedReviewReport);
          }
        }
      } catch (error) {
        localStorage.removeItem(storageKey);
        setReviewError(error.message || '진행 중이던 리포트 생성 상태를 확인할 수 없습니다.');
        window.clearInterval(intervalId);
      }
    }, 2000);

    return () => window.clearInterval(intervalId);
  }, [contractId, reviewJob?.jobId, reviewJob?.status]);

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
  const reviewResult = savedReviewReport;
  const progress = reviewJob?.progress || 0;
  const isReviewRunning = startingReview || reviewJob?.status === 'PENDING' || reviewJob?.status === 'RUNNING';

  const handleStartReviewJob = async () => {
    if (savedReviewReport) {
      const confirmed = window.confirm('기존 리포트를 새 분석 결과로 갱신합니다. 다시 생성하시겠습니까?');
      if (!confirmed) {
        return;
      }
    }

    setReviewError('');
    setStartingReview(true);
    try {
      const startedJob = await startReviewJob(contract.contractId);
      localStorage.setItem(`${REVIEW_JOB_STORAGE_PREFIX}${contract.contractId}`, startedJob.jobId);
      setReviewJob({
        ...startedJob,
        progress: 0,
        result: null,
        savedReviewReport: null,
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
      <header className="page-header no-print">
        <h1>Analysis result</h1>
        <p>확인 필요 항목과 계약서에서 발견된 근거 문장을 함께 보여줍니다.</p>
      </header>

      <section className="panel stack no-print">
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

      <section className="panel stack no-print">
        <div className="section-title">
          <h2>Risk summary</h2>
          <RiskBadge level={analysis.overallRiskLevel} />
        </div>
        <p>{analysis.summary}</p>
      </section>

      <section className="stack no-print">
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

      <section className="panel stack multi-agent-panel">
        <div className="section-title no-print">
          <div>
            <h2>Hybrid Multi-Agent Report</h2>
            <p className="muted">저장된 최신 리포트를 우선 표시하고, 새 리포트 생성이 완료되면 최신 결과로 갱신합니다.</p>
          </div>
          <button
            className="primary-button"
            type="button"
            onClick={handleStartReviewJob}
            disabled={isReviewRunning}
          >
            <FileText size={18} />
            {isReviewRunning ? '새 리포트 생성 중' : reviewResult ? '다시 생성' : 'AI 종합 검토 리포트 생성'}
          </button>
        </div>

        {isReviewRunning && (
          <div className="review-progress no-print">
            <div className="section-title">
              <strong>{getProgressLabel(progress, reviewJob?.status)}</strong>
              <span className="muted">{reviewJob?.status || 'RUNNING'}</span>
            </div>
            <div className="progress-bar" aria-label="Review progress">
              <span style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
            </div>
            <p className="muted">새 리포트를 생성하는 동안 기존 저장 리포트는 유지됩니다. {progress}%</p>
          </div>
        )}

        {loadingSavedReport && <p className="muted no-print">저장된 리포트를 불러오는 중입니다...</p>}
        {reviewError && <p className="error-text no-print">{reviewError}</p>}

        {!loadingSavedReport && !reviewResult && (
          <p className="muted no-print">아직 생성된 종합 리포트가 없습니다.</p>
        )}

        {reviewResult && (
          <>
            <ReportDownloadPanel contract={contract} result={reviewResult} />
            <article className="review-report printable-report stack">
              <div className="section-title">
                <div>
                  <h3>종합 리포트 결과</h3>
                  <p className="muted">계약서 파일명: {contract.originalFileName}</p>
                  {reviewResult.updatedAt && (
                    <p className="muted">마지막 생성일: {new Date(reviewResult.updatedAt).toLocaleString('ko-KR')}</p>
                  )}
                </div>
                <RiskBadge level={reviewResult.overallRiskLevel} />
              </div>
              <p>{reviewResult.summary}</p>
              <details className="report-body-collapsible">
                <summary>리포트 본문 보기</summary>
                <MarkdownReport markdown={reviewResult.reportMarkdown} />
              </details>
              <AgentTrace result={reviewResult} />
              {(reviewResult.sources || []).length > 0 && (
                <details className="sources sources-collapsible no-print">
                  <summary>근거 sources 보기</summary>
                  <div className="sources-list">
                    {(reviewResult.sources || []).slice(0, 6).map((source, index) => (
                      <SourcePreview source={source} key={`${source.sourceTitle}-${index}`} />
                    ))}
                  </div>
                </details>
              )}
            </article>
          </>
        )}
      </section>

      <div className="action-row no-print">
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
