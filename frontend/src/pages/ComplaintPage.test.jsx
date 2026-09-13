import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { configureStore } from '@reduxjs/toolkit'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Provider } from 'react-redux'

import ComplaintPage from './ComplaintPage'
import complaintReducer, { EMPTY_COMPLAINT, setComplaint, setRiskAssessment } from '../store/complaintSlice'
import copilotReducer from '../store/copilotSlice'

vi.mock('../services/api', () => ({
  MAX_DOCUMENT_SIZE_BYTES: 10 * 1024 * 1024,
  SUPPORTED_DOCUMENT_EXTENSIONS: ['pdf', 'docx', 'txt', 'eml'],
  getApiErrorMessage: vi.fn((error, fallback) => error?.response?.data?.detail || fallback),
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

const responseFor = (complaint, changedFields = []) => ({
  complaint: { ...EMPTY_COMPLAINT, ...complaint },
  risk_assessment: riskAssessment,
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
    const { container } = renderPage()
    const file = new File(['complaint text'], 'complaint.txt', { type: 'text/plain' })

    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [file] },
    })

    await waitFor(() => expect(screen.getByLabelText('Product Name')).toHaveValue('Metformin'))
    expect(uploadComplaintDocument).toHaveBeenCalledWith(file)
  })

  it('shows the complaint number after an explicit save', async () => {
    const store = makeStore()
    store.dispatch(setComplaint(initialComplaint))
    store.dispatch(setRiskAssessment(riskAssessment))
    saveComplaint.mockResolvedValueOnce({ complaint_number: 'CMP-2026-0007' })
    renderPage(store)

    fireEvent.click(screen.getByRole('button', { name: 'Save Complaint' }))

    await waitFor(() => expect(screen.getByText('Complaint saved as CMP-2026-0007')).toBeInTheDocument())
    expect(saveComplaint).toHaveBeenCalledWith(expect.objectContaining({
      product_name: 'Metformin',
      risk_assessment: riskAssessment,
    }))
  })
})
