import { FileCheck } from 'lucide-react';

export default function HomePage({ navigate }) {
  return (
    <section className="page intro-page">
      <div>
        <p className="eyebrow">RAG 기반 임대차계약서 위험요소 점검</p>
        <h1>LeaseGuard AI</h1>
        <p className="lead">
          계약서 내용을 법령 및 공공 체크리스트와 비교해 확인이 필요한 항목을 정리합니다.
          법률 자문이 아닌 참고용 점검 도구입니다.
        </p>
        <button className="primary-button" type="button" onClick={() => navigate('upload')}>
          <FileCheck size={18} />
          계약서 업로드 시작
        </button>
      </div>
    </section>
  );
}
