import { useState } from 'react';

import AnalysisPage from './pages/AnalysisPage.jsx';
import ChatPage from './pages/ChatPage.jsx';
import ContractUploadPage from './pages/ContractUploadPage.jsx';
import HomePage from './pages/HomePage.jsx';

export default function App() {
  const [page, setPage] = useState('home');
  const [contractResult, setContractResult] = useState(null);
  const [chatSession, setChatSession] = useState(null);

  const navigate = (nextPage) => setPage(nextPage);

  return (
    <main className="app-shell">
      {page === 'home' && <HomePage navigate={navigate} />}
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
        />
      )}
      {page === 'chat' && (
        <ChatPage
          navigate={navigate}
          contractResult={contractResult}
          chatSession={chatSession}
          setChatSession={setChatSession}
        />
      )}
    </main>
  );
}
