import { configureStore } from '@reduxjs/toolkit';
import formReducer from './formSlice';
import chatReducer from './chatSlice';
import crmReducer from './crmSlice';

export const store = configureStore({
  reducer: {
    interactionForm: formReducer,
    chat: chatReducer,
    crm: crmReducer,
  },
});

export default store;
