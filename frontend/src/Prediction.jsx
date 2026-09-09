import { useEffect, useState } from "react";
import { ArrowRight, RefreshCw } from "lucide-react";

export default function Prediction({ ask }) {
  const [values, setValues] = useState({
    recency: "",
    frequency: "",
    monetary: "",
  });
  const [period, setPeriod] = useState({ observation_start:'', observation_end:'', reference_date:'', mode:'historical' });
  const [info, setInfo] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/model-info", { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok)
          throw Error(
            "Le modèle est indisponible. Vérifiez son export et le démarrage de l’API.",
          );
        const model = await r.json();
        setInfo(model);
        setPeriod({ observation_start: model.training.window_start.slice(0,10), observation_end: model.training.window_end.slice(0,10), reference_date: model.training.reference_date.slice(0,10), mode:'historical' });
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, []);
  async function submit(e) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          { ...Object.fromEntries(Object.entries(values).map(([k,v]) => [k,Number(v)])), ...period },
        ),
        signal: AbortSignal.timeout(20000),
      });
      const data = await response.json();
      if (!response.ok)
        throw Error(data.error || "Le classement est indisponible.");
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <h2>Quel segment correspond à ce client ?</h2>
      <p className="subtitle">
        Renseignez ses trois indicateurs RFM pour appliquer le modèle entraîné.
      </p>
      <div className="split">
        <section className="card">
          <h3>Informations d’achat</h3>
          <p>
            Utilisez les achats positifs sur une même période d’observation.
            Aucun nom ni identifiant personnel n’est nécessaire.
          </p>
          <form className="prediction-form" onSubmit={submit}>
            <label>Cadre de classement<select aria-label="Cadre de classement" value={period.mode} disabled={busy || !info} onChange={e => {
              const mode=e.target.value;
              setPeriod(p=> mode==='historical' ? {mode,observation_start:info.training.window_start.slice(0,10),observation_end:info.training.window_end.slice(0,10),reference_date:info.training.reference_date.slice(0,10)} : {...p,mode}); setResult(null);
            }}><option value="historical">Période historique du modèle</option><option value="simulation">Simulation sur une autre période</option></select></label>
            {period.mode==='simulation' && <p className="notice">Simulation exploratoire : une autre durée ou saison peut changer le sens du classement. Les montants et fréquences ne sont pas annualisés. La pertinence hors période n'est pas validée.</p>}
            {[['observation_start','Début des achats observés'],['observation_end','Fin des achats observés'],['reference_date','Date de calcul de la récence']].map(([key,label]) => <label key={key}><strong>{label}</strong><input type="date" aria-label={label} required value={period[key]} readOnly={period.mode==='historical'} disabled={busy || !info} onChange={e=>{setPeriod(p=>({...p,[key]:e.target.value}));setResult(null);}}/></label>)}
            <p className="source">La date de référence suit la fin de la fenêtre. La récence doit placer le dernier achat dans cette fenêtre. La fréquence et le montant couvrent toute la fenêtre déclarée.</p>
            {[
              [
                "recency",
                "Récence (jours)",
                "Jours écoulés depuis le dernier achat valide à la date de référence.",
                0,
                1,
                1000000,
              ],
              [
                "frequency",
                "Fréquence (factures)",
                "Nombre de factures distinctes sur toute la période.",
                1,
                1,
                1000000000,
              ],
              [
                "monetary",
                "Montant des achats (£)",
                "Total des achats positifs en livres sterling, sans déduire les retours.",
                0.01,
                "any",
                1e15,
              ],
            ].map(([name, label, help, min, step, max]) => (
              <label key={name} htmlFor={name}>
                <strong>{label}</strong>
                <small id={name + "-help"}>{help}</small>
                <input
                  id={name}
                  aria-describedby={name + "-help"}
                  type="number"
                  min={min}
                  max={max}
                  step={step}
                  required
                  value={values[name]}
                  disabled={busy}
                  onChange={(e) => {
                    setValues((v) => ({ ...v, [name]: e.target.value }));
                    setResult(null);
                  }}
                />
              </label>
            ))}
            <button className="primary" disabled={busy || !info}>
              {busy ? (
                <RefreshCw size={16} className="spin" />
              ) : (
                <ArrowRight size={16} />
              )}{" "}
              {busy ? "Classement en cours…" : "Déterminer le segment"}
            </button>
          </form>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
        </section>
        <section className="card" aria-live="polite">
          {result ? (
            <>
              <span className="eyebrow">SEGMENT ATTRIBUÉ</span>
              <h2 style={{ marginTop: 20 }}>{result.segment}</h2>
              <p>{result.segment_definition}</p>
              <p>
                {result.recommendation || "Aucune recommandation disponible."}
              </p>
              {result.capped_features.length > 0 && (
                <p className="notice">
                  Valeurs plafonnées au seuil appris :{" "}
                  {result.capped_features
                    .map(
                      (k) =>
                        ({
                          Recency: "récence",
                          Frequency: "fréquence",
                          Monetary: "montant",
                        })[k],
                    )
                    .join(", ")}
                  . Les valeurs extrêmes sont traitées comme à l’entraînement.
                </p>
              )}
              <p className={result.temporal_context.matches_training ? '' : 'notice'}>{result.notice}</p>
              <p className="source">Période saisie : {result.temporal_context.observation_start} au {result.temporal_context.observation_end} ({result.temporal_context.observation_days} jours). Référence : {result.temporal_context.reference_date}. Mode : {result.temporal_context.mode==='simulation'?'simulation':'historique'}.</p>
              <button
                onClick={() =>
                  ask(
                    `Quelles actions sont documentées pour le segment ${result.segment} ?`,
                  )
                }
              >
                Explorer les actions du segment <ArrowRight size={16} />
              </button>
              <p className="source">
                Modèle : {result.model_id} · {result.k} groupes. Cette
                simulation n’ajoute pas de client aux données.
              </p>
            </>
          ) : (
            <>
              <span className="eyebrow">
                UNE AFFECTATION, PAS UNE PRÉVISION
              </span>
              <h3 style={{ marginTop: 20 }}>Le profil le plus proche</h3>
              <p>
                Le modèle compare le profil saisi aux groupes appris, après
                plafonnement, transformation logarithmique et standardisation.
              </p>
              <p>
                Ce classement n’est ni un score de solvabilité ni une
                probabilité de succès commercial. Il doit être interprété dans
                le contexte des achats observés.
              </p>
            </>
          )}
          {info && (
            <div className="note">
              <span>
                Référence : {info.training.reference_date.slice(0, 10)}.
                Entraînement du {info.training.window_start.slice(0, 10)} au{" "}
                {info.training.window_end.slice(0, 10)}, sur{" "}
                {info.training.clients} clients. Des achats actuels ou une
                fenêtre plus courte constituent une simulation hors du contexte
                historique ; leur pertinence doit être évaluée.
              </span>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
