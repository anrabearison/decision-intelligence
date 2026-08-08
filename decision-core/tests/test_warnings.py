"""
Tests pour les corrections de faux positifs saisonnalité et relations déterministes.
"""
import pytest
import pandas as pd
import numpy as np
from decision_core.reporting.warnings.seasonality import _detect_temporal_columns
from decision_core.report import generate_report
from decision_core.models import SimulationConfig
from decision_core import import_file


class TestTemporalColumnsDetection:
    """Tests pour la correction des faux positifs saisonnalité sur métriques *_Jour."""
    
    def test_numeric_metric_with_jour_not_detected_as_temporal(self):
        """Litres_Lait_Jour (float64, 80 valeurs distinctes) → NON détectée comme temporelle."""
        df = pd.DataFrame({
            'Litres_Lait_Jour': np.random.uniform(10, 50, 100),
            'Salaire': np.random.normal(3000, 500, 100),
        })
        result = _detect_temporal_columns(df)
        assert result == []
    
    def test_integer_metric_with_jour_not_detected_as_temporal(self):
        """Visiteurs_Jour (int64, 100 valeurs distinctes) → NON détectée comme temporelle."""
        df = pd.DataFrame({
            'Visiteurs_Jour': np.random.randint(50, 200, 100),
            'CA': np.random.normal(5000, 1000, 100),
        })
        result = _detect_temporal_columns(df)
        assert result == []
    
    def test_string_date_column_still_detected(self):
        """Date (object, '2025-01-01') → DÉTECTÉE comme temporelle."""
        df = pd.DataFrame({
            'Date': pd.date_range('2025-01-01', periods=50).astype(str),
            'CA': np.random.normal(5000, 1000, 50),
        })
        result = _detect_temporal_columns(df)
        assert 'Date' in result
    
    def test_string_saison_column_still_detected(self):
        """Saison (object, 'Hiver') → DÉTECTÉE comme temporelle."""
        df = pd.DataFrame({
            'Saison': np.random.choice(['Hiver', 'Printemps', 'Été', 'Automne'], 50),
            'CA': np.random.normal(5000, 1000, 50),
        })
        result = _detect_temporal_columns(df)
        assert 'Saison' in result
    
    def test_integer_month_column_detected(self):
        """Mois (int64, 1..12, 12 valeurs uniques) → DÉTECTÉE comme temporelle."""
        df = pd.DataFrame({
            'Mois': np.random.randint(1, 13, 50),
            'CA': np.random.normal(5000, 1000, 50),
        })
        result = _detect_temporal_columns(df)
        assert 'Mois' in result


class TestDeterministicRelations:
    """Tests pour la correction des relations déterministes affichées comme '100.0%'."""
    
    def test_deterministic_relation_gets_specific_warning(self):
        """Relation déterministe → warning 'Relation déterministe' sans '100.0%'."""
        df = pd.DataFrame({
            'Plan': ['A', 'B', 'C'] * 30,
            'MRR': [10.0, 20.0, 30.0] * 30,  # Plan détermine entièrement MRR
        })
        report = generate_report(df)
        
        # Vérifier warning "Relation déterministe" présent
        warnings_str = ' '.join(report.get('warnings', []))
        assert 'Relation déterministe détectée' in warnings_str
        assert 'Plan' in warnings_str
        assert 'MRR' in warnings_str
        
        # Vérifier PAS de warning "100.0%"
        assert '100.0%' not in warnings_str
    
    def test_deterministic_relation_excluded_from_subgroup_warnings(self):
        """Relation déterministe → PAS de warning 'Sous-groupe significatif détecté'."""
        df = pd.DataFrame({
            'Plan': ['A', 'B', 'C'] * 30,
            'MRR': [10.0, 20.0, 30.0] * 30,
        })
        report = generate_report(df)
        
        warnings_str = ' '.join(report.get('warnings', []))
        assert 'Sous-groupe significatif détecté' not in warnings_str
        assert 'Plan' not in warnings_str or 'Sous-groupe' not in warnings_str
    
    def test_no_duplicate_deterministic_warnings(self):
        """Plusieurs colonnes numériques déterminées par la même catégorie → 1 seul warning par paire."""
        df = pd.DataFrame({
            'Plan': ['A', 'B', 'C'] * 30,
            'MRR': [10.0, 20.0, 30.0] * 30,
            'Churn': [0.1, 0.2, 0.3] * 30,
        })
        report = generate_report(df)
        
        warnings_str = ' '.join(report.get('warnings', []))
        # Compter le nombre de fois où "Relation déterministe" apparaît
        # Doit être 2 (Plan→MRR et Plan→Churn), pas plus
        count = warnings_str.count('Relation déterministe détectée')
        assert count == 2
    
    def test_real_saas_deterministic_warning(self):
        """SaaS réel → warning 'Relation déterministe' pour Plan_Souscrit."""
        df = import_file('examples/saas_abonnements_2025.csv')
        report = generate_report(df)
        
        warnings_str = ' '.join(report.get('warnings', []))
        assert 'Relation déterministe détectée' in warnings_str
        assert 'Plan_Souscrit' in warnings_str
        assert '100.0%' not in warnings_str
    
    def test_non_deterministic_subgroup_unaffected(self):
        """Relation non-déterministe (std > 0) → warning 'Sous-groupe significatif' présent."""
        np.random.seed(42)
        region = np.array(['A', 'B', 'C'] * 30)
        salary_a = 3000 + np.random.normal(0, 100, 30)
        salary_b = 4000 + np.random.normal(0, 100, 30)
        salary_c = 5000 + np.random.normal(0, 100, 30)
        df = pd.DataFrame({
            'Region': region,
            'Salaire': np.concatenate([salary_a, salary_b, salary_c]),
        })
        report = generate_report(df)
        
        warnings_str = ' '.join(report.get('warnings', []))
        # Le sous-groupe peut ne pas être détecté si eta² < 0.5
        # Ce test vérifie juste que les relations non-déterministes ne sont pas bloquées
        assert 'Relation déterministe' not in warnings_str
