import { Send } from 'lucide-react';

export default function ChatPage() {
  return (
    <section className="page chat-page">
      <header className="page-header">
        <h1>계약서 Q&A</h1>
        <p>계약서 근거와 법령/체크리스트 근거를 구분해 표시할 예정입니다.</p>
      </header>
      <div className="chat-window">
        <div className="assistant-message">
          계약서에서 궁금한 조항을 질문해 주세요. 제공된 문서만으로 확인 가능한 범위에서 답변합니다.
        </div>
      </div>
      <form className="chat-form">
        <input placeholder="예: 보증금 반환 조건이 위험한지 봐줘" />
        <button className="icon-button" type="submit" aria-label="메시지 보내기">
          <Send size={18} />
        </button>
      </form>
    </section>
  );
}
