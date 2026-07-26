const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export async function analyzeDataset(file, simulationConfig) {
  const formData = new FormData()
  formData.append('file', file)
  if (simulationConfig) {
    formData.append('target', simulationConfig.target)
    formData.append('feature', simulationConfig.feature)
    formData.append('change_pct', simulationConfig.changePct)
  }

  const res = await fetch(`${API_URL}/engine/analyze`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(body.detail || 'Erreur inconnue lors de l\'analyse.', res.status)
  }

  return res.json()
}
