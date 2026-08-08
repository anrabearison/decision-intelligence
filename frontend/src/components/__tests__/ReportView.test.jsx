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

describe('ReportView - warnings structurés', () => {
  it('affiche les warnings structurés avec severity, code et recommendation', () => {
    const report = {
      ...baseReport,
      warnings_structured: [
        {
          severity: 'high',
          code: 'DETERMINISTIC',
          message: 'Relation déterministe détectée',
          recommendation: 'Analysez séparément par catégorie'
        }
      ],
      warnings: [],
    }
    render(<ReportView report={report} />)
    expect(screen.getByText('high')).toBeTruthy()
    expect(screen.getByText('DETERMINISTIC')).toBeTruthy()
    expect(screen.getByText((content) => content.includes('Relation déterministe détectée'))).toBeTruthy()
    expect(screen.getByText((content) => content.includes('Analysez séparément par catégorie'))).toBeTruthy()
  })

  it('ne plante pas quand warnings_structured est absent', () => {
    const report = {
      ...baseReport,
      warnings: ['Ancien warning string'],
      // warnings_structured non inclus
    }
    render(<ReportView report={report} />)
    expect(screen.getByText((content) => content.includes('Ancien warning string'))).toBeTruthy()
  })

  it('affiche les warnings string en complément des warnings structurés', () => {
    const report = {
      ...baseReport,
      warnings_structured: [
        {
          severity: 'high',
          code: 'DETERMINISTIC',
          message: 'Relation déterministe détectée',
        }
      ],
      warnings: ['Warning string non dupliqué'],
    }
    render(<ReportView report={report} />)
    expect(screen.getByText('DETERMINISTIC')).toBeTruthy()
    expect(screen.getByText((content) => content.includes('Warning string non dupliqué'))).toBeTruthy()
  })
})

describe('ReportView - simulation étendue', () => {
  it('affiche le badge Non actionnable quand simulation.actionable est false', () => {
    const report = {
      ...baseReport,
      simulation: {
        feature: 'Prix',
        target: 'Ventes',
        baseline: 100,
        simulated: 90,
        change_pct: -10,
        change_pct_reliable: true,
        actionable: false,
        non_actionable_reason: 'Données insuffisantes',
        model_r_squared: 0.8,
      },
    }
    render(<ReportView report={report} />)
    expect(screen.getByText('Non actionnable')).toBeTruthy()
    expect(screen.getByText((content) => content.includes('Données insuffisantes'))).toBeTruthy()
  })

  it('affiche lintervalle de prédiction quand présent', () => {
    const report = {
      ...baseReport,
      simulation: {
        feature: 'Prix',
        target: 'Ventes',
        baseline: 100,
        simulated: 90,
        change_pct: -10,
        change_pct_reliable: true,
        prediction_interval: {
          lower: 85,
          upper: 95,
          confidence: 0.8,
        },
        model_r_squared: 0.8,
      },
    }
    render(<ReportView report={report} />)
    expect(screen.getByText((content) => content.includes('Intervalle 80%'))).toBeTruthy()
    expect(screen.getByText((content) => content.includes('85'))).toBeTruthy()
    expect(screen.getByText((content) => content.includes('95'))).toBeTruthy()
  })

  it('affiche les métriques de cross-validation quand présentes', () => {
    const report = {
      ...baseReport,
      simulation: {
        feature: 'Prix',
        target: 'Ventes',
        baseline: 100,
        simulated: 90,
        change_pct: -10,
        change_pct_reliable: true,
        cross_validation: {
          cv_r2_mean: 0.75,
          mae: 5.2,
          rmse: 7.8,
        },
        model_r_squared: 0.8,
      },
    }
    render(<ReportView report={report} />)
    expect(screen.getByText((content) => content.includes('Validation croisée 5-fold'))).toBeTruthy()
    expect(screen.getByText((content) => content.includes('0.75'))).toBeTruthy()
    expect(screen.getByText((content) => content.includes('5.2'))).toBeTruthy()
    expect(screen.getByText((content) => content.includes('7.8'))).toBeTruthy()
  })

  it('affiche le warning quand bounds_applied est true', () => {
    const report = {
      ...baseReport,
      simulation: {
        feature: 'Prix',
        target: 'Ventes',
        baseline: 100,
        simulated: 90,
        change_pct: -10,
        change_pct_reliable: true,
        bounds_applied: true,
        model_r_squared: 0.8,
      },
    }
    render(<ReportView report={report} />)
    expect(screen.getByText((content) => content.includes('Résultat borné par les limites physiques'))).toBeTruthy()
  })
})
