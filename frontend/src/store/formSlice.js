import { createSlice } from '@reduxjs/toolkit';

const getTodayDate = () => {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const getCurrentTime = () => {
  const d = new Date();
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${hours}:${minutes}`;
};

const initialState = {
  hcp_id: '',
  hcp_name: '',
  interaction_type: 'Meeting',
  date: getTodayDate(),
  time: getCurrentTime(),
  attendees: [],
  topics_discussed: '',
  materials_shared: [],
  samples_distributed: [],
  sentiment: 'Neutral',
  outcomes: '',
  follow_up_actions: '',
};

const formSlice = createSlice({
  name: 'interactionForm',
  initialState,
  reducers: {
    updateField: (state, action) => {
      const { key, value } = action.payload;
      state[key] = value;
    },
    setFormState: (state, action) => {
      return { ...state, ...action.payload };
    },
    clearForm: (state) => {
      return {
        ...initialState,
        date: getTodayDate(),
        time: getCurrentTime(),
      };
    },
    addAttendee: (state, action) => {
      const name = action.payload.trim();
      if (name && !state.attendees.includes(name)) {
        state.attendees.push(name);
      }
    },
    removeAttendee: (state, action) => {
      state.attendees = state.attendees.filter(name => name !== action.payload);
    },
    addMaterial: (state, action) => {
      const mat = action.payload.trim();
      if (mat && !state.materials_shared.includes(mat)) {
        state.materials_shared.push(mat);
      }
    },
    removeMaterial: (state, action) => {
      state.materials_shared = state.materials_shared.filter(mat => mat !== action.payload);
    },
    addSample: (state, action) => {
      const sam = action.payload.trim();
      if (sam && !state.samples_distributed.includes(sam)) {
        state.samples_distributed.push(sam);
      }
    },
    removeSample: (state, action) => {
      state.samples_distributed = state.samples_distributed.filter(sam => sam !== action.payload);
    },
  },
});

export const {
  updateField,
  setFormState,
  clearForm,
  addAttendee,
  removeAttendee,
  addMaterial,
  removeMaterial,
  addSample,
  removeSample,
} = formSlice.actions;

export default formSlice.reducer;
