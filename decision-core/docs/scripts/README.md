# Scripts d'investigation et validation

Ce dossier contient des scripts manuels pour l'investigation et la validation du projet.

## test_all_examples.py

Script de validation inter-domaines qui analyse tous les fichiers examples/ et génère des rapports pour chacun d'eux.

### Usage

```bash
cd decision-core
python docs/scripts/test_all_examples.py
```

### Ce que ça produit

Analyse les 18 fichiers examples/*.csv et affiche pour chacun :
- Dimensions du dataset
- Colonnes détectées
- Rapport d'analyse complet (statistiques, corrélations, anomalies, sous-groupes)
- Score d'exploitabilité (green/orange/red)
- Warnings détectés

### Sortie

Résumé global avec :
- Nombre d'analyses réussies
- Score moyen d'exploitabilité
- Répartition par niveau (green/orange/red)
