const API_URL = import.meta.env.VITE_API_URL;

const handleResponse = async (response) => {
  const json = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(json.message || response.statusText || 'API request failed')
  }
  return json
}

// Normalise analysis response — ensures new fields always exist with safe defaults
// so pages written before the backend upgrade never crash on missing keys.
export const normalizeAnalysis = (data = {}) => ({
  ...data,
  agent_trace:        data.agent_trace        ?? [],
  interpretation:     data.interpretation     ?? null,
  emergency_alert:    data.emergency_alert     ?? false,
  knowledge_sources:  data.knowledge_sources  ?? [],
  relevant_knowledge: data.relevant_knowledge ?? [],
  follow_up_questions: data.follow_up_questions ?? [],
})

export const normalizeFinalAssessment = (data = {}) => ({
  ...data,
  agent_trace:       data.agent_trace       ?? [],
  diagnosis_result:  data.diagnosis_result  ?? null,
  knowledge_sources: data.knowledge_sources ?? [],
})

export const analyzeSymptoms = async (payload) => {
  const response = await fetch(`${API_URL}/analyze-symptoms`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return normalizeAnalysis(await handleResponse(response))
}

export const finalAssessment = async (payload) => {
  const response = await fetch(`${API_URL}/final-assessment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return normalizeFinalAssessment(await handleResponse(response))
}

export const saveReport = async (payload) => {
  const response = await fetch(`${API_URL}/save-report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return handleResponse(response)
}

export const getHistory = async () => {
  const response = await fetch(`${API_URL}/history`)
  return handleResponse(response)
}

export const shareReport = async (report, form) => {
  const response = await fetch(`${API_URL}/share-report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report, form }),
  })
  return handleResponse(response)
}

export const getSharedReport = async (token) => {
  const response = await fetch(`${API_URL}/shared/${token}`)
  return handleResponse(response)
}
