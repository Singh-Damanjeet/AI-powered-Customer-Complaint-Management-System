import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { configureStore } from '@reduxjs/toolkit'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Provider } from 'react-redux'

import ComplaintPage from './ComplaintPage'
import complaintReducer, {
  EMPTY_COMPLAINT,
  addPendingAuditEvent,
  setComplaint,
  setRiskAssessment,
} from '../store/complaintSlice'
import copilotReducer from '../store/copilotSlice'

vi.mock('../services/api', () => ({
  MAX_DOCUMENT_SIZE_BYTES: 10 * 1024 * 1024,
  SUPPORTED_DOCUMENT_EXTENSIONS: ['pdf', 'docx', 'txt', 'eml'],
  getApiErrorMessage: vi.fn((error, fallback) => error?.response?.data?.detail || fallback),
  getComplaintAudit: vi.fn(),
  saveComplaint: vi.fn(),
  sendAgentMessage: vi.fn(),
  uploadComplaintDocument: vi.fn(),
}))

import {
  saveComplaint,
  sendAgentMessage,
  uploadComplaintDocument,
} from '../services/api'

const initialComplaint = {
  ...EMPTY_COMPLAINT,
  complaint_source: 'Customer email',
  customer_name: 'ABC Pharma',
  product_name: 'Metformin',
  product_strength_grade: '500 mg',
  batch_lot_number: 'MT24003',
  quantity_affected: '120',
  quantity_unit: 'tablets',
  complaint_type: 'Discoloration',
  detailed_description: 'Brown discoloration was reported on tablets.',
}

const riskAssessment = {
  severity: 'Major',
  priority: 'High',
  rationale: 'Potential finished-product quality defect.',
  recommended_actions: ['Initiate QA investigation'],
  qa_investigation_required: true,
  product_replacement_recommended: false,
}

const responseFor = (complaint, changedFields = [], assessment = riskAssessment) => ({
  complaint: { ...EMPTY_COMPLAINT, ...complaint },
  risk_assessment: assessment,
  assistant_message: 'The complaint record has been updated.',
  changed_fields: changedFields,
})

const makeStore = () => configureStore({
  reducer: {
    complaint: complaintReducer,
    copilot: copilotReducer,
  },
})

const renderPage = (store = makeStore()) => {
  const renderResult = render(
    <Provider store={store}>
      <ComplaintPage />
    </Provider>,
  )
  return { ...renderResult, store }
}

