import React, { useEffect, useState, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { 
  Plus, 
  MessageSquare, 
  Sparkles, 
  Mic, 
  Smile, 
  Meh, 
  Frown, 
  Send, 
  RotateCcw, 
  Save, 
  Search, 
  Calendar, 
  Clock, 
  Users, 
  FileText, 
  Award,
  Layers,
  X,
  Trash2
} from 'lucide-react';
import { 
  fetchHcps, 
  fetchMaterials, 
  fetchSamples, 
  fetchInteractions, 
  updateFormState, 
  clearFormState, 
  submitInteraction, 
  sendChatMessage,
  summarizeVoiceNote,
  deleteInteraction
} from './store/crmSlice';

export default function App() {
  const dispatch = useDispatch();
  
  // Redux Selectors
  const { 
    hcps, 
    materials, 
    samples, 
    interactions, 
    currentFormState, 
    chatHistory, 
    agentLogs,
    loading, 
    chatLoading, 
    voiceLoading, 
    error 
  } = useSelector((state) => state.crm);

  // Local Component States
  const [chatInput, setChatInput] = useState('');
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [voiceTextPreset, setVoiceTextPreset] = useState('');
  const [voiceTimer, setVoiceTimer] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const recordingInterval = useRef(null);
  const chatEndRef = useRef(null);

  // Load Initial Data
  useEffect(() => {
    dispatch(fetchHcps());
    dispatch(fetchMaterials());
    dispatch(fetchSamples());
    dispatch(fetchInteractions());
  }, [dispatch]);

  // Scroll Chat to Bottom on New Message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, chatLoading]);

  // Form State Handlers
  const handleInputChange = (field, value) => {
    dispatch(updateFormState({ [field]: value }));
  };

  const handleHcpChange = (e) => {
    const selectedId = e.target.value;
    handleInputChange('hcp_id', selectedId);
    
    // Auto-update name field as well
    const hcp = hcps.find(h => h.id.toString() === selectedId.toString());
    if (hcp) {
      handleInputChange('hcp_name', hcp.name);
    } else {
      handleInputChange('hcp_name', '');
    }
  };

  const toggleMaterial = (id) => {
    const current = currentFormState.materials_shared || [];
    const updated = current.includes(id) 
      ? current.filter(mId => mId !== id)
      : [...current, id];
    handleInputChange('materials_shared', updated);
  };

  const toggleSample = (id) => {
    const current = currentFormState.samples_distributed || [];
    const updated = current.includes(id)
      ? current.filter(sId => sId !== id)
      : [...current, id];
    handleInputChange('samples_distributed', updated);
  };

  // Form Submission Handler
  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!currentFormState.hcp_id) {
      alert("Please select a Healthcare Professional.");
      return;
    }
    dispatch(submitInteraction(currentFormState));
  };

  // Form Reset
  const handleFormReset = () => {
    dispatch(clearFormState());
  };

  // Chat Send Message
  const handleChatSubmit = (e) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;
    
    const userMsg = chatInput.trim();
    setChatInput('');
    
    // Add User Message to local chat
    dispatch({
      type: 'crm/addChatMessage',
      payload: {
        sender: 'user',
        text: userMsg,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    });

    // Call Agent
    dispatch(sendChatMessage({ 
      message: userMsg, 
      currentFormState 
    }));
  };

  // Voice Simulation Handlers
  const startRecording = () => {
    setIsRecording(true);
    setVoiceTimer(0);
    recordingInterval.current = setInterval(() => {
      setVoiceTimer(prev => prev + 1);
    }, 1000);
  };

  const stopRecording = () => {
    setIsRecording(false);
    clearInterval(recordingInterval.current);
  };

  const openVoiceSimulator = () => {
    setShowVoiceModal(true);
    setVoiceTextPreset('');
    stopRecording();
  };

  const closeVoiceSimulator = () => {
    setShowVoiceModal(false);
    stopRecording();
  };

  const handleVoicePresetSelect = (presetText) => {
    setVoiceTextPreset(presetText);
    startRecording();
    // Simulate recording for 2 seconds then stop automatically
    setTimeout(() => {
      stopRecording();
    }, 2500);
  };

  const submitVoiceDictation = () => {
    if (!voiceTextPreset.trim()) return;
    dispatch(summarizeVoiceNote(voiceTextPreset));
    setShowVoiceModal(false);
  };

  // Pre-set Dictations representing typical field notes
  const voicePresets = [
    {
      title: "Dr. Patel - OncoBoost Efficacy Discussion",
      text: "Met Dr. Sarah Patel today at her clinic. We discussed the OncoBoost Phase III clinical results. She had a positive sentiment about the lung cancer efficacy data and requested 2 starter samples. I told her I will send the trials PDF as a follow-up."
    },
    {
      title: "Dr. Chen - CardioShield Call",
      text: "Had a call with Dr. Robert Chen. Discussed CardioShield safety profile and potential medication interactions. He had a neutral sentiment and requested we follow up in two weeks with the reports."
    },
    {
      title: "Dr. Ross - NeuroMax Email",
      text: "Emailed Dr. Amanda Ross with the NeuroMax efficacy study file. She replied with positive feedback and scheduled a follow up by next Monday."
    }
  ];

  // Helper formatting for voice timer
  const formatTime = (secs) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // Suggestion Handler
  const applySuggestedFollowup = (text, relatedMaterialId = null) => {
    handleInputChange('follow_up_actions', text);
    if (relatedMaterialId) {
      const current = currentFormState.materials_shared || [];
      if (!current.includes(relatedMaterialId)) {
        handleInputChange('materials_shared', [...current, relatedMaterialId]);
      }
    }
  };

  return (
    <>
      <header className="app-header">
        <div className="logo-container">
          <Sparkles className="logo-icon" />
          <span className="logo-text">PulseCRM AI</span>
        </div>
        <div className="agent-status">
          <div className="status-dot"></div>
          <span>AI Assistant: Online</span>
        </div>
      </header>

      <main className="main-dashboard">
        
        {/* Left Side: Structured Form Panel */}
        <section className="glass-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <FileText size={18} className="text-primary" />
              Log HCP Interaction Details
            </h2>
            <button className="btn btn-secondary" onClick={handleFormReset} style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>
              <RotateCcw size={14} /> Reset
            </button>
          </div>

          <div className="panel-content">
            <form onSubmit={handleFormSubmit}>
              <div className="form-grid">
                
                {/* HCP Selection */}
                <div className="form-group">
                  <label htmlFor="hcp-select">HCP Name</label>
                  <select 
                    id="hcp-select"
                    value={currentFormState.hcp_id || ''}
                    onChange={handleHcpChange}
                    required
                  >
                    <option value="">Select or search HCP...</option>
                    {hcps.map(hcp => (
                      <option key={hcp.id} value={hcp.id}>
                        {hcp.name} ({hcp.specialty})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Interaction Type */}
                <div className="form-group">
                  <label htmlFor="interaction-type">Interaction Type</label>
                  <select 
                    id="interaction-type"
                    value={currentFormState.type || 'Meeting'}
                    onChange={(e) => handleInputChange('type', e.target.value)}
                  >
                    <option value="Meeting">Meeting (In-Person)</option>
                    <option value="Call">Call</option>
                    <option value="Email">Email</option>
                    <option value="Video Conference">Video Conference</option>
                  </select>
                </div>

                {/* Date */}
                <div className="form-group">
                  <label htmlFor="interaction-date">Date</label>
                  <div style={{ position: 'relative' }}>
                    <input 
                      type="date" 
                      id="interaction-date"
                      value={currentFormState.date || ''}
                      onChange={(e) => handleInputChange('date', e.target.value)}
                      required
                      style={{ width: '100%', boxSizing: 'border-box' }}
                    />
                  </div>
                </div>

                {/* Time */}
                <div className="form-group">
                  <label htmlFor="interaction-time">Time</label>
                  <input 
                    type="time" 
                    id="interaction-time"
                    value={currentFormState.time || ''}
                    onChange={(e) => handleInputChange('time', e.target.value)}
                    required
                  />
                </div>

                {/* Attendees */}
                <div className="form-group full-width">
                  <label htmlFor="attendees">Attendees</label>
                  <input 
                    type="text" 
                    id="attendees"
                    placeholder="Enter attendee names, separated by commas (e.g. Dr. Patel, Rep Alex)"
                    value={currentFormState.attendees || ''}
                    onChange={(e) => handleInputChange('attendees', e.target.value)}
                  />
                </div>

                {/* Topics Discussed */}
                <div className="form-group full-width">
                  <label htmlFor="topics">Topics Discussed</label>
                  <textarea 
                    id="topics"
                    placeholder="Enter clinical topics or details discussed..."
                    value={currentFormState.topics_discussed || ''}
                    onChange={(e) => handleInputChange('topics_discussed', e.target.value)}
                  />
                  
                  {/* Voice Note Simulation Button */}
                  <button 
                    type="button" 
                    className={`voice-simulate-btn ${voiceLoading ? 'recording' : ''}`}
                    onClick={openVoiceSimulator}
                  >
                    <Mic size={16} />
                    {voiceLoading ? 'AI Summarizing Voice Note...' : 'Summarize from Voice Note (Requires Consent)'}
                  </button>
                </div>

                {/* Materials Shared */}
                <div className="form-group full-width multi-select-container">
                  <label>Materials Shared / Distributed</label>
                  <div className="chips-grid">
                    {materials.map(m => {
                      const isActive = (currentFormState.materials_shared || []).includes(m.id);
                      return (
                        <div 
                          key={m.id} 
                          className={`chip-item ${isActive ? 'active' : ''}`}
                          onClick={() => toggleMaterial(m.id)}
                        >
                          <FileText size={12} />
                          <span>{m.name}</span>
                          <span style={{ fontSize: '0.65rem', opacity: 0.6 }}>({m.type})</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Samples Distributed */}
                <div className="form-group full-width multi-select-container">
                  <label>Samples Distributed</label>
                  <div className="chips-grid">
                    {samples.map(s => {
                      const isActive = (currentFormState.samples_distributed || []).includes(s.id);
                      const isLow = s.stock_quantity <= 15;
                      return (
                        <div 
                          key={s.id} 
                          className={`chip-item ${isActive ? 'active' : ''}`}
                          onClick={() => toggleSample(s.id)}
                        >
                          <Layers size={12} />
                          <span>{s.name}</span>
                          <span className={`stock-tag ${isLow ? 'low' : ''}`}>
                            {s.stock_quantity} left
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Inferred HCP Sentiment */}
                <div className="form-group full-width">
                  <label>Observed/Inferred HCP Sentiment</label>
                  <div className="sentiment-group">
                    {[
                      { value: 'Positive', label: 'Positive', icon: Smile, class: 'positive' },
                      { value: 'Neutral', label: 'Neutral', icon: Meh, class: 'neutral' },
                      { value: 'Negative', label: 'Negative', icon: Frown, class: 'negative' }
                    ].map(item => {
                      const IconComp = item.icon;
                      const isActive = currentFormState.sentiment === item.value;
                      return (
                        <div 
                          key={item.value}
                          className={`sentiment-label ${isActive ? `active ${item.class}` : ''}`}
                          onClick={() => handleInputChange('sentiment', item.value)}
                        >
                          <IconComp className="sentiment-icon" />
                          <span>{item.label}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Outcomes */}
                <div className="form-group full-width">
                  <label htmlFor="outcomes">Outcomes / Agreements</label>
                  <textarea 
                    id="outcomes"
                    placeholder="Key outcomes, agreements, or feedback received..."
                    value={currentFormState.outcomes || ''}
                    onChange={(e) => handleInputChange('outcomes', e.target.value)}
                  />
                </div>

                {/* Follow-up Actions */}
                <div className="form-group full-width">
                  <label htmlFor="followup">Follow-up Actions</label>
                  <textarea 
                    id="followup"
                    placeholder="Enter next steps, tasks, or follow-ups..."
                    value={currentFormState.follow_up_actions || ''}
                    onChange={(e) => handleInputChange('follow_up_actions', e.target.value)}
                  />
                </div>

              </div>

              {/* AI Suggested Follow-ups */}
              <div className="ai-suggestions-box">
                <div className="suggestions-title">
                  <Sparkles size={14} />
                  AI Suggested Follow-ups
                </div>
                <div className="suggestions-list">
                  <button 
                    type="button" 
                    className="suggestion-item-btn"
                    onClick={() => applySuggestedFollowup("Schedule follow-up meeting in 2 weeks to review lung cancer efficacy metrics.")}
                  >
                    <span>Schedule follow-up meeting in 2 weeks</span>
                    <span className="suggestion-plus">+ Add</span>
                  </button>
                  <button 
                    type="button" 
                    className="suggestion-item-btn"
                    onClick={() => {
                      // Find OncoBoost PDF ID
                      const p = materials.find(m => m.name.includes("OncoBoost"));
                      applySuggestedFollowup("Send OncoBoost Phase III clinical results PDF to doctor.", p ? p.id : null);
                    }}
                  >
                    <span>Send OncoBoost Phase III PDF</span>
                    <span className="suggestion-plus">+ Add</span>
                  </button>
                  <button 
                    type="button" 
                    className="suggestion-item-btn"
                    onClick={() => applySuggestedFollowup("Submit application to invite doctor to advisory board list.")}
                  >
                    <span>Add doctor to advisory board invitation list</span>
                    <span className="suggestion-plus">+ Add</span>
                  </button>
                </div>
              </div>

              {/* Form Submission */}
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  <Save size={16} />
                  {loading ? 'Saving...' : 'Log Interaction'}
                </button>
              </div>
            </form>
          </div>
        </section>

        {/* Right Side: AI Assistant Chat Panel */}
        <section className="glass-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <MessageSquare size={18} className="text-primary" />
              AI Assistant
            </h2>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Log via conversational chat
            </div>
          </div>

          <div className="panel-content chat-container">
            <div className="messages-scroller">
              {chatHistory.map((msg, idx) => (
                <div key={idx} className={`chat-message-row ${msg.sender}`}>
                  <div className="message-bubble">
                    {msg.text}
                    
                    {/* Render execution logs if the assistant ran any tools */}
                    {msg.logs && msg.logs.length > 0 && (
                      <div className="agent-execution-logs">
                        {msg.logs.map((logLine, lIdx) => (
                          <div key={lIdx} className="agent-log-line">
                            <div className="agent-log-indicator"></div>
                            <span>{logLine}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <span className="message-meta">{msg.timestamp}</span>
                </div>
              ))}
              
              {chatLoading && (
                <div className="chat-message-row assistant">
                  <div className="message-bubble">
                    <div className="typing-indicator">
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={chatEndRef} />
            </div>

            {/* Chat Send Input Box */}
            <form onSubmit={handleChatSubmit} className="chat-input-bar">
              <input 
                type="text" 
                className="chat-input-field"
                placeholder="Describe interaction (e.g. 'Met Dr. Sarah, sentiment positive...')"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                disabled={chatLoading}
              />
              <button type="submit" className="chat-send-btn" disabled={chatLoading || !chatInput.trim()}>
                <Send size={16} />
              </button>
            </form>
          </div>
        </section>

        {/* Bottom Panel: Logged Interactions History */}
        <section className="glass-panel history-section">
          <div className="panel-header">
            <h2 className="panel-title">
              <Award size={18} className="text-primary" />
              Recent Logged Interactions History
            </h2>
          </div>
          <div className="panel-content" style={{ padding: '0.75rem 1.5rem' }}>
            {interactions.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                No interactions logged yet. Log your first one using the form or chat!
              </div>
            ) : (
              <div className="interactions-table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>HCP</th>
                      <th>Type</th>
                      <th>Date / Time</th>
                      <th>Topics</th>
                      <th>Materials Shared</th>
                      <th>Samples</th>
                      <th>Sentiment</th>
                      <th>Tasks</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {interactions.map(item => {
                      // Fetch HCP name from list or use default
                      const hcpObj = hcps.find(h => h.id === item.hcp_id);
                      const hcpName = hcpObj ? hcpObj.name : `HCP (ID: ${item.hcp_id})`;
                      const hcpSpecialty = hcpObj ? hcpObj.specialty : '';
                      
                      return (
                        <tr key={item.id}>
                          <td>
                            <div style={{ fontWeight: 600 }}>{hcpName}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{hcpSpecialty}</div>
                          </td>
                          <td>
                            <span className="badge badge-type">{item.type}</span>
                          </td>
                          <td>
                            <div>{item.date}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.time}</div>
                          </td>
                          <td style={{ maxWidth: '240px' }}>
                            <div style={{ fontWeight: 500, fontSize: '0.825rem' }}>
                              {item.topics_discussed || 'N/A'}
                            </div>
                          </td>
                          <td>
                            {item.materials && item.materials.length > 0 ? (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                {item.materials.map(m => (
                                  <span key={m.id} style={{ fontSize: '0.75rem', color: '#818cf8' }}>
                                    • {m.name}
                                  </span>
                                ))}
                              </div>
                            ) : 'None'}
                          </td>
                          <td>
                            {item.samples && item.samples.length > 0 ? (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                {item.samples.map(s => (
                                  <span key={s.id} style={{ fontSize: '0.75rem', color: '#34d399' }}>
                                    • {s.name}
                                  </span>
                                ))}
                              </div>
                            ) : 'None'}
                          </td>
                          <td>
                            <span className={`badge badge-sentiment-${item.sentiment?.toLowerCase() || 'neutral'}`}>
                              {item.sentiment}
                            </span>
                          </td>
                          <td>
                            {item.tasks && item.tasks.length > 0 ? (
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                {item.tasks.map(t => (
                                  <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <span style={{ color: '#fbbf24' }}>⌛</span>
                                    <span>{t.description}</span>
                                  </div>
                                ))}
                              </div>
                            ) : 'None'}
                          </td>
                          <td>
                            <button 
                              className="btn btn-secondary" 
                              style={{ padding: '0.25rem 0.5rem', color: 'var(--accent-red)', borderColor: 'rgba(239, 68, 68, 0.2)', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                              onClick={() => {
                                if (window.confirm("Are you sure you want to delete this interaction log?")) {
                                  dispatch(deleteInteraction(item.id));
                                }
                              }}
                            >
                              <Trash2 size={12} /> Delete
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

      </main>

      {/* Voice Note Simulation Modal */}
      {showVoiceModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            
            <div className="panel-header">
              <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Mic size={18} className="text-primary" />
                Voice Note Dictation Simulator
              </h3>
              <button 
                onClick={closeVoiceSimulator}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={20} />
              </button>
            </div>

            <div className="voice-mic-wave-container">
              
              <div className={`pulse-mic-circle`}>
                <Mic size={32} />
              </div>
              
              <div className="voice-timer">
                {isRecording ? formatTime(voiceTimer) : "00:00"}
              </div>
              
              <div className="voice-status-msg">
                {isRecording ? "Recording representative audio input..." : "Select a simulation preset script below:"}
              </div>

              {/* Preset List */}
              <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '0.50rem' }}>
                {voicePresets.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleVoicePresetSelect(preset.text)}
                    className="suggestion-item-btn"
                    style={{ background: voiceTextPreset === preset.text ? 'rgba(99, 102, 241, 0.15)' : '' }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{preset.title}</div>
                      <div style={{ fontSize: '0.725rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '380px' }}>
                        {preset.text}
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {/* Dictation Output Display */}
              {voiceTextPreset && (
                <div style={{ marginTop: '1.25rem', width: '100%' }}>
                  <label>Transcribed Voice Text</label>
                  <textarea 
                    style={{ width: '100%', boxSizing: 'border-box', background: '#020617', minHeight: '70px', fontSize: '0.8rem', marginTop: '0.25rem' }}
                    value={voiceTextPreset}
                    onChange={(e) => setVoiceTextPreset(e.target.value)}
                  />
                </div>
              )}

            </div>

            <div className="modal-actions">
              <button 
                className="btn btn-secondary" 
                style={{ flex: 1 }} 
                onClick={closeVoiceSimulator}
              >
                Cancel
              </button>
              <button 
                className="btn btn-primary" 
                style={{ flex: 1 }} 
                onClick={submitVoiceDictation}
                disabled={!voiceTextPreset || isRecording}
              >
                Summarize & Fill Form
              </button>
            </div>

          </div>
        </div>
      )}
    </>
  );
}
