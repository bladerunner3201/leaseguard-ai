import { useState } from 'react';

import AnalysisPage from './pages/AnalysisPage.jsx';
import ChatPage from './pages/ChatPage.jsx';
import ContractUploadPage from './pages/ContractUploadPage.jsx';
import HomePage from './pages/HomePage.jsx';

const pages = {
  home: HomePage,
  upload: ContractUploadPage,
  analysis: AnalysisPage,
  chat: ChatPage,
};

export default function App() {
  const [page, setPage] = useState('home');
  const Page = pages[page];

  return (
    <main className="app-shell">
      <Page navigate={setPage} />
    </main>
  );
}