const sendText = (text) => {
  fireEvent.change(screen.getByLabelText('AI Copilot message'), {
    target: { value: text },
  })
  fireEvent.click(screen.getByRole('button', { name: /send/i }))
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ComplaintPage AI workflow', () => {
  it('renders every complaint field as read-only', () => {
    renderPage()

    const fields = [
      'Complaint Source',
      'Customer Name',
      'Complainant Name',
      'Complainant Contact',
      'Product Type',
      'Product Name',
      'Product Strength / Grade',
      'Batch / Lot Number',
      'Manufacturing Date',
      'Expiry Date',
      'Quantity Affected',
      'Quantity Unit',
      'Complaint Type',
      'Complaint Date',
      'Received Date',
      'Detailed Complaint Description',
      'Severity',
      'Priority',
    ]

    fields.forEach((label) => {
      expect(screen.getByLabelText(label)).toHaveAttribute('readonly')
    })
  })

  it('populates the read-only form and risk card from an AI log response', async () => {
    sendAgentMessage.mockResolvedValueOnce(responseFor(initialComplaint, [
      'customer_name',
      'product_name',
      'batch_lot_number',
    ]))
    renderPage()

    sendText('ABC Pharma reported brown discoloration on Metformin tablets.')

    await waitFor(() => expect(screen.getByLabelText('Customer Name')).toHaveValue('ABC Pharma'))
    expect(screen.getByLabelText('Batch / Lot Number')).toHaveValue('MT24003')
    expect(screen.getByText('Potential finished-product quality defect.')).toBeInTheDocument()
    expect(screen.getAllByText('✦ AI updated').length).toBe(3)
  })

  it('sends the current complaint for edits and preserves unrelated values', async () => {
    sendAgentMessage
      .mockResolvedValueOnce(responseFor(initialComplaint, Object.keys(initialComplaint).filter((key) => initialComplaint[key] !== null)))
      .mockResolvedValueOnce(responseFor({ ...initialComplaint, batch_lot_number: 'MT24004', quantity_affected: '500' }, [
        'batch_lot_number',
        'quantity_affected',
      ]))
    renderPage()

    sendText('Log the complaint for ABC Pharma.')
    await waitFor(() => expect(screen.getByLabelText('Batch / Lot Number')).toHaveValue('MT24003'))

    sendText('Actually change the batch to MT24004 and quantity to 500.')
    await waitFor(() => expect(screen.getByLabelText('Batch / Lot Number')).toHaveValue('MT24004'))

    expect(sendAgentMessage).toHaveBeenNthCalledWith(2, expect.stringContaining('Actually'), initialComplaint)
    expect(screen.getByLabelText('Product Name')).toHaveValue('Metformin')
    expect(screen.getByLabelText('Quantity Affected')).toHaveValue('500')
  })

  it('preserves the current complaint when an AI request fails', async () => {
    const store = makeStore()
    store.dispatch(setComplaint(initialComplaint))
    store.dispatch(setRiskAssessment(riskAssessment))
    sendAgentMessage.mockRejectedValueOnce(new Error('network unavailable'))
    renderPage(store)

    sendText('Change the quantity to 500.')

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('The complaint could not be processed'))
    expect(screen.getByLabelText('Product Name')).toHaveValue('Metformin')
    expect(screen.getByLabelText('Quantity Affected')).toHaveValue('120')
    expect(screen.getByText('Potential finished-product quality defect.')).toBeInTheDocument()
  })

  it('populates the same form from a document upload', async () => {
    uploadComplaintDocument.mockResolvedValueOnce(responseFor(initialComplaint, ['product_name']))
    const { container, store } = renderPage()
    const file = new File(['complaint text'], 'complaint.txt', { type: 'text/plain' })

    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [file] },
    })

    await waitFor(() => expect(screen.getByLabelText('Product Name')).toHaveValue('Metformin'))
    expect(uploadComplaintDocument).toHaveBeenCalledWith(file)
    expect(store.getState().complaint.pendingAuditEvents).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          action: 'DOCUMENT_EXTRACTED',
          new_value: 'complaint.txt',
          source: 'AI',
        }),
      ]),
    )
  })

  it('tracks actual AI edits and risk changes in the unsaved local history', async () => {
    const changedRisk = { ...riskAssessment, severity: 'Critical', priority: 'Medium' }
    sendAgentMessage
      .mockResolvedValueOnce(responseFor(initialComplaint))
      .mockResolvedValueOnce(responseFor(
        { ...initialComplaint, batch_lot_number: 'MT24004', quantity_affected: '500' },
        ['batch_lot_number', 'quantity_affected'],
        changedRisk,
      ))
    const { store } = renderPage()

    sendText('Log the complaint for ABC Pharma.')
    await waitFor(() => expect(screen.getByLabelText('Batch / Lot Number')).toHaveValue('MT24003'))
    sendText('Change the batch to MT24004 and quantity to 500.')

    await waitFor(() => expect(screen.getByLabelText('Batch / Lot Number')).toHaveValue('MT24004'))
    const events = store.getState().complaint.pendingAuditEvents

    expect(events.map((event) => event.action)).toEqual([
      'AI_COMPLAINT_CREATED',
      'AI_EDITED_FIELD',
      'AI_EDITED_FIELD',
      'RISK_REASSESSED',
      'RISK_REASSESSED',
    ])
    expect(events[1]).toMatchObject({
      field_name: 'batch_lot_number',
      old_value: 'MT24003',
      new_value: 'MT24004',
      source: 'AI',
    })
    expect(events[2]).toMatchObject({
      field_name: 'quantity_affected',
      old_value: '120',
      new_value: '500',
    })
    expect(events[3]).toMatchObject({
      field_name: 'severity',
      old_value: 'Major',
      new_value: 'Critical',
    })
  })

  it('does not add an edit event when an AI edit is a no-op', async () => {
    sendAgentMessage
      .mockResolvedValueOnce(responseFor(initialComplaint))
      .mockResolvedValueOnce(responseFor(initialComplaint, ['quantity_affected']))
    const { store } = renderPage()

    sendText('Log the complaint for ABC Pharma.')
    await waitFor(() => expect(screen.getByLabelText('Quantity Affected')).toHaveValue('120'))
    sendText('Set the quantity to 120.')
    await waitFor(() => expect(sendAgentMessage).toHaveBeenCalledTimes(2))

    expect(store.getState().complaint.pendingAuditEvents.map((event) => event.action)).toEqual([
      'AI_COMPLAINT_CREATED',
    ])
  })

  it('shows the complaint number after an explicit save', async () => {
    const store = makeStore()
    store.dispatch(setComplaint(initialComplaint))
    store.dispatch(setRiskAssessment(riskAssessment))
    store.dispatch(addPendingAuditEvent({
      action: 'AI_COMPLAINT_CREATED',
      field_name: null,
      old_value: null,
      new_value: null,
      source: 'AI',
    }))
    saveComplaint.mockResolvedValueOnce({ complaint_number: 'CMP-2026-0007' })
    renderPage(store)

    fireEvent.click(screen.getByRole('button', { name: 'Save Complaint' }))

    await waitFor(() => expect(screen.getByText('Complaint saved as CMP-2026-0007')).toBeInTheDocument())
    expect(saveComplaint).toHaveBeenCalledWith(expect.objectContaining({
      complaint: expect.objectContaining({ product_name: 'Metformin' }),
      risk_assessment: riskAssessment,
      audit_events: [expect.objectContaining({ action: 'AI_COMPLAINT_CREATED' })],
    }))
    expect(store.getState().complaint.pendingAuditEvents).toEqual([])
    expect(screen.getAllByRole('button', { name: 'Saved' })).toHaveLength(2)
    expect(screen.getByLabelText('AI Copilot message')).toBeDisabled()
    expect(screen.getByLabelText('Choose file')).toBeDisabled()
    expect(screen.getByText('Complaint saved')).toBeInTheDocument()
  })

  it('preserves the complaint and pending audit events when save fails', async () => {
    const store = makeStore()
    store.dispatch(setComplaint(initialComplaint))
    store.dispatch(setRiskAssessment(riskAssessment))
    store.dispatch({
      type: 'complaint/addPendingAuditEvent',
      payload: {
        action: 'AI_EDITED_FIELD',
        field_name: 'quantity_affected',
        old_value: '120',
        new_value: '500',
        source: 'AI',
      },
    })
    saveComplaint.mockRejectedValueOnce({
      response: { status: 503, data: { detail: 'Save temporarily unavailable.' } },
    })
    renderPage(store)

    fireEvent.click(screen.getByRole('button', { name: 'Save Complaint' }))

    await waitFor(() => expect(screen.getByText('Save temporarily unavailable.')).toBeInTheDocument())
    expect(store.getState().complaint.complaint).toEqual(initialComplaint)
    expect(store.getState().complaint.riskAssessment).toEqual(riskAssessment)
    expect(store.getState().complaint.pendingAuditEvents).toHaveLength(1)
  })

  it('prevents duplicate save requests while the first save is pending', async () => {
    const store = makeStore()
    store.dispatch(setComplaint(initialComplaint))
    store.dispatch(setRiskAssessment(riskAssessment))
    let resolveSave
    saveComplaint.mockReturnValueOnce(new Promise((resolve) => {
      resolveSave = resolve
    }))
    renderPage(store)

    const saveButton = screen.getByRole('button', { name: 'Save Complaint' })
    fireEvent.click(saveButton)
    fireEvent.click(saveButton)

    expect(saveComplaint).toHaveBeenCalledTimes(1)
    resolveSave({ complaint_number: 'CMP-2026-0008' })
    await waitFor(() => expect(screen.getByText('Complaint saved as CMP-2026-0008')).toBeInTheDocument())
  })
})
