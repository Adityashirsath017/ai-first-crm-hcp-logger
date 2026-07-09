import React from 'react';
import LogInteractionForm from './components/LogInteractionForm';
import AIAssistantChat from './components/AIAssistantChat';

function App() {
  return (
    <div className="app-container">
      <header className="header" style={{ paddingLeft: '0.25rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: '700', color: '#0f172a' }}>
          Log HCP Interaction
        </h1>
      </header>
      
      <main className="main-content">
        <LogInteractionForm />
        <AIAssistantChat />
      </main>
    </div>
  );
}

export default App;
