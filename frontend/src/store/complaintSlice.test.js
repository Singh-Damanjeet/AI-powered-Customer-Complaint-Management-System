import { describe, expect, it } from 'vitest'

import complaintReducer, {
  EMPTY_COMPLAINT,
  addPendingAuditEvent,
  clearPendingAuditEvents,
  resetComplaintState,
  setAuditEvents,
  setAiInsights,
  setChangedFields,
  setComplaint,
  setRiskAssessment,
} from './complaintSlice'

const assessment = {
  severity: 'Major',
  priority: 'High',
  rationale: 'Potential product quality defect.',
  recommended_actions: ['Initiate QA investigation'],
  qa_investigation_required: true,
  product_replacement_recommended: false,
}

describe('complaintSlice', () => {
  it('sets and normalizes complaint data', () => {
    const state = complaintReducer(undefined, setComplaint({ customer_name: 'ABC Pharma' }))

    expect(state.complaint.customer_name).toBe('ABC Pharma')
    expect(state.complaint.batch_lot_number).toBeNull()
    expect(Object.keys(state.complaint)).toEqual(Object.keys(EMPTY_COMPLAINT))
  })

  it('updates risk assessment and changed fields', () => {
    let state = complaintReducer(undefined, setRiskAssessment(assessment))
    state = complaintReducer(state, setChangedFields(['batch_lot_number', 'quantity_affected']))

    expect(state.riskAssessment).toEqual(assessment)
    expect(state.changedFields).toEqual(['batch_lot_number', 'quantity_affected'])
  })

  it('stores optional AI insights and reset clears them', () => {
    const insights = {
      completeness: {
        score: 82,
        status: 'MOSTLY_COMPLETE',
        missing_fields: ['expiry_date'],
        missing_critical_fields: [],
        message: 'Some details are still missing.',
      },
    }
    let state = complaintReducer(undefined, setAiInsights(insights))

    expect(state.aiInsights).toEqual(insights)
    state = complaintReducer(state, resetComplaintState())
    expect(state.aiInsights).toBeNull()
  })

  it('reset clears the working complaint, risk, changed fields, and save state', () => {
    let state = complaintReducer(undefined, setComplaint({
      product_name: 'Metformin',
      quantity_affected: '120',
    }))
    state = complaintReducer(state, setRiskAssessment(assessment))
    state = complaintReducer(state, setChangedFields(['product_name']))
    state = complaintReducer(state, addPendingAuditEvent({ action: 'AI_COMPLAINT_CREATED' }))
    state = complaintReducer(state, setAuditEvents([{ action: 'COMPLAINT_SAVED' }]))

    state = complaintReducer(state, resetComplaintState())

    expect(state.complaint).toEqual(EMPTY_COMPLAINT)
    expect(state.riskAssessment).toBeNull()
    expect(state.changedFields).toEqual([])
    expect(state.pendingAuditEvents).toEqual([])
    expect(state.auditEvents).toEqual([])
    expect(state.savedComplaint).toBeNull()
    expect(state.saveStatus).toBe('idle')
    expect(state.saveError).toBeNull()
  })

  it('supports adding and clearing pending audit events independently', () => {
    let state = complaintReducer(undefined, addPendingAuditEvent({
      action: 'AI_EDITED_FIELD',
      field_name: 'quantity_affected',
    }))
    state = complaintReducer(state, clearPendingAuditEvents())

    expect(state.pendingAuditEvents).toEqual([])
  })
})
