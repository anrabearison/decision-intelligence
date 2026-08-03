# Artifacts de documentation

Ce dossier contient des artefacts de documentation et de preuve pour le projet decision-core.

## run_output.txt

Fichier contenant la sortie de test manuelle sur les 19 fichiers CSV d'exemple situés dans `examples/`.

### Contenu
- Résultats d'analyse sur chaque fichier d'exemple
- Détails des corrélations, anomalies, simulations et warnings
- Preuve du comportement du moteur sur des données réelles

### Utilité
Ce fichier sert de documentation de référence pour :
- Valider le comportement du moteur sur les cas d'usage documentés dans `RAPPORT_TESTS_DOMAINES.md`
- Fournir des exemples concrets de sorties pour les développeurs
- Documenter les avertissements générés par le moteur

### Régénération
Ce fichier est une preuve figée et ne doit pas être régénéré automatiquement. Il peut être mis à jour manuellement lors de changements majeurs du moteur pour refléter le nouveau comportement.

Pour régénérer ce fichier si nécessaire :
```bash
# Exécuter le script de test manuel sur les 19 CSV d'exemple
# (script à documenter si disponible)
```
