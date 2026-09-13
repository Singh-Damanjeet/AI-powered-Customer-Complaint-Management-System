import { createSlice } from '@reduxjs/toolkit'

export const EMPTY_COMPLAINT = {
  complaint_source: null,
  customer_name: null,
  complainant_name: null,
  complainant_contact: null,
  product_type: null,
  product_name: null,
  product_strength_grade: null,
  batch_lot_number: null,
  manufacturing_date: null,
  expiry_date: null,
  quantity_affected: null,
  quantity_unit: null,
  complaint_type: null,
  complaint_date: null,
  received_date: null,
  detailed_description: null,
}

export const COMPLAINT_FIELD_KEYS = Object.keys(EMPTY_COMPLAINT)

const createEmptyComplaint = () => ({ ...EMPTY_COMPLAINT })

const normalizeComplaint = (complaint) => ({
  ...EMPTY_COMPLAINT,
  ...(complaint && typeof complaint === 'object' ? complaint : {}),
})

const initialState = {
  complaint: createEmptyComplaint(),
  riskAssessment: null,
  changedFields: [],
  savedComplaint: null,
  saveStatus: 'idle',
  saveError: null,
}

const complaintSlice = createSlice({
  name: 'complaint',
  initialState,
  reducers: {
    setComplaint(state, action) {
      state.complaint = normalizeComplaint(action.payload)
    },
    setRiskAssessment(state, action) {
      state.riskAssessment = action.payload || null
    },
    setChangedFields(state, action) {
      state.changedFields = Array.isArray(action.payload)
        ? action.payload.filter((fieldName) => typeof fieldName === 'string')
        : []
    },
    clearComplaint(state) {
      state.complaint = createEmptyComplaint()
    },
    setSavedComplaint(state, action) {
      state.savedComplaint = action.payload || null
    },
    setSaveStatus(state, action) {
      state.saveStatus = action.payload
    },
    setSaveError(state, action) {
      state.saveError = action.payload || null
    },
    resetComplaintState() {
      return {
        ...initialState,
        complaint: createEmptyComplaint(),
      }
    },
  },
})

export const {
  clearComplaint,
  resetComplaintState,
  setChangedFields,
  setComplaint,
  setRiskAssessment,
  setSaveError,
  setSavedComplaint,
  setSaveStatus,
} = complaintSlice.actions

export default complaintSlice.reducer
