import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import UploadZone from '../UploadZone.jsx'

function makeFile(sizeInBytes, name = 'data.csv') {
  const file = new File(['x'], name, { type: 'text/csv' })
  Object.defineProperty(file, 'size', { value: sizeInBytes })
  return file
}

describe('UploadZone - validation de taille (régression connue)', () => {
  it('appelle onError et jamais onFileSelected pour un fichier > 50 Mo', () => {
    const onFileSelected = vi.fn()
    const onError = vi.fn()
    const { container } = render(
      <UploadZone onFileSelected={onFileSelected} onError={onError} />
    )
    const input = container.querySelector('input[type="file"]')
    const bigFile = makeFile(60 * 1024 * 1024)

    fireEvent.change(input, { target: { files: [bigFile] } })

    expect(onError).toHaveBeenCalledOnce()
    expect(onFileSelected).not.toHaveBeenCalled()
    expect(onError.mock.calls[0][0]).toContain('50 Mo')
  })

  it('appelle onFileSelected pour un fichier sous la limite', () => {
    const onFileSelected = vi.fn()
    const onError = vi.fn()
    const { container } = render(
      <UploadZone onFileSelected={onFileSelected} onError={onError} />
    )
    const input = container.querySelector('input[type="file"]')
    const okFile = makeFile(2 * 1024 * 1024)

    fireEvent.change(input, { target: { files: [okFile] } })

    expect(onFileSelected).toHaveBeenCalledOnce()
    expect(onError).not.toHaveBeenCalled()
  })
})
