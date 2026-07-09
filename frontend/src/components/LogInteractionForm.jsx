import React, { useState, useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { 
  updateField, 
  addAttendee, 
  removeAttendee, 
  addMaterial, 
  removeMaterial, 
  addSample, 
  removeSample,
  clearForm,
  setFormState
} from '../store/formSlice';
import { 
  submitLogInteraction, 
  editInteractionAPI, 
  fetchHCPs, 
  fetchCatalog, 
  fetchInteractions 
} from '../store/crmSlice';
import { 
  Search, 
  Plus, 
  Mic, 
  MicOff, 
  X, 
  Calendar, 
  Clock, 
  Sparkles, 
  CheckSquare, 
  Undo,
  Edit2
} from 'lucide-react';

export default function LogInteractionForm() {
  const dispatch = useDispatch();
  
  // Selectors
  const form = useSelector((state) => state.interactionForm);
  const { hcps, catalog, interactions, submitting } = useSelector((state) => state.crm);
  const chatSuggestions = useSelector((state) => state.chat.suggestions);

  // Local state
  const [hcpSearch, setHcpSearch] = useState('');
  const [showHcpDropdown, setShowHcpDropdown] = useState(false);
  const [attendeeInput, setAttendeeInput] = useState('');
  
  const [materialSearch, setMaterialSearch] = useState('');
  const [showMaterialDropdown, setShowMaterialDropdown] = useState(false);
  
  const [sampleSearch, setSampleSearch] = useState('');
  const [showSampleDropdown, setShowSampleDropdown] = useState(false);
  
  const [isRecording, setIsRecording] = useState(false);
  const [editingId, setEditingId] = useState(null); // Track if we are editing
  
  // Speech Recognition Ref
  const recognitionRef = useRef(null);

  // Sync hcpSearch with form state (e.g. if AI fills out the doctor's name)
  useEffect(() => {
    setHcpSearch(form.hcp_name || '');
  }, [form.hcp_name]);

  // Fetch initial database records on mount
  useEffect(() => {
    dispatch(fetchHCPs());
    dispatch(fetchCatalog());
    dispatch(fetchInteractions());
  }, [dispatch]);

  // Web Speech API initialization
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = 'en-US';

      rec.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
          const currentTopics = form.topics_discussed ? form.topics_discussed + ' ' : '';
          dispatch(updateField({ key: 'topics_discussed', value: currentTopics + finalTranscript }));
        }
      };

      rec.onerror = (e) => {
        console.error('Speech recognition error:', e);
        setIsRecording(false);
      };

      rec.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = rec;
    }
  }, [form.topics_discussed, dispatch]);

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. Please try Chrome, Edge or Safari.');
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      setIsRecording(true);
      recognitionRef.current.start();
    }
  };

  // Autocomplete filtering
  const filteredHCPs = hcps.filter(hcp => 
    hcp.name.toLowerCase().includes(hcpSearch.toLowerCase()) ||
    hcp.specialty.toLowerCase().includes(hcpSearch.toLowerCase())
  );

  const filteredMaterials = catalog.filter(item => 
    item.category === 'material' &&
    item.name.toLowerCase().includes(materialSearch.toLowerCase()) &&
    !form.materials_shared.includes(item.name)
  );

  const filteredSamples = catalog.filter(item => 
    item.category === 'sample' &&
    item.name.toLowerCase().includes(sampleSearch.toLowerCase()) &&
    !form.samples_distributed.includes(item.name)
  );

  // Handlers
  const handleHcpSelect = (hcp) => {
    dispatch(updateField({ key: 'hcp_id', value: hcp.id }));
    dispatch(updateField({ key: 'hcp_name', value: hcp.name }));
    dispatch(addAttendee(hcp.name));
    setHcpSearch(hcp.name);
    setShowHcpDropdown(false);
  };

  const handleAddAttendee = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (attendeeInput.trim()) {
        dispatch(addAttendee(attendeeInput));
        setAttendeeInput('');
      }
    }
  };

  const handleSuggestionClick = (suggestion) => {
    const currentText = form.follow_up_actions ? form.follow_up_actions + '\n' : '';
    dispatch(updateField({ key: 'follow_up_actions', value: currentText + `• ${suggestion}` }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.hcp_id) {
      alert('Please search and select an HCP from the dropdown.');
      return;
    }

    if (editingId) {
      dispatch(editInteractionAPI({ 
        interactionId: editingId, 
        updateData: form 
      })).then((res) => {
        if (!res.error) {
          setEditingId(null);
          dispatch(clearForm());
          setHcpSearch('');
          alert('Interaction updated successfully!');
        }
      });
    } else {
      dispatch(submitLogInteraction(form)).then((res) => {
        if (!res.error) {
          setHcpSearch('');
          alert('Interaction logged successfully!');
        }
      });
    }
  };

  const startEdit = (inter) => {
    setEditingId(inter.id);
    dispatch(setFormState({
      hcp_id: inter.hcp_id,
      hcp_name: inter.hcp_name,
      interaction_type: inter.interaction_type,
      date: inter.date,
      time: inter.time,
      attendees: inter.attendees,
      topics_discussed: inter.topics_discussed,
      materials_shared: inter.materials_shared,
      samples_distributed: inter.samples_distributed,
      sentiment: inter.sentiment,
      outcomes: inter.outcomes,
      follow_up_actions: inter.follow_up_actions,
    }));
    setHcpSearch(inter.hcp_name);
  };

  const cancelEdit = () => {
    setEditingId(null);
    dispatch(clearForm());
    setHcpSearch('');
  };

  return (
    <div className="glass-card">
      <h2 className="card-title">
        Interaction Details
      </h2>
      
      <form onSubmit={handleSubmit} className="form-scrollable">
        <div className="form-grid">
          
          {/* HCP Name */}
          <div className="form-group autocomplete-container">
            <label>HCP Name</label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                value={hcpSearch}
                onChange={(e) => {
                  setHcpSearch(e.target.value);
                  setShowHcpDropdown(true);
                  if (form.hcp_name && e.target.value !== form.hcp_name) {
                    dispatch(updateField({ key: 'hcp_id', value: '' }));
                    dispatch(updateField({ key: 'hcp_name', value: '' }));
                  }
                }}
                onFocus={() => setShowHcpDropdown(true)}
                placeholder="Search or select HCP..."
                style={{ width: '100%' }}
                required
              />
            </div>
            
            {showHcpDropdown && (
              <div className="autocomplete-dropdown">
                {filteredHCPs.length > 0 ? (
                  filteredHCPs.map(hcp => (
                    <div 
                      key={hcp.id} 
                      className="autocomplete-item" 
                      onClick={() => handleHcpSelect(hcp)}
                    >
                      <strong>{hcp.name}</strong> - {hcp.specialty} ({hcp.hospital})
                    </div>
                  ))
                ) : (
                  <div className="autocomplete-item" style={{ color: '#6b7280', cursor: 'default' }}>
                    No HCPs found
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Interaction Type */}
          <div className="form-group">
            <label>Interaction Type</label>
            <select
              value={form.interaction_type}
              onChange={(e) => dispatch(updateField({ key: 'interaction_type', value: e.target.value }))}
            >
              <option value="Meeting">Meeting</option>
              <option value="Call">Call</option>
              <option value="Email">Email</option>
              <option value="Seminar">Seminar</option>
              <option value="Advisory Board">Advisory Board</option>
            </select>
          </div>

          {/* Date */}
          <div className="form-group">
            <label>Date</label>
            <div style={{ position: 'relative' }}>
              <input
                type="date"
                value={form.date}
                onChange={(e) => dispatch(updateField({ key: 'date', value: e.target.value }))}
                style={{ width: '100%', paddingLeft: '2.2rem' }}
              />
              <Calendar size={15} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
            </div>
          </div>

          {/* Time */}
          <div className="form-group">
            <label>Time</label>
            <div style={{ position: 'relative' }}>
              <input
                type="time"
                value={form.time}
                onChange={(e) => dispatch(updateField({ key: 'time', value: e.target.value }))}
                style={{ width: '100%', paddingLeft: '2.2rem' }}
              />
              <Clock size={15} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
            </div>
          </div>

          {/* Attendees */}
          <div className="form-group full-width">
            <label>Attendees</label>
            <input
              type="text"
              value={attendeeInput}
              onChange={(e) => setAttendeeInput(e.target.value)}
              onKeyDown={handleAddAttendee}
              placeholder="Enter names or search..."
              style={{ width: '100%' }}
            />
            <div className="chips-container">
              {form.attendees.map(name => (
                <span key={name} className="chip">
                  {name}
                  <button type="button" className="chip-remove" onClick={() => dispatch(removeAttendee(name))}>
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Topics Discussed */}
          <div className="form-group full-width" style={{ position: 'relative' }}>
            <label>Topics Discussed</label>
            <div style={{ position: 'relative' }}>
              <textarea
                value={form.topics_discussed}
                onChange={(e) => dispatch(updateField({ key: 'topics_discussed', value: e.target.value }))}
                placeholder="Enter key discussion points..."
                style={{ width: '100%', paddingRight: '2.5rem', minHeight: '80px' }}
              />
              <button
                type="button"
                className={`chat-mic-btn ${isRecording ? 'recording' : ''}`}
                onClick={toggleRecording}
                style={{ position: 'absolute', right: '10px', bottom: '10px', top: 'auto', transform: 'none' }}
                title="Dictate voice note"
              >
                {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
              </button>
            </div>
            <div className="voice-button-container">
              <button
                type="button"
                className={`voice-btn ${isRecording ? 'recording' : ''}`}
                onClick={toggleRecording}
              >
                ✦ Summarize from Voice Note (Requires Consent)
              </button>
            </div>
          </div>

          {/* Materials Shared / Samples Distributed */}
          <div className="form-group full-width">
            <label>Materials Shared / Samples Distributed</label>
            
            {/* Materials Shared */}
            <div className="nested-box-panel">
              <div className="form-section-header">
                <span>Materials Shared</span>
                <button 
                  type="button" 
                  className="section-btn" 
                  onClick={() => setShowMaterialDropdown(!showMaterialDropdown)}
                >
                  <Search size={11} /> Search/Add
                </button>
              </div>

              {showMaterialDropdown && (
                <div style={{ position: 'relative', marginBottom: '0.5rem' }}>
                  <input
                    type="text"
                    value={materialSearch}
                    onChange={(e) => setMaterialSearch(e.target.value)}
                    placeholder="Search materials catalog..."
                    style={{ width: '100%' }}
                    autoFocus
                  />
                  <div className="autocomplete-dropdown">
                    {filteredMaterials.length > 0 ? (
                      filteredMaterials.map(mat => (
                        <div 
                          key={mat.id} 
                          className="autocomplete-item"
                          onClick={() => {
                            dispatch(addMaterial(mat.name));
                            setMaterialSearch('');
                            setShowMaterialDropdown(false);
                          }}
                        >
                          {mat.name}
                        </div>
                      ))
                    ) : (
                      <div className="autocomplete-item" style={{ color: '#6b7280', cursor: 'default' }}>
                        No matching materials found
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="chips-container">
                {form.materials_shared.length > 0 ? (
                  form.materials_shared.map(mat => (
                    <span key={mat} className="chip">
                      {mat}
                      <button type="button" className="chip-remove" onClick={() => dispatch(removeMaterial(mat))}>
                        <X size={10} />
                      </button>
                    </span>
                  ))
                ) : (
                  <span className="catalog-no-items">No materials added.</span>
                )}
              </div>
            </div>

            {/* Samples Distributed */}
            <div className="nested-box-panel" style={{ marginTop: '0.6rem' }}>
              <div className="form-section-header">
                <span>Samples Distributed</span>
                <button 
                  type="button" 
                  className="section-btn" 
                  onClick={() => setShowSampleDropdown(!showSampleDropdown)}
                >
                  <Plus size={11} /> Add Sample
                </button>
              </div>

              {showSampleDropdown && (
                <div style={{ position: 'relative', marginBottom: '0.5rem' }}>
                  <input
                    type="text"
                    value={sampleSearch}
                    onChange={(e) => setSampleSearch(e.target.value)}
                    placeholder="Search drug samples catalog..."
                    style={{ width: '100%' }}
                    autoFocus
                  />
                  <div className="autocomplete-dropdown">
                    {filteredSamples.length > 0 ? (
                      filteredSamples.map(sam => (
                        <div 
                          key={sam.id} 
                          className="autocomplete-item"
                          onClick={() => {
                            dispatch(addSample(sam.name));
                            setSampleSearch('');
                            setShowSampleDropdown(false);
                          }}
                        >
                          {sam.name}
                        </div>
                      ))
                    ) : (
                      <div className="autocomplete-item" style={{ color: '#6b7280', cursor: 'default' }}>
                        No matching drug samples found
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="chips-container">
                {form.samples_distributed.length > 0 ? (
                  form.samples_distributed.map(sam => (
                    <span key={sam} className="chip">
                      {sam}
                      <button type="button" className="chip-remove" onClick={() => dispatch(removeSample(sam))}>
                        <X size={10} />
                      </button>
                    </span>
                  ))
                ) : (
                  <span className="catalog-no-items">No samples added.</span>
                )}
              </div>
            </div>
          </div>

          {/* Sentiment Selection */}
          <div className="form-group full-width">
            <label>Observed/Inferred HCP Sentiment</label>
            <div className="sentiment-group">
              <label className="sentiment-option">
                <input
                  type="radio"
                  name="sentiment"
                  value="Positive"
                  checked={form.sentiment === 'Positive'}
                  onChange={(e) => dispatch(updateField({ key: 'sentiment', value: e.target.value }))}
                />
                <span className="sentiment-emoji-inline">😊</span> Positive
              </label>
              <label className="sentiment-option">
                <input
                  type="radio"
                  name="sentiment"
                  value="Neutral"
                  checked={form.sentiment === 'Neutral'}
                  onChange={(e) => dispatch(updateField({ key: 'sentiment', value: e.target.value }))}
                />
                <span className="sentiment-emoji-inline">😐</span> Neutral
              </label>
              <label className="sentiment-option">
                <input
                  type="radio"
                  name="sentiment"
                  value="Negative"
                  checked={form.sentiment === 'Negative'}
                  onChange={(e) => dispatch(updateField({ key: 'sentiment', value: e.target.value }))}
                />
                <span className="sentiment-emoji-inline">😞</span> Negative
              </label>
            </div>
          </div>

          {/* Outcomes */}
          <div className="form-group full-width">
            <label>Outcomes</label>
            <textarea
              value={form.outcomes}
              onChange={(e) => dispatch(updateField({ key: 'outcomes', value: e.target.value }))}
              placeholder="Key outcomes or agreements..."
            />
          </div>

          {/* Follow-up Actions */}
          <div className="form-group full-width">
            <label>Follow-up Actions</label>
            <textarea
              value={form.follow_up_actions}
              onChange={(e) => dispatch(updateField({ key: 'follow_up_actions', value: e.target.value }))}
              placeholder="Enter next steps or tasks..."
            />
          </div>

          {/* AI Suggested Followups */}
          {chatSuggestions.length > 0 && (
            <div className="form-group full-width suggested-followups">
              <span className="suggested-title">
                AI Suggested Follow-ups:
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', alignItems: 'flex-start' }}>
                {chatSuggestions.map((sug, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="suggestion-pill"
                    onClick={() => handleSuggestionClick(sug)}
                  >
                    + {sug}
                  </button>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* Submit Button */}
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1.25rem', marginBottom: '1.5rem' }}>
          <button 
            type="submit" 
            className="btn btn-primary" 
            style={{ flex: 1 }}
            disabled={submitting}
          >
            {submitting ? 'Saving...' : (editingId ? 'Save & Update Log' : 'Log HCP Interaction')}
          </button>
          {editingId && (
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={cancelEdit}
            >
              <Undo size={14} /> Cancel
            </button>
          )}
        </div>

        {/* Log History */}
        <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1.25rem' }}>
          <h3 className="card-title" style={{ fontSize: '0.95rem', marginBottom: '0.75rem' }}>
            Recent Logged Interactions ({interactions.length})
          </h3>
          <div className="history-sidebar" style={{ maxHeight: '180px' }}>
            {interactions.length > 0 ? (
              interactions.map(inter => (
                <div key={inter.id} className="history-item">
                  <div className="history-header">
                    <span>{inter.hcp_name}</span>
                    <span className="history-date">{inter.date} {inter.time}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.25rem' }}>
                    <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                      {inter.interaction_type} | Sentiment: <span className={`history-sentiment ${inter.sentiment.toLowerCase()}`}>{inter.sentiment}</span>
                    </span>
                    <button 
                      type="button" 
                      className="history-edit-btn" 
                      onClick={() => startEdit(inter)}
                    >
                      <Edit2 size={10} style={{ display: 'inline', marginRight: '2px' }} />
                      Edit Log
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <span className="catalog-no-items">No interactions logged yet.</span>
            )}
          </div>
        </div>

      </form>
    </div>
  );
}
