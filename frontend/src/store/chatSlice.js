import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { setFormState } from './formSlice';
import { fetchInteractions } from './crmSlice';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ message, currentFormState }, { dispatch, getState, rejectWithValue }) => {
    try {
      // Get full messages history from Redux state (which already includes the new user message)
      const messagesHistory = getState().chat.messages;
      const apiMessages = messagesHistory.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await fetch(`${API_URL}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: apiMessages,
          form_state: currentFormState
        })
      });

      if (!response.ok) {
        throw new Error('Failed to reach AI Agent');
      }

      const data = await response.json();
      
      // Update form state with the extracted entity values
      dispatch(setFormState(data.updated_form));
      
      // Refresh interactions list if logged or updated
      const replyLower = data.reply.toLowerCase();
      if (
        replyLower.includes('logged') || 
        replyLower.includes('saved') || 
        replyLower.includes('updated') || 
        replyLower.includes('success')
      ) {
        dispatch(fetchInteractions());
      }
      
      return data; // { reply, updated_form, suggestions }
    } catch (err) {
      return rejectWithValue(err.message || 'Something went wrong');
    }
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [
      {
        role: 'assistant',
        content: "Hello! I am your AI CRM Assistant. You can describe your interaction here (e.g., 'Met Dr. Sharma today, discussed OncoBoost efficacy. He was positive and asked for OncoBoost Phase III PDF. Dosing was set to 10mg.'). I will automatically fill out the form for you!"
      }
    ],
    suggestions: [
      "Schedule follow-up meeting in 2 weeks",
      "Send OncoBoost Phase III PDF",
      "Add Dr. Sharma to advisory board invite list"
    ],
    loading: false,
    error: null,
  },
  reducers: {
    addMessage: (state, action) => {
      state.messages.push(action.payload);
    },
    clearChat: (state) => {
      state.messages = [
        {
          role: 'assistant',
          content: "Chat cleared. Describe a new interaction or ask for help."
        }
      ];
      state.suggestions = [];
    },
    setSuggestions: (state, action) => {
      state.suggestions = action.payload;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.loading = false;
        state.messages.push({
          role: 'assistant',
          content: action.payload.reply
        });
        state.suggestions = action.payload.suggestions || [];
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
        state.messages.push({
          role: 'assistant',
          content: `Sorry, I encountered an error: ${action.payload}. Please make sure the backend server is running.`
        });
      });
  }
});

export const { addMessage, clearChat, setSuggestions } = chatSlice.actions;
export default chatSlice.reducer;
