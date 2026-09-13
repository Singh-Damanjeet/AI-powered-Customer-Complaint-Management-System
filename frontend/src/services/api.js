import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  headers: {
    Accept: 'application/json',
  },
})

export const SUPPORTED_DOCUMENT_EXTENSIONS = ['pdf', 'docx', 'txt', 'eml']
export const MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024

export async function sendAgentMessage(message, complaint = null) {
  const response = await apiClient.post('/agent/message', {
    message,
    complaint,
  })
  return response.data
}

export async function uploadComplaintDocument(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post('/agent/document', formData, {
    // Let the browser add the multipart boundary instead of sending JSON.
    headers: { 'Content-Type': undefined },
  })
  return response.data
}

export async function saveComplaint(payload) {
  const response = await apiClient.post('/complaints', payload)
  return response.data
}

export function getApiErrorMessage(error, fallback = 'Unable to reach the server.') {
  if (!error?.response) {
    if (error?.request) {
      return 'Unable to reach the server. Your current complaint data has been preserved.'
    }
    return fallback
  }

  const { status, data } = error.response
  const detail = typeof data?.detail === 'string' ? data.detail : ''

  if (status === 413) {
    return 'This document is too large. Please choose a file under 10 MB.'
  }
  if (status === 415) {
    return 'This file type is not supported. Use PDF, DOCX, TXT, or EML.'
  }
  if (status === 422 && detail) {
    return detail
  }
  if (status === 502 || status === 503) {
    return 'AI service is temporarily unavailable. Your current complaint data has been preserved.'
  }
  if (status >= 500) {
    return 'The server could not process that request. Your current complaint data has been preserved.'
  }
  return detail || fallback
}
