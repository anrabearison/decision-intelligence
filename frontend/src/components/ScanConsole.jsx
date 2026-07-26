import { useEffect, useState } from 'react'

const SCAN_STEPS = [
  'Lecture du fichier…',
  'Détection des types de colonnes…',
  'Calcul des statistiques descriptives…',
  'Recherche de corrélations…',
  'Assemblage du rapport…',
]

export default function ScanConsole({ fileName }) {
  const [stepIndex, setStepIndex] = useState(0)
  const [counter, setCounter] = useState(0)

  useEffect(() => {
    const stepInterval = setInterval(() => {
      setStepIndex((i) => Math.min(i + 1, SCAN_STEPS.length - 1))
    }, 550)
    const counterInterval = setInterval(() => {
      setCounter((c) => c + Math.floor(Math.random() * 340) + 40)
    }, 60)
    return () => {
      clearInterval(stepInterval)
      clearInterval(counterInterval)
    }
  }, [])

  return (
    <div className="scan-console">
      <div className="scan-console__header">
        <span className="scan-console__dot" />
        <span className="mono scan-console__file">{fileName}</span>
      </div>
      <div className="scan-console__counter mono">
        {counter.toLocaleString('fr-FR')} <span className="scan-console__counter-label">valeurs lues</span>
      </div>
      <ul className="scan-console__steps">
        {SCAN_STEPS.map((step, i) => (
          <li key={step} className={i <= stepIndex ? 'is-active' : ''}>
            <span className="scan-console__marker mono">{i < stepIndex ? '✓' : i === stepIndex ? '›' : '·'}</span>
            {step}
          </li>
        ))}
      </ul>
    </div>
  )
}
