import { Upload } from 'lucide-react';

import { useAnonymousSession } from '../hooks/useAnonymousSession.js';

export default function ContractUploadPage({ navigate }) {
  const { anonymousSessionId, loading } = useAnonymousSession();

  return (
    <section className="page">
      <header className="page-header">
        <h1>계약서 업로드</h1>
        <p>초기 MVP는 TXT 계약서부터 연결하고, 이후 PDF 추출을 확장합니다.</p>
      </header>
      <div className="panel">
        <label className="upload-box">
          <Upload size={28} />
          <span>PDF 또는 TXT 파일 선택</span>
          <input type="file" accept=".pdf,.txt" disabled={loading} />
        </label>
        <p className="muted">세션: {anonymousSessionId || '생성 중'}</p>
        <button className="secondary-button" type="button" onClick={() => navigate('analysis')}>
          분석 결과 예시 보기
        </button>
      </div>
    </section>
  );
}
