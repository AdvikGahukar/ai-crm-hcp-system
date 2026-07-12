import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const initialFormState = {
  hcp_id: '',
  hcp_name: '',
  type: 'Meeting',
  date: '',
  time: '',
  attendees: '',
  topics_discussed: '',
  sentiment: 'Neutral',
  outcomes: '',
  follow_up_actions: '',
  materials_shared: [], // list of IDs
  samples_distributed: [] // list of IDs
};

// Async Thunks
export const fetchHcps = createAsyncThunk('crm/fetchHcps', async () => {
  const response = await axios.get(`${API_BASE_URL}/hcps`);
  return response.data;
});

export const fetchMaterials = createAsyncThunk('crm/fetchMaterials', async () => {
  const response = await axios.get(`${API_BASE_URL}/materials`);
  return response.data;
});

export const fetchSamples = createAsyncThunk('crm/fetchSamples', async () => {
  const response = await axios.get(`${API_BASE_URL}/samples`);
  return response.data;
});

export const fetchInteractions = createAsyncThunk('crm/fetchInteractions', async () => {
  const response = await axios.get(`${API_BASE_URL}/interactions`);
  return response.data;
});

export const submitInteraction = createAsyncThunk(
  'crm/submitInteraction',
  async (formData, { dispatch, rejectWithValue }) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/interactions`, formData);
      dispatch(fetchInteractions());
      dispatch(fetchSamples()); // Refresh stock quantity
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to submit interaction');
    }
  }
);

export const sendChatMessage = createAsyncThunk(
  'crm/sendChatMessage',
  async ({ message, currentFormState }, { rejectWithValue }) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message,
        current_form_state: currentFormState
      });
      return response.data; // contains response (str), form_state (dict), logs (list)
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Chat assistant error');
    }
  }
);

export const summarizeVoiceNote = createAsyncThunk(
  'crm/summarizeVoiceNote',
  async (audioText, { rejectWithValue }) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/voice-summarize`, {
        audio_text: audioText
      });
      return response.data; // contains summary (str) and extracted_fields (dict)
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Voice note summarization error');
    }
  }
);

const crmSlice = createSlice({
  name: 'crm',
  initialState: {
    hcps: [],
    materials: [],
    samples: [],
    interactions: [],
    currentFormState: { ...initialFormState },
    chatHistory: [
      {
        sender: 'assistant',
        text: 'Hello! I am your AI CRM Assistant. You can describe your interaction here (e.g. "I had a call with Dr. Sarah Patel, we discussed OncoBoost efficacy and she was very positive") and I will automatically parse it and log it for you.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        logs: []
      }
    ],
    agentLogs: [],
    loading: false,
    chatLoading: false,
    voiceLoading: false,
    error: null
  },
  reducers: {
    updateFormState: (state, action) => {
      state.currentFormState = { ...state.currentFormState, ...action.payload };
    },
    clearFormState: (state) => {
      state.currentFormState = { ...initialFormState };
    },
    addChatMessage: (state, action) => {
      state.chatHistory.push(action.payload);
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch HCPs
      .addCase(fetchHcps.fulfilled, (state, action) => {
        state.hcps = action.payload;
      })
      // Fetch Materials
      .addCase(fetchMaterials.fulfilled, (state, action) => {
        state.materials = action.payload;
      })
      // Fetch Samples
      .addCase(fetchSamples.fulfilled, (state, action) => {
        state.samples = action.payload;
      })
      // Fetch Interactions
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.interactions = action.payload;
      })
      // Submit Interaction
      .addCase(submitInteraction.pending, (state) => {
        state.loading = true;
      })
      .addCase(submitInteraction.fulfilled, (state) => {
        state.loading = false;
        state.currentFormState = { ...initialFormState };
      })
      .addCase(submitInteraction.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // Chat message
      .addCase(sendChatMessage.pending, (state) => {
        state.chatLoading = true;
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.chatLoading = false;
        const { response, form_state, logs } = action.payload;
        
        // Clean assistant text response by removing the JSON codeblock
        let cleanText = response;
        const jsonBlockRegex = /```json\s*[\s\S]*?\s*```/g;
        cleanText = cleanText.replace(jsonBlockRegex, '').trim();

        state.chatHistory.push({
          sender: 'assistant',
          text: cleanText,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          logs: logs || []
        });

        state.agentLogs = logs || [];

        // Sync the form state
        if (form_state) {
          state.currentFormState = { ...state.currentFormState, ...form_state };
        }
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.chatLoading = false;
        state.chatHistory.push({
          sender: 'assistant',
          text: `Sorry, I encountered an error: ${action.payload}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          logs: []
        });
      })
      // Summarize voice note
      .addCase(summarizeVoiceNote.pending, (state) => {
        state.voiceLoading = true;
      })
      .addCase(summarizeVoiceNote.fulfilled, (state, action) => {
        state.voiceLoading = false;
        const { extracted_fields } = action.payload;
        
        // Match HCP name to ID from our HCP list
        let matchedHcpId = '';
        if (extracted_fields.hcp_name) {
          const match = state.hcps.find(h => h.name.toLowerCase().includes(extracted_fields.hcp_name.toLowerCase()));
          if (match) {
            matchedHcpId = match.id;
            extracted_fields.hcp_name = match.name; // Use standard name
          }
        }

        const updates = {
          ...extracted_fields,
          hcp_id: matchedHcpId || state.currentFormState.hcp_id
        };
        delete updates.hcp_name; // Do not save HCP name directly in form state, it's keyed by hcp_id

        state.currentFormState = { ...state.currentFormState, ...updates };
      })
      .addCase(summarizeVoiceNote.rejected, (state, action) => {
        state.voiceLoading = false;
        state.error = action.payload;
      });
  }
});

export const { updateFormState, clearFormState, addChatMessage } = crmSlice.actions;
export default crmSlice.reducer;
