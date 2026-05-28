import { useMemo, useState } from 'react';

import {
  createChatSession,
  getChatSessions,
  getContractAnalysis,
} from './api/client.js';
import AnalysisPage from './pages/AnalysisPage.jsx';
import ChatPage from './pages/ChatPage.jsx';
import ContractUploadPage from './pages/ContractUploadPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import HomePage from './pages/HomePage.jsx';

const CHAT_SESSION_STORAGE_KEY = 'leaseguardChatSessionsByContract';

function loadStoredChatSessions() {
  try {
    return JSON.parse(localStorage.getItem(CHAT_SESSION_STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function storeChatSession(contractId, chatSession) {
  if (!contractId || !chatSession) {
    return;
  }
  const stored = loadStoredChatSessions();
  stored[String(contractId)] = chatSession;
  localStorage.setItem(CHAT_SESSION_STORAGE_KEY, JSON.stringify(stored));
}

export default function App() {
  const [page, setPage] = useState('home');
  const [contractResult, setContractResult] = useState(null);
  const [chatSession, setChatSession] = useState(null);
  const [navigationError, setNavigationError] = useState('');

  const storedChatSessions = useMemo(loadStoredChatSessions, [chatSession]);

  const navigate = (nextPage) => {
    setNavigationError('');
    setPage(nextPage);
  };

  const openAnalysis = async (contract) => {
    setNavigationError('');
    try {
      const analysis = await getContractAnalysis(contract.contractId);
      setContractResult({ contract, analysis });
      setChatSession(storedChatSessions[String(contract.contractId)] || null);
      setPage('analysis');
    } catch (error) {
      setNavigationError(error.message);
    }
  };

  const ensureChatSessionForContract = async (contract) => {
    const contractId = contract?.contractId;
    if (!contractId) {
      return null;
    }

    const stored = loadStoredChatSessions()[String(contractId)];
    if (stored) {
      return stored;
    }

    const sessions = await getChatSessions();
    const existingSession = sessions.find((session) => session.contractId === contractId);
    if (existingSession) {
      storeChatSession(contractId, existingSession);
      return existingSession;
    }

    const createdSession = await createChatSession({
      contractId,
      title: `Contract ${contractId} chat`,
    });
    storeChatSession(contractId, createdSession);
    return createdSession;
  };

  const openChat = async (contract) => {
    setNavigationError('');
    try {
      let analysis = contractResult?.contract?.contractId === contract.contractId
        ? contractResult.analysis
        : null;
      if (!analysis) {
        analysis = await getContractAnalysis(contract.contractId);
      }
      const session = await ensureChatSessionForContract(contract);
      setContractResult({ contract, analysis });
      setChatSession(session);
      setPage('chat');
    } catch (error) {
      setNavigationError(error.message);
    }
  };

  const setAndStoreChatSession = (nextChatSession) => {
    setChatSession(nextChatSession);
    const contractId = contractResult?.contract?.contractId || nextChatSession?.contractId;
    storeChatSession(contractId, nextChatSession);
  };

  return (
    <main className="app-shell">
      {navigationError && <p className="global-error error-text">{navigationError}</p>}
      {page === 'home' && <HomePage navigate={navigate} />}
      {page === 'dashboard' && (
        <DashboardPage
          navigate={navigate}
          onOpenAnalysis={openAnalysis}
          onOpenChat={openChat}
        />
      )}
      {page === 'upload' && (
        <ContractUploadPage
          navigate={navigate}
          onUploadSuccess={(result) => {
            setContractResult(result);
            setChatSession(null);
            setPage('analysis');
          }}
        />
      )}
      {page === 'analysis' && (
        <AnalysisPage
          navigate={navigate}
          contractResult={contractResult}
          onOpenChat={() => openChat(contractResult.contract)}
        />
      )}
      {page === 'chat' && (
        <ChatPage
          navigate={navigate}
          contractResult={contractResult}
          chatSession={chatSession}
          setChatSession={setAndStoreChatSession}
        />
      )}
    </main>
  );
}
