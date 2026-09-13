import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  messages: [],
  status: 'idle',
  error: null,
  uploadedFileName: null,
  processingMessage: null,
}

let messageSequence = 0

export const createMessage = (role, content) => {
  messageSequence += 1
  return {
    id: `${Date.now()}-${messageSequence}`,
    role,
    content,
    timestamp: new Date().toISOString(),
  }
}

const copilotSlice = createSlice({
  name: 'copilot',
  initialState,
  reducers: {
    addMessage(state, action) {
      state.messages.push(action.payload)
    },
    clearMessages(state) {
      state.messages = []
    },
    setCopilotError(state, action) {
      state.error = action.payload || null
    },
    setCopilotStatus(state, action) {
      state.status = action.payload
    },
    setProcessingMessage(state, action) {
      state.processingMessage = action.payload || null
    },
    setUploadedFileName(state, action) {
      state.uploadedFileName = action.payload || null
    },
    resetCopilot() {
      return { ...initialState, messages: [] }
    },
  },
})

export const {
  addMessage,
  clearMessages,
  resetCopilot,
  setCopilotError,
  setCopilotStatus,
  setProcessingMessage,
  setUploadedFileName,
} = copilotSlice.actions

export default copilotSlice.reducer
