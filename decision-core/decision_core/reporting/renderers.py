"""
Fonctions de rendu pour decision-core (texte et HTML).
"""
import html
from decision_core.models import ReportResult


def render_text_summary(report: ReportResult) -> str:
    """Génère un résumé textuel lisible du rapport.

    Args:
        report: ReportResult typé issu de generate_report.

    Returns:
        Résumé texte multi-lignes.
    """
    lines = []
    ds = report.dataset_summary
    lines.append(f"📊 Résumé du dataset : {ds.n_rows} lignes, {ds.n_columns} colonnes.")

    # P1-5 : insight principal en tête
    if getattr(report, "main_insight", None):
        lines.append(f"💡 Conclusion principale : {report.main_insight}")

    # Disclaimer systématique sur la causalité
    lines.append("⚠️ AVERTISSEMENT : Corrélation ≠ Causalité. Les résultats présentés "
                 "ne doivent pas être interprétés comme des relations de cause à effet.")

    if report.validation["duplicates_count"] > 0:
        lines.append(f"⚠️ {report.validation['duplicates_count']} doublon(s) détecté(s).")

    if report.top_correlations:
        top = report.top_correlations[0]
        lines.append(
            f"🔎 Corrélation la plus forte : {top['column_a']} ↔ {top['column_b']} "
            f"({top['value']:.2f})."
        )

    if report.simulation is not None:
        sim = report.simulation
        # P0-2 : indiquer si simulation non actionnable
        actionable_suffix = ""
        if sim.get("actionable") is False:
            actionable_suffix = " — calcul indicatif uniquement, non actionnable"
        if sim.get("change_percentage_points") is not None:
            lines.append(
                f"💡 Simulation sur '{sim['feature']}' : "
                f"{sim['baseline']:.1%} → {sim['simulated']:.1%} "
                f"({sim['change_percentage_points']:+.1f} points){actionable_suffix}."
            )
        elif sim.get("change_pct_reliable", True):
            lines.append(
                f"💡 Simulation sur '{sim['feature']}' : "
                f"{sim['baseline']:.1f} → {sim['simulated']:.1f} "
                f"({sim['change_pct']:+.1f}%){actionable_suffix}."
            )
        else:
            lines.append(
                f"💡 Simulation sur '{sim['feature']}' : "
                f"{sim['baseline']:.2f} → {sim['simulated']:.2f}{actionable_suffix}. "
                f"Variation en % non fiable ici (valeur de référence trop "
                f"proche de zéro) - se fier aux valeurs absolues plutôt "
                f"qu'au pourcentage."
            )
        if sim.get("actionable") is False and sim.get("non_actionable_reason"):
            lines.append(f"⚠️ {sim['non_actionable_reason']}")

    for w in report.warnings:
        lines.append(f"⚠️ {w}")

    return "\n".join(lines)


def render_html(report: ReportResult) -> str:
    """Génère un rapport HTML à partir du ReportResult.

    Args:
        report: ReportResult typé issu de generate_report.

    Returns:
        Document HTML complet.
    """
    ds = report.dataset_summary
    # Échappement systématique de toute donnée dérivée du fichier importé
    # (noms de colonnes notamment) - ces valeurs viennent d'un upload
    # utilisateur non fiable et ne doivent jamais être injectées telles
    # quelles dans du HTML (risque XSS, cf. commit). Le JSON retourné par
    # l'API n'est lui jamais échappé : c'est React qui échappe déjà côté
    # frontend, échapper ici aussi produirait un double échappement.
    text_summary = html.escape(render_text_summary(report)).replace("\n", "<br>")

    correlations_rows = "".join(
        f"<tr><td>{html.escape(str(c['column_a']))}</td>"
        f"<td>{html.escape(str(c['column_b']))}</td>"
        f"<td>{c['value']:.3f}</td></tr>"
        for c in report.top_correlations
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Rapport Decision Core</title></head>
<body>
<h1>Rapport d'analyse</h1>
<p>{ds.n_rows} lignes, {ds.n_columns} colonnes.</p>
<div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 10px; margin: 10px 0;">
<strong>⚠️ AVERTISSEMENT IMPORTANT :</strong> Corrélation ≠ Causalité. Les résultats présentés ne doivent pas être interprétés comme des relations de cause à effet.
</div>
<h2>Synthèse</h2>
<p>{text_summary}</p>
<h2>Corrélations principales</h2>
<table border="1">
<tr><th>Variable A</th><th>Variable B</th><th>Corrélation</th></tr>
{correlations_rows}
</table>
</body>
</html>"""
