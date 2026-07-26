import { useState } from 'react'
import UploadZone from './components/UploadZone.jsx'
import ScanConsole from './components/ScanConsole.jsx'
import ReportView from './components/ReportView.jsx'
import { analyzeDataset, ApiError } from './api/client.js'

export default function App() {
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('idle') // idle | scanning | done | error
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const [simEnabled, setSimEnabled] = useState(false)
  const [target, setTarget] = useState('')
  const [feature, setFeature] = useState('')
  const [changePct, setChangePct] = useState('5')

  const runAnalysis = async (selectedFile) => {
    setFile(selectedFile)
    setStatus('scanning')
    setError(null)
    try {
      const simConfig = simEnabled && target && feature
        ? { target, feature, changePct: parseFloat(changePct) / 100 }
        : null
      const result = await analyzeDataset(selectedFile, simConfig)
      setReport(result)
      setStatus('done')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Impossible de contacter le moteur d\'analyse.')
      setStatus('error')
    }
  }

  const reset = () => {
    setFile(null)
    setStatus('idle')
    setReport(null)
    setError(null)
  }

  return (
    <div className="app">
      <header className="app__header">
        <span className="app__logo mono">decision<span className="app__logo-accent">·</span>studio</span>
        <span className="app__tag mono">Phase 2 — decision-engine</span>
      </header>

      <main className="app__main">
        {status === 'idle' && (
          <>
            <div className="app__intro">
              <h1>Déposez vos données.<br /><span className="app__intro-accent">Obtenez une lecture rigoureuse.</span></h1>
              <p className="app__intro-sub">
                Import, validation, statistiques, corrélations et simulation —
                calculés, pas devinés.
              </p>
            </div>
            <UploadZone onFileSelected={runAnalysis} />

            <details className="sim-config" onToggle={(e) => setSimEnabled(e.target.open)}>
              <summary className="mono">+ Configurer une simulation (facultatif)</summary>
              <div className="sim-config__fields">
                <label>
                  <span>Colonne cible</span>
                  <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="ex: Ventes" />
                </label>
                <label>
                  <span>Variable modifiée</span>
                  <input value={feature} onChange={(e) => setFeature(e.target.value)} placeholder="ex: Prix" />
                </label>
                <label>
                  <span>Variation (%)</span>
                  <input value={changePct} onChange={(e) => setChangePct(e.target.value)} type="number" />
                </label>
              </div>
            </details>
          </>
        )}

        {status === 'scanning' && <ScanConsole fileName={file?.name} />}

        {status === 'error' && (
          <div className="app__error">
            <p>{error}</p>
            <button className="btn" onClick={reset}>Réessayer</button>
          </div>
        )}

        {status === 'done' && report && (
          <>
            <div className="app__result-header">
              <span className="mono">{file?.name}</span>
              <button className="btn btn--ghost" onClick={reset}>Nouvelle analyse</button>
            </div>
            <ReportView report={report} />
          </>
        )}
      </main>
    </div>
  )
}
