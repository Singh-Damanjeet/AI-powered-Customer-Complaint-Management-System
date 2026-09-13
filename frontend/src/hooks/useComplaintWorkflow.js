import { useCallback, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'

import {
  MAX_DOCUMENT_SIZE_BYTES,
  SUPPORTED_DOCUMENT_EXTENSIONS,
  getApiErrorMessage,
  getComplaintAudit,
  saveComplaint,
  sendAgentMessage,
  uploadComplaintDocument,
} from '../services/api'
import {
  COMPLAINT_FIELD_KEYS,
  addPendingAuditEvents,
  clearPendingAuditEvents,
  resetComplaintState,
  setAuditEvents,
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

const RISK_AUDIT_FIELDS = ['severity', 'priority']
const CREATION_ACTIONS = new Set(['AI_COMPLAINT_CREATED', 'COMPLAINT_CREATED'])

const complaintHasFacts = (complaint) =>
  Object.values(complaint || {}).some(
    (value) => value !== null && value !== undefined && value !== '',
  )

const extensionFor = (filename) => {
  const parts = String(filename || '').toLowerCase().split('.')
  return parts.length > 1 ? parts.at(-1) : ''
}

const valuesEqual = (left, right) => {
  if (left === right) return true
  if (left === null || left === undefined || right === null || right === undefined) {
    return false
  }

  // Backend decimal values are serialized as strings while locally mocked or
  // freshly returned values may be numbers. Treat those representations as
  // the same factual value when both are numeric.
  if (
    (typeof left === 'number' || typeof left === 'string') &&
    (typeof right === 'number' || typeof right === 'string') &&
    left !== '' &&
    right !== ''
  ) {
    const leftNumber = Number(left)
    const rightNumber = Number(right)
    if (!Number.isNaN(leftNumber) && !Number.isNaN(rightNumber)) {
      return leftNumber === rightNumber
    }
  }

  return JSON.stringify(left) === JSON.stringify(right)
}

const createAuditEvent = (
  action,
  fieldName = null,
  oldValue = null,
  newValue = null,
  source = 'AI',
) => ({
  action,
  field_name: fieldName ?? null,
  old_value: oldValue ?? null,
  new_value: newValue ?? null,
  source,
  created_at: new Date().toISOString(),
})

const actualComplaintChanges = (before, after) =>
  COMPLAINT_FIELD_KEYS.filter(
    (fieldName) => !valuesEqual(before?.[fieldName], after?.[fieldName]),
  )

const deriveAuditEvents = ({
  previousComplaint,
  nextComplaint,
  previousRiskAssessment,
  nextRiskAssessment,
  origin = 'chat',
  filename = null,
  pendingAuditEvents = [],
}) => {
  const events = []
  const actualChanges = actualComplaintChanges(previousComplaint, nextComplaint)
  const alreadyCreated = pendingAuditEvents.some((event) =>
    CREATION_ACTIONS.has(event?.action),
  )

  if (origin === 'document') {
    events.push(createAuditEvent('DOCUMENT_EXTRACTED', null, null, filename))
    if (complaintHasFacts(previousComplaint)) {
      actualChanges.forEach((fieldName) => {
        events.push(
          createAuditEvent(
            'AI_EDITED_FIELD',
            fieldName,
            previousComplaint?.[fieldName],
            nextComplaint?.[fieldName],
          ),
        )
      })
    }
  } else if (!complaintHasFacts(previousComplaint)) {
    if (!alreadyCreated) {
      events.push(createAuditEvent('AI_COMPLAINT_CREATED'))
    }
  } else {
    actualChanges.forEach((fieldName) => {
      events.push(
        createAuditEvent(
          'AI_EDITED_FIELD',
          fieldName,
          previousComplaint?.[fieldName],
          nextComplaint?.[fieldName],
        ),
      )
    })
  }

  if (previousRiskAssessment && nextRiskAssessment) {
    RISK_AUDIT_FIELDS.forEach((fieldName) => {
      if (!valuesEqual(previousRiskAssessment[fieldName], nextRiskAssessment[fieldName])) {
        events.push(
          createAuditEvent(
            'RISK_REASSESSED',
            fieldName,
            previousRiskAssessment[fieldName],
            nextRiskAssessment[fieldName],
          ),
        )
      }
    })
  }

  return events
}

const assertAgentResponse = (response) => {
  if (!response || !response.complaint || !response.risk_assessment) {
    throw new Error('The server returned an incomplete complaint response.')
  }
  return response
}

const applyAgentResponse = (
  dispatch,
  response,
  {
    previousComplaint = {},
    previousRiskAssessment = null,
    origin = 'chat',
    filename = null,
    pendingAuditEvents = [],
  } = {},
) => {
  const validResponse = assertAgentResponse(response)
  const auditEvents = deriveAuditEvents({
    previousComplaint,
    nextComplaint: validResponse.complaint,
    previousRiskAssessment,
    nextRiskAssessment: validResponse.risk_assessment,
    origin,
    filename,
    pendingAuditEvents,
  })

  dispatch(setComplaint(validResponse.complaint))
  dispatch(setRiskAssessment(validResponse.risk_assessment))
  dispatch(setChangedFields(validResponse.changed_fields || []))
  dispatch(setAuditEvents([]))
  if (auditEvents.length) {
    dispatch(addPendingAuditEvents(auditEvents))
  }
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

const auditPayload = (event) => {
  const { created_at: _createdAt, id: _id, ...payload } = event
  return payload
}

const auditItemsFromResponse = (response) => {
  if (Array.isArray(response)) return response
  if (Array.isArray(response?.items)) return response.items
  return []
}

export function useComplaintWorkflow() {
  const dispatch = useDispatch()
  const complaintState = useSelector((state) => state.complaint)
  const complaint = complaintState.complaint
  const riskAssessment = complaintState.riskAssessment
  const pendingAuditEvents = complaintState.pendingAuditEvents || []
  const savedComplaint = complaintState.savedComplaint
  const saveStatus = complaintState.saveStatus
  const copilotStatus = useSelector((state) => state.copilot.status)
  const savingRef = useRef(false)

  const isProcessing = copilotStatus === 'processing'
  const isSaved = Boolean(savedComplaint)

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
    async (request, processingMessage, successFallback, context = {}) => {
      dispatch(setCopilotStatus('processing'))
      dispatch(setCopilotError(null))
      dispatch(setProcessingMessage(processingMessage))

      try {
        const response = await request()
        const appliedResponse = applyAgentResponse(dispatch, response, {
          ...context,
          pendingAuditEvents,
        })
        dispatch(setCopilotStatus('success'))
        dispatch(setProcessingMessage(null))
        return appliedResponse
      } catch (error) {
        failWorkflow(error, successFallback)
        return null
      }
    },
    [dispatch, failWorkflow, pendingAuditEvents],
  )

  const submitMessage = useCallback(
    async (rawMessage) => {
      const message = String(rawMessage || '').trim()
      if (!message || isProcessing || isSaved) {
        return null
      }

      dispatch(addMessage(createMessage('user', message)))
      const currentComplaint = complaintHasFacts(complaint) ? complaint : null
      return runAgentRequest(
        () => sendAgentMessage(message, currentComplaint),
        'AI is reading the complaint and assessing risk…',
        'The complaint could not be processed. Your current complaint data has been preserved.',
        {
          previousComplaint: complaint,
          previousRiskAssessment: riskAssessment,
          origin: 'chat',
        },
      )
    },
    [complaint, dispatch, isProcessing, isSaved, riskAssessment, runAgentRequest],
  )

  const uploadDocument = useCallback(
    async (file) => {
      if (!file || isProcessing || isSaved) {
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
        {
          previousComplaint: complaint,
          previousRiskAssessment: riskAssessment,
          origin: 'document',
          filename: file.name,
        },
      )
    },
    [complaint, dispatch, failWorkflow, isProcessing, isSaved, riskAssessment, runAgentRequest],
  )

  const saveCurrentComplaint = useCallback(async () => {
    if (isProcessing || isSaved || saveStatus === 'saving' || savingRef.current) {
      return null
    }

    savingRef.current = true
    const pendingForRequest = pendingAuditEvents.map((event) => ({ ...event }))
    dispatch(setSaveStatus('saving'))
    dispatch(setSaveError(null))
    try {
      const saved = await saveComplaint({
        complaint: { ...complaint },
        risk_assessment: riskAssessment,
        audit_events: pendingForRequest.map(auditPayload),
      })
      if (!saved || typeof saved !== 'object') {
        throw new Error('The server returned an incomplete saved complaint.')
      }

      dispatch(setSavedComplaint(saved))
      dispatch(setSaveStatus('success'))

      const savedEvent = createAuditEvent(
        'COMPLAINT_SAVED',
        null,
        null,
        saved.complaint_number,
        'SYSTEM',
      )
      let persistedItems = []
      if (saved.id && typeof getComplaintAudit === 'function') {
        try {
          persistedItems = auditItemsFromResponse(await getComplaintAudit(saved.id))
        } catch {
          // The complaint is already committed. Keep a useful local history
          // fallback if the optional refresh request fails.
        }
      }
      dispatch(
        setAuditEvents(
          persistedItems.length
            ? persistedItems
            : [...pendingForRequest, savedEvent],
        ),
      )
      dispatch(clearPendingAuditEvents())
      return saved
    } catch (error) {
      const message = getApiErrorMessage(
        error,
        'The complaint could not be saved. Please try again.',
      )
      dispatch(setSaveStatus('error'))
      dispatch(setSaveError(message))
      return null
    } finally {
      savingRef.current = false
    }
  }, [
    complaint,
    dispatch,
    isProcessing,
    isSaved,
    pendingAuditEvents,
    riskAssessment,
    saveStatus,
  ])

  const resetWorkspace = useCallback(() => {
    dispatch(resetComplaintState())
    dispatch(resetCopilot())
  }, [dispatch])

  return {
    isProcessing,
    isSaved,
    resetWorkspace,
    saveCurrentComplaint,
    submitMessage,
    uploadDocument,
  }
}

export {
  actualComplaintChanges,
  applyAgentResponse,
  complaintHasFacts,
  createAuditEvent,
  deriveAuditEvents,
  extensionFor,
  valuesEqual,
}
