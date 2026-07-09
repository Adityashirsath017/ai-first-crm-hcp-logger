import React, { useState, useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendMessage, addMessage } from '../store/chatSlice';
import { submitLogInteraction } from '../store/crmSlice';
import { MessageSquare, AlertTriangle, Mic, MicOff } from 'lucide-react';

export default function AIAssistantChat() {
  const dispatch = useDispatch();
  
  // Selectors
  const { messages, loading } = useSelector((state) => state.chat);
  const currentFormState = useSelector((state) => state.interactionForm);
  const { submitting } = useSelector((state) => state.crm);
  
  // Local state
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  
  // References
  const chatEndRef = useRef(null);
  const recognitionRef = useRef(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Speech Recognition setup for chat bar
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = 'en-US';

      rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setInputText(prev => (prev ? prev + ' ' : '') + transcript);
        }
      };

      rec.onerror = (e) => {
        console.error('Speech recognition error in chat:', e);
        setIsRecording(false);
      };

      rec.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = rec;
    }
  }, []);

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. Please use Chrome, Edge or Safari.');
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      setIsRecording(true);
      recognitionRef.current.start();
    }
  };

  const handleSend = (e) => {
    e.preventDefault();
    if (!inputText.trim() || loading || submitting) return;

    const userMsg = inputText.trim();
    setInputText('');

    // 1. Add user message to UI
    dispatch(addMessage({ role: 'user', content: userMsg }));

    // 2. Dispatch to LangGraph Agent
    dispatch(sendMessage({ message: userMsg, currentFormState }));
  };

  const handleQuickLog = () => {
    if (!currentFormState.hcp_id) {
      alert("AI Assistant needs to identify the HCP before logging. Please mention the doctor's name first (e.g. 'Met Dr. Sharma today...').");
      return;
    }
    
    dispatch(submitLogInteraction(currentFormState)).then((res) => {
      if (!res.error) {
        alert('Interaction logged successfully!');
      }
    });
  };

  return (
    <div className="glass-card" style={{ height: '100%' }}>
      <h2 className="card-title" style={{ marginBottom: '2px' }}>
        <MessageSquare size={18} style={{ color: '#2563eb' }} />
        AI Assistant
      </h2>
      <div style={{ fontSize: '0.78rem', color: '#64748b', marginBottom: '1.25rem', display: 'flex', alignItems: 'center' }}>
        Log interaction via chat
      </div>
      
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        
        {/* Chat Feed */}
        <div className="chat-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-bubble ${msg.role}`}>
              {msg.content}
            </div>
          ))}
          {loading && (
            <div className="message-bubble assistant">
              <div className="typing-indicator">
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Controls */}
        <form onSubmit={handleSend} className="chat-input-container">
          <div className="chat-input-wrapper">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Describe interaction..."
              disabled={loading || submitting}
            />
            <button
              type="button"
              className={`chat-mic-btn ${isRecording ? 'recording' : ''}`}
              onClick={toggleRecording}
              title="Dictate message"
            >
              {isRecording ? <MicOff size={15} /> : <Mic size={15} />}
            </button>
          </div>
          
          <button 
            type="submit" 
            className="btn btn-log"
            disabled={!inputText.trim() || loading || submitting}
          >
            <AlertTriangle size={13} style={{ fill: '#ffffff', stroke: 'none' }} /> Log
          </button>
        </form>

      </div>
    </div>
  );
}
