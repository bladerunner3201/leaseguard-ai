import { ArrowLeft, FolderOpen, Send } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { createChatSession, getChatMessages, sendChatMessage } from '../api/client.js';

const SOURCE_PREVIEW_LENGTH = 300;
const SOURCE_REF_PATTERN = /\[Source\s+(\d+)\]/g;

function ChatMessage({ message, messageIndex }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [openSourceNumbers, setOpenSourceNumbers] = useState(() => new Set());
  const [highlightedSource, setHighlightedSource] = useState(null);
  const citedSourceNumbers = useMemo(() => extractCitedSourceNumbers(message.content), [message.content]);

  const handleCitationClick = (sourceNumber) => {
    setSourcesOpen(true);
    setOpenSourceNumbers((current) => new Set([...current, sourceNumber]));
    setHighlightedSource(sourceNumber);

    window.setTimeout(() => {
      document
        .getElementById(getSourceElementId(messageIndex, sourceNumber))
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 80);
  };

  const handleSourceToggle = (sourceNumber, isOpen) => {
    setOpenSourceNumbers((current) => {
      const next = new Set(current);
      if (isOpen) {
        next.add(sourceNumber);
      } else {
        next.delete(sourceNumber);
      }
      return next;
    });
  };

  return (
    <article className={`${message.role}-message`}>
      <strong>{message.role}</strong>
      <MessageContent content={message.content} onCitationClick={handleCitationClick} />
      <ChatSources
        sources={message.sources}
        citedSourceNumbers={citedSourceNumbers}
        messageIndex={messageIndex}
        isOpen={sourcesOpen}
        onOpenChange={setSourcesOpen}
        openSourceNumbers={openSourceNumbers}
        highlightedSource={highlightedSource}
        onSourceToggle={handleSourceToggle}
      />
    </article>
  );
}

function MessageContent({ content, onCitationClick }) {
  const parts = [];
  const text = content || '';
  let lastIndex = 0;

  for (const match of text.matchAll(SOURCE_REF_PATTERN)) {
    const [label, numberText] = match;
    const sourceNumber = Number(numberText);
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <button
        className="source-citation-button"
        type="button"
        onClick={() => onCitationClick(sourceNumber)}
        key={`${match.index}-${label}`}
      >
        {label}
      </button>,
    );
    lastIndex = match.index + label.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <p className="message-content">{parts}</p>;
}

function ChatSources({
  sources,
  citedSourceNumbers,
  messageIndex,
  isOpen,
  onOpenChange,
  openSourceNumbers,
  highlightedSource,
  onSourceToggle,
}) {
  const groupedSources = useMemo(
    () => groupSources(sources || [], citedSourceNumbers),
    [sources, citedSourceNumbers],
  );
  const visibleSourceCount = groupedSources.reduce((count, group) => count + group.items.length, 0);

  if (!sources?.length || citedSourceNumbers.size === 0 || visibleSourceCount === 0) {
    return null;
  }

  return (
    <details className="chat-sources" open={isOpen} onToggle={(event) => onOpenChange(event.currentTarget.open)}>
      <summary>Sources ({visibleSourceCount})</summary>
      <div className="chat-source-groups">
        {groupedSources.map((group) => (
          <section className="chat-source-group" key={group.key}>
            <h4>{group.label}</h4>
            <div className="chat-sources-list">
              {group.items.map(({ source, sourceIndex }) => {
                const sourceNumber = sourceIndex + 1;
                return (
                  <ChatSourceItem
                    source={source}
                    sourceNumber={sourceNumber}
                    messageIndex={messageIndex}
                    isOpen={openSourceNumbers.has(sourceNumber)}
                    highlighted={highlightedSource === sourceNumber}
                    onToggle={onSourceToggle}
                    key={`${source.sourceTitle}-${sourceIndex}`}
                  />
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </details>
  );
}

function ChatSourceItem({ source, sourceNumber, messageIndex, isOpen, highlighted, onToggle }) {
  const [expanded, setExpanded] = useState(false);
  const chunkText = source.chunkText || '';
  const shouldTruncate = chunkText.length > SOURCE_PREVIEW_LENGTH;
  const visibleText = expanded || !shouldTruncate ? chunkText : `${chunkText.slice(0, SOURCE_PREVIEW_LENGTH)}...`;

  return (
    <details
      className={`chat-source-item${highlighted ? ' highlighted' : ''}`}
      id={getSourceElementId(messageIndex, sourceNumber)}
      open={isOpen}
      onToggle={(event) => onToggle(sourceNumber, event.currentTarget.open)}
    >
      <summary>
        <span>{`Source ${sourceNumber}: ${source.sourceTitle || `Source ${sourceNumber}`}`}</span>
        <small>{source.sourceType}</small>
      </summary>
      <div className="chat-source-detail">
        <div className="section-title">
          <span>{`[Source ${sourceNumber}] ${source.sourceType}`}</span>
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

function groupSources(sources, citedSourceNumbers) {
  const contractItems = [];
  const referenceItems = [];

  sources.forEach((source, sourceIndex) => {
    const sourceNumber = sourceIndex + 1;
    if (!citedSourceNumbers.has(sourceNumber)) {
      return;
    }

    const item = { source, sourceIndex };
    if (source.sourceType === 'contract') {
      contractItems.push(item);
    } else {
      referenceItems.push(item);
    }
  });

  return [
    { key: 'contract', label: '계약서 근거', items: contractItems },
    { key: 'reference', label: '법령/체크리스트 근거', items: referenceItems },
  ].filter((group) => group.items.length > 0);
}

function extractCitedSourceNumbers(content) {
  const citedNumbers = new Set();
  const text = content || '';

  for (const match of text.matchAll(SOURCE_REF_PATTERN)) {
    citedNumbers.add(Number(match[1]));
  }

  return citedNumbers;
}

function getSourceElementId(messageIndex, sourceNumber) {
  return `chat-message-${messageIndex}-source-${sourceNumber}`;
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
            업로드한 계약서에 대해 궁금한 점을 질문하세요. 답변에는 필요한 경우 계약서와 reference source가 함께 표시됩니다.
          </div>
        )}

        {messages.map((message, index) => (
          <ChatMessage message={message} messageIndex={index} key={message.messageId || `${message.role}-${index}`} />
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
          placeholder="보증금 반환 조건이나 특약 위험을 질문해 보세요."
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
