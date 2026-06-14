import { ArrowLeft, FolderOpen, Send } from 'lucide-react';
import { useEffect, useState } from 'react';

import { createChatSession, getChatMessages, sendChatMessage } from '../api/client.js';

const SOURCE_PREVIEW_LENGTH = 300;

function ChatSources({ sources }) {
  if (!sources?.length) {
    return null;
  }

  return (
    <details className="chat-sources">
      <summary>Sources ({sources.length})</summary>
      <div className="chat-sources-list">
        {sources.map((source, sourceIndex) => (
          <ChatSourceItem source={source} sourceIndex={sourceIndex} key={`${source.sourceTitle}-${sourceIndex}`} />
        ))}
      </div>
    </details>
  );
}

function ChatSourceItem({ source, sourceIndex }) {
  const [expanded, setExpanded] = useState(false);
  const chunkText = source.chunkText || '';
  const shouldTruncate = chunkText.length > SOURCE_PREVIEW_LENGTH;
  const visibleText = expanded || !shouldTruncate ? chunkText : `${chunkText.slice(0, SOURCE_PREVIEW_LENGTH)}...`;

  return (
    <details className="chat-source-item">
      <summary>
        <span>{source.sourceTitle || `Source ${sourceIndex + 1}`}</span>
        <small>{source.sourceType}</small>
      </summary>
      <div className="chat-source-detail">
        <div className="section-title">
          <span>{source.sourceType}</span>
          <span>{source.similarityScore}</span>
        </div>
        <p>{visibleText}</p>
        {shouldTruncate && (
          <button className="text-button compact" type="button" onClick={() => setExpanded((current) => !current)}>
            {expanded ? '접기' : '더보기'}
          </button>
        )}
      </div>
    </details>
  );
}

export default function ChatPage({ navigate, contractResult, chatSession, setChatSession }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState('');

  const contractId = contractResult?.contract?.contractId;
  const chatSessionId = chatSession?.chatSessionId;

  useEffect(() => {
    let ignore = false;

    async function loadMessages() {
      if (!chatSessionId) {
        setMessages([]);
        return;
      }

      setLoadingMessages(true);
      setError('');
      try {
        const savedMessages = await getChatMessages(chatSessionId);
        if (!ignore) {
          setMessages(savedMessages || []);
        }
      } catch (loadError) {
        if (!ignore) {
          setError(loadError.message);
        }
      } finally {
        if (!ignore) {
          setLoadingMessages(false);
        }
      }
    }

    loadMessages();
    return () => {
      ignore = true;
    };
  }, [chatSessionId]);

  const ensureChatSession = async () => {
    if (chatSession) {
      return chatSession;
    }
    const createdSession = await createChatSession({
      contractId,
      title: `Contract ${contractId || ''} chat`.trim(),
    });
    setChatSession(createdSession);
    return createdSession;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (sending) {
      return;
    }

    const message = input.trim();
    if (!message) {
      return;
    }

    setSending(true);
    setError('');
    setInput('');
    setMessages((current) => [...current, { role: 'user', content: message, sources: [] }]);

    try {
      const session = await ensureChatSession();
      const answer = await sendChatMessage({
        chatSessionId: session.chatSessionId,
        contractId,
        message,
      });
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: answer.answer,
          sources: answer.sources || [],
        },
      ]);
    } catch (sendError) {
      setError(sendError.message);
    } finally {
      setSending(false);
    }
  };

  if (!contractResult) {
    return (
      <section className="page">
        <header className="page-header">
          <h1>No contract selected</h1>
          <p>Upload a contract or choose one from your saved contract list before opening chat.</p>
        </header>
        <div className="action-row left">
          <button className="primary-button" type="button" onClick={() => navigate('upload')}>
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

  return (
    <section className="page chat-page">
      <header className="page-header">
        <button className="text-button" type="button" onClick={() => navigate('analysis')}>
          <ArrowLeft size={16} />
          Back to analysis
        </button>
        <h1>Contract Q&A</h1>
        <p>업로드한 계약서와 임대차 reference 문서를 바탕으로 답변합니다.</p>
      </header>

      <div className="chat-window">
        {loadingMessages && <div className="assistant-message">Loading saved messages...</div>}
        {!loadingMessages && messages.length === 0 && (
          <div className="assistant-message">
            업로드한 계약서에 대해 궁금한 점을 질문하세요. 답변에는 계약서와 reference source가 함께 표시됩니다.
          </div>
        )}

        {messages.map((message, index) => (
          <article className={`${message.role}-message`} key={message.messageId || `${message.role}-${index}`}>
            <strong>{message.role}</strong>
            <p className="message-content">{message.content}</p>
            <ChatSources sources={message.sources} />
          </article>
        ))}

        {sending && (
          <div className="chat-loading-message" aria-label="답변 생성 중">
            <div className="chat-spinner" />
          </div>
        )}
      </div>

      {error && <p className="error-text">{error}</p>}
      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          value={input}
          placeholder="보증금 반환 조건이 위험한지 질문해 보세요"
          disabled={sending}
          onChange={(event) => setInput(event.target.value)}
        />
        <button className="icon-button" type="submit" aria-label="Send message" disabled={sending || !input.trim()}>
          <Send size={18} />
        </button>
      </form>
    </section>
  );
}
