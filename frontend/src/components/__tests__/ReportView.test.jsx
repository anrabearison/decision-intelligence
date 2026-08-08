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

describe('ReportView - exploitability et main_insight', () => {
  it('affiche le niveau, le score et le résumé quand exploitability est présent', () => {
    const report = {
      ...baseReport,
      exploitability: {
        level: 'orange',
        score: 40,
        summary: 'Interprétation prudente — plusieurs limites détectées, croiser avec l\'expertise métier.'
      },
    }
    render(<ReportView report={report} />)
    expect(screen.getByText('ORANGE')).toBeTruthy()
    expect(screen.getByText('40/100')).toBeTruthy()
    expect(screen.getByText(/Interprétation prudente/)).toBeTruthy()
  })

  it('ne plante pas quand exploitability est absent (compatibilité ascendante)', () => {
    const report = {
      ...baseReport,
      // exploitability non inclus
    }
    render(<ReportView report={report} />)
    // Le rapport s'affiche normalement sans crash
    expect(screen.getByText('40')).toBeTruthy()
    expect(screen.getByText('lignes')).toBeTruthy()
    expect(screen.queryByText('ORANGE')).toBeNull()
    expect(screen.queryByText('40/100')).toBeNull()
  })

  it('affiche main_insight quand présent', () => {
    const report = {
      ...baseReport,
      main_insight: 'La variable \'Produit\' explique 100% des écarts — bien plus que votre feature \'testée\'. Analysez séparément par \'Produit\' avant de simuler globalement.',
    }
    render(<ReportView report={report} />)
    expect(screen.getByText(/La variable 'Produit' explique 100%/)).toBeTruthy()
  })

  it('ne plante pas quand main_insight est absent ou null', () => {
    const report = {
      ...baseReport,
      main_insight: null,
    }
    render(<ReportView report={report} />)
    expect(screen.getByText('40')).toBeTruthy()
    expect(screen.getByText('lignes')).toBeTruthy()
    // Le champ insight ne s'affiche pas si null
    expect(screen.queryByText(/La variable 'Produit'/)).toBeNull()
  })

  it('ne plante pas quand main_insight est absent du rapport', () => {
    const report = {
      ...baseReport,
      // main_insight non inclus
    }
    render(<ReportView report={report} />)
    expect(screen.getByText('40')).toBeTruthy()
    expect(screen.getByText('lignes')).toBeTruthy()
  })
})

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

  it('affiche les simulations logistiques en points de pourcentage', () => {
    const report = {
      ...baseReport,
      simulation: {
        feature: 'Tickets_Support',
        baseline: 0.0666,
        simulated: 0.7389,
        change_pct: null,
        change_pct_reliable: false,
        change_percentage_points: 67.23,
        model_type: 'logistic',
        model_r_squared: 0.81,
      },
    }
    render(<ReportView report={report} />)
    expect(screen.getByText('6.7%')).toBeTruthy()
    expect(screen.getByText('73.9%')).toBeTruthy()
    expect(screen.getByText('+67.2 pts')).toBeTruthy()
    expect(screen.queryByText('% non fiable')).toBeNull()
    expect(screen.getByText(/régression logistique/)).toBeTruthy()
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
