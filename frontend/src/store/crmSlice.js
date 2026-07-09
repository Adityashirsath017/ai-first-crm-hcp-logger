import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { clearForm } from './formSlice';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const fetchHCPs = createAsyncThunk('crm/fetchHCPs', async (_, { rejectWithValue }) => {
  try {
    const response = await fetch(`${API_URL}/api/hcps`);
    if (!response.ok) throw new Error('Failed to fetch HCPs');
    return await response.json();
  } catch (err) {
    return rejectWithValue(err.message);
  }
});

export const fetchCatalog = createAsyncThunk('crm/fetchCatalog', async (_, { rejectWithValue }) => {
  try {
    const response = await fetch(`${API_URL}/api/catalog`);
    if (!response.ok) throw new Error('Failed to fetch catalog');
    return await response.json(); // Array of { id, name, category, description }
  } catch (err) {
    return rejectWithValue(err.message);
  }
});

export const fetchInteractions = createAsyncThunk('crm/fetchInteractions', async (_, { rejectWithValue }) => {
  try {
    const response = await fetch(`${API_URL}/api/interactions`);
    if (!response.ok) throw new Error('Failed to fetch interactions');
    return await response.json();
  } catch (err) {
    return rejectWithValue(err.message);
  }
});

export const submitLogInteraction = createAsyncThunk(
  'crm/submitLog',
  async (formData, { dispatch, rejectWithValue }) => {
    try {
      const response = await fetch(`${API_URL}/api/interactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to log interaction');
      }
      const data = await response.json();
      dispatch(clearForm());
      dispatch(fetchInteractions());
      return data;
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const editInteractionAPI = createAsyncThunk(
  'crm/editInteraction',
  async ({ interactionId, updateData }, { dispatch, rejectWithValue }) => {
    try {
      const response = await fetch(`${API_URL}/api/interactions/${interactionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update interaction');
      }
      const data = await response.json();
      dispatch(fetchInteractions());
      return data;
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

const crmSlice = createSlice({
  name: 'crm',
  initialState: {
    hcps: [],
    catalog: [],
    interactions: [],
    loading: false,
    error: null,
    submitting: false,
    submitSuccess: false,
  },
  reducers: {
    resetSubmitSuccess: (state) => {
      state.submitSuccess = false;
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch HCPs
      .addCase(fetchHCPs.pending, (state) => { state.loading = true; })
      .addCase(fetchHCPs.fulfilled, (state, action) => {
        state.loading = false;
        state.hcps = action.payload;
      })
      .addCase(fetchHCPs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // Fetch Catalog
      .addCase(fetchCatalog.fulfilled, (state, action) => {
        state.catalog = action.payload;
      })
      // Fetch Interactions
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.interactions = action.payload;
      })
      // Submit Log
      .addCase(submitLogInteraction.pending, (state) => {
        state.submitting = true;
        state.submitSuccess = false;
      })
      .addCase(submitLogInteraction.fulfilled, (state) => {
        state.submitting = false;
        state.submitSuccess = true;
      })
      .addCase(submitLogInteraction.rejected, (state, action) => {
        state.submitting = false;
        state.error = action.payload;
      })
      // Edit Interaction
      .addCase(editInteractionAPI.pending, (state) => {
        state.submitting = true;
      })
      .addCase(editInteractionAPI.fulfilled, (state) => {
        state.submitting = false;
      })
      .addCase(editInteractionAPI.rejected, (state, action) => {
        state.submitting = false;
        state.error = action.payload;
      });
  },
});

export const { resetSubmitSuccess } = crmSlice.actions;
export default crmSlice.reducer;
