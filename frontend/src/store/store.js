import { configureStore } from '@reduxjs/toolkit'

import complaintReducer from './complaintSlice'
import copilotReducer from './copilotSlice'

export const store = configureStore({
  reducer: {
    complaint: complaintReducer,
    copilot: copilotReducer,
  },
})
