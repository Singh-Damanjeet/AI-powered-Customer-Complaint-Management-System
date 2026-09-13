import { useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'

import {
  MAX_DOCUMENT_SIZE_BYTES,
  SUPPORTED_DOCUMENT_EXTENSIONS,
  getApiErrorMessage,
  saveComplaint,
  sendAgentMessage,
  uploadComplaintDocument,
} from '../services/api'
import {
  resetComplaintState,
  setChangedFields,
  setComplaint,
  setRiskAssessment,
  setSaveError,
  setSavedComplaint,
  setSaveStatus,
} from '../store/complaintSlice'
import {
  addMessage,
  createMessage,
  resetCopilot,
  setCopilotError,
  setCopilotStatus,
  setProcessingMessage,
  setUploadedFileName,
} from '../store/copilotSlice'

const complaintHasFacts = (complaint) =>
  Object.values(complaint || {}).some(
    (value) => value !== null && value !== undefined && value !== '',
  )

const extensionFor = (filename) => {
  const parts = String(filename || '').toLowerCase().split('.')
  return parts.length > 1 ? parts.at(-1) : ''
}

const assertAgentResponse = (response) => {
  if (!response || !response.complaint || !response.risk_assessment) {
    throw new Error('The server returned an incomplete complaint response.')
  }
  return response
}

const applyAgentResponse = (dispatch, response) => {
  const validResponse = assertAgentResponse(response)
  dispatch(setComplaint(validResponse.complaint))
  dispatch(setRiskAssessment(validResponse.risk_assessment))
  dispatch(setChangedFields(validResponse.changed_fields || []))
  dispatch(setSavedComplaint(null))
  dispatch(setSaveStatus('idle'))
  dispatch(setSaveError(null))
  dispatch(
    addMessage(
      createMessage(
        'assistant',
        validResponse.assistant_message || 'Complaint state updated.',
      ),
    ),
  )
  return validResponse
}

export function useComplaintWorkflow() {
  const dispatch = useDispatch()
  const complaint = useSelector((state) => state.complaint.complaint)
  const riskAssessment = useSelector((state) => state.complaint.riskAssessment)
  const copilotStatus = useSelector((state) => state.copilot.status)

  const isProcessing = copilotStatus === 'processing'

  const failWorkflow = useCallback(
    (error, fallback) => {
      const message = getApiErrorMessage(error, fallback)
      dispatch(setCopilotStatus('error'))
      dispatch(setCopilotError(message))
      dispatch(setProcessingMessage(null))
      dispatch(addMessage(createMessage('system', message)))
      return message
    },
    [dispatch],
  )

  const runAgentRequest = useCallback(
    async (request, processingMessage, successFallback) => {
      dispatch(setCopilotStatus('processing'))
      dispatch(setCopilotError(null))
      dispatch(setProcessingMessage(processingMessage))

      try {
        const response = await request()
        const appliedResponse = applyAgentResponse(dispatch, response)
        dispatch(setCopilotStatus('success'))
        dispatch(setProcessingMessage(null))
        return appliedResponse
      } catch (error) {
        failWorkflow(error, successFallback)
        return null
      }
    },
    [dispatch, failWorkflow],
  )

  const submitMessage = useCallback(
    async (rawMessage) => {
      const message = String(rawMessage || '').trim()
      if (!message || isProcessing) {
        return null
      }

      dispatch(addMessage(createMessage('user', message)))
      const currentComplaint = complaintHasFacts(complaint) ? complaint : null
      return runAgentRequest(
        () => sendAgentMessage(message, currentComplaint),
        'AI is reading the complaint and assessing risk…',
        'The complaint could not be processed. Your current complaint data has been preserved.',
      )
    },
    [complaint, dispatch, isProcessing, runAgentRequest],
  )

  const uploadDocument = useCallback(
    async (file) => {
      if (!file || isProcessing) {
        return null
      }

      const extension = extensionFor(file.name)
      if (!SUPPORTED_DOCUMENT_EXTENSIONS.includes(extension)) {
        failWorkflow(
          { response: { status: 415, data: { detail: '' } } },
          'This file type is not supported. Use PDF, DOCX, TXT, or EML.',
        )
        return null
      }
      if (file.size > MAX_DOCUMENT_SIZE_BYTES) {
        failWorkflow(
          { response: { status: 413, data: { detail: '' } } },
          'This document is too large. Please choose a file under 10 MB.',
        )
        return null
      }

      dispatch(setUploadedFileName(file.name))
      return runAgentRequest(
        () => uploadComplaintDocument(file),
        'Uploading document and extracting complaint details…',
        'The document could not be processed. Your current complaint data has been preserved.',
      )
    },
    [dispatch, failWorkflow, isProcessing, runAgentRequest],
  )

  const saveCurrentComplaint = useCallback(async () => {
    if (isProcessing) {
      return null
    }

    dispatch(setSaveStatus('saving'))
    dispatch(setSaveError(null))
    try {
      const payload = { ...complaint }
      if (riskAssessment) {
        payload.risk_assessment = riskAssessment
      }
      const saved = await saveComplaint(payload)
      dispatch(setSavedComplaint(saved))
      dispatch(setSaveStatus('success'))
      return saved
    } catch (error) {
      const message = getApiErrorMessage(
        error,
        'The complaint could not be saved. Please try again.',
      )
      dispatch(setSaveStatus('error'))
      dispatch(setSaveError(message))
      return null
    }
  }, [complaint, dispatch, isProcessing, riskAssessment])

  const resetWorkspace = useCallback(() => {
    dispatch(resetComplaintState())
    dispatch(resetCopilot())
  }, [dispatch])

  return {
    isProcessing,
    resetWorkspace,
    saveCurrentComplaint,
    submitMessage,
    uploadDocument,
  }
}

export { complaintHasFacts, extensionFor }
