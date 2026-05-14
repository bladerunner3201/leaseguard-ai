import { MessageCircle } from 'lucide-react';

export default function AnalysisPage({ navigate }) {
  return (
    <section className="page">
      <header className="page-header">
        <h1>분석 결과</h1>
        <p>위험도와 확인 필요 항목이 이 화면에 표시됩니다.</p>
      </header>
      <div className="risk-summary">
        <span className="risk-badge caution">CAUTION</span>
        <p>보증금 반환 조건과 특약 조항을 추가 확인하는 흐름으로 구현 예정입니다.</p>
      </div>
      <button className="primary-button" type="button" onClick={() => navigate('chat')}>
        <MessageCircle size={18} />
        계약서에 대해 질문하기
      </button>
    </section>
  );
}
