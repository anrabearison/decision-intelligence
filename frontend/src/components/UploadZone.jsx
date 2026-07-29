import { useCallback, useRef, useState } from 'react'

// Reflète MAX_FILE_SIZE_MB côté decision-engine (main.py) - vérifier
// côté client évite d'uploader inutilement un fichier qui sera de
// toute façon rejeté par le serveur (trouvé en revue de code : le
// texte "max 50 Mo" était affiché mais jamais vérifié avant l'envoi).
const MAX_FILE_SIZE_MB = 50
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

export default function UploadZone({ onFileSelected, onError, disabled }) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef(null)

  const validateAndSelect = useCallback((file) => {
    if (file.size > MAX_FILE_SIZE_BYTES) {
      onError?.(`Fichier trop volumineux (${(file.size / (1024 * 1024)).toFixed(1)} Mo) — maximum ${MAX_FILE_SIZE_MB} Mo.`)
      return
    }
    onFileSelected(file)
  }, [onFileSelected, onError])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) validateAndSelect(file)
  }, [validateAndSelect])

  const handleChange = (e) => {
    const file = e.target.files?.[0]
    if (file) validateAndSelect(file)
  }

  return (
    <div
      className={`upload-zone ${isDragging ? 'is-dragging' : ''} ${disabled ? 'is-disabled' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        onChange={handleChange}
        disabled={disabled}
        hidden
      />
      <div className="upload-zone__icon" aria-hidden="true">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <path d="M12 3v12m0-12l-4 4m4-4l4 4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"
                stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <p className="upload-zone__label">Glissez un fichier CSV ou Excel</p>
      <p className="upload-zone__sub mono">ou cliquez pour parcourir — max 50 Mo</p>
    </div>
  )
}
