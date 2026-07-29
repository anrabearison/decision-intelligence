import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ReportView from '../ReportView.jsx'

const baseReport = {
  dataset_summary: { n_rows: 40, n_columns: 3 },
  validation: { duplicates_count: 0 },
  warnings: [],
  top_correlations: [],
  simulation: null,
}

describe('ReportView - simulation change_pct null (régression connue)', () => {
  it('ne plante pas quand change_pct_reliable est false et change_pct est null', () => {
    const report = {
      ...baseReport,
      simulation: {
        feature: 'X',
        baseline: 0.05,
        simulated: -0.06,
        change_pct: null,
        change_pct_reliable: false,
        model_r_squared: 0.02,
      },
    }
    render(<ReportView report={report} />)
    expect(screen.getByText('% non fiable')).toBeTruthy()
    expect(screen.getByText(/Variation en % non fiable ici/)).toBeTruthy()
  })

  it('affiche normalement le pourcentage quand change_pct_reliable est true', () => {
    const report = {
      ...baseReport,
      simulation: {
        feature: 'Prix',
        baseline: 67.3,
        simulated: 65.1,
        change_pct: -3.2,
        change_pct_reliable: true,
        model_r_squared: 0.79,
      },
    }
    render(<ReportView report={report} />)
    expect(screen.getByText('-3.2%')).toBeTruthy()
  })
})

describe('ReportView - significativité statistique des corrélations (régression connue)', () => {
  it('affiche un indicateur "non significatif" quand significant_after_correction est false', () => {
    const report = {
      ...baseReport,
      top_correlations: [
        { column_a: 'A', column_b: 'B', value: 0.6, significant_after_correction: false },
      ],
    }
    render(<ReportView report={report} />)
    expect(screen.getByText('non significatif')).toBeTruthy()
  })

  it("n'affiche pas l'indicateur quand la corrélation est significative", () => {
    const report = {
      ...baseReport,
      top_correlations: [
        { column_a: 'A', column_b: 'B', value: 0.9, significant_after_correction: true },
      ],
    }
    render(<ReportView report={report} />)
    expect(screen.queryByText('non significatif')).toBeNull()
  })

  it('traite une corrélation sans le champ (compatibilité) comme significative par défaut', () => {
    const report = {
      ...baseReport,
      top_correlations: [{ column_a: 'A', column_b: 'B', value: 0.9 }],
    }
    render(<ReportView report={report} />)
    expect(screen.queryByText('non significatif')).toBeNull()
  })
})
