import { useEffect, useState } from "react";
import { ArrowRight, RefreshCw } from "lucide-react";

export default function Prediction({ ask }) {
  const [values, setValues] = useState({
    recency: "",
    frequency: "",
    monetary: "",
  });
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
        setInfo(await r.json());
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
          Object.fromEntries(
            Object.entries(values).map(([k, v]) => [k, Number(v)]),
          ),
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
            <button className="primary" disabled={busy}>
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
              <p>{result.notice}</p>
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
