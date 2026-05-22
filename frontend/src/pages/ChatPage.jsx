import { ArrowLeft, Send } from 'lucide-react';
import { useState } from 'react';

import { createChatSession, sendChatMessage } from '../api/client.js';

export default function ChatPage({ navigate, contractResult, chatSession, setChatSession }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const contractId = contractResult?.contract?.contractId;

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
          <p>Upload a contract before opening chat.</p>
        </header>
        <button className="primary-button" type="button" onClick={() => navigate('upload')}>
          Go to upload
        </button>
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
        <p>Messages are sent through Spring Boot to the FastAPI stub server.</p>
      </header>

      <div className="chat-window">
        {messages.length === 0 && (
          <div className="assistant-message">
            Ask a question about the uploaded contract. The current answer is a fixed FastAPI stub response.
          </div>
        )}

        {messages.map((message, index) => (
          <article className={`${message.role}-message`} key={`${message.role}-${index}`}>
            <strong>{message.role}</strong>
            <p>{message.content}</p>
            {message.sources?.length > 0 && (
              <div className="sources">
                <h3>Sources</h3>
                {message.sources.map((source, sourceIndex) => (
                  <div className="source-item" key={`${source.sourceTitle}-${sourceIndex}`}>
                    <div className="section-title">
                      <span>{source.sourceType}</span>
                      <span>{source.similarityScore}</span>
                    </div>
                    <strong>{source.sourceTitle}</strong>
                    <p>{source.chunkText}</p>
                  </div>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>

      {error && <p className="error-text">{error}</p>}
      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          value={input}
          placeholder="Ask about deposit return terms"
          disabled={sending}
          onChange={(event) => setInput(event.target.value)}
        />
        <button className="icon-button" type="submit" aria-label="Send message" disabled={sending}>
          <Send size={18} />
        </button>
      </form>
    </section>
  );
}
