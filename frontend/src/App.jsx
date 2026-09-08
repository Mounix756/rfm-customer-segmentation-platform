import { useEffect, useRef, useState } from "react";
import Prediction from "./Prediction.jsx";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  LayoutDashboard,
  Users,
  ChartNoAxesCombined,
  MessageSquare,
  ArrowUpRight,
  ArrowRight,
  Download,
  RefreshCw,
  Search,
  Send,
  Plus,
  Layers,
  CircleHelp,
} from "lucide-react";

const number = (v, digits = 0) =>
  v == null
    ? "Non disponible"
    : new Intl.NumberFormat("fr-FR", { maximumFractionDigits: digits }).format(
        v,
      );
const money = (v) =>
  v == null
    ? "Non disponible"
    : new Intl.NumberFormat("fr-FR", {
        style: "currency",
        currency: "GBP",
        currencyDisplay: "narrowSymbol",
        notation: Math.abs(v) >= 1000000 ? "compact" : "standard",
        maximumFractionDigits: Math.abs(v) >= 1000000 ? 2 : 0,
      }).format(v);
const colors = ["#276b50", "#83a88c", "#dbad59", "#8b90b5", "#d08269"];
const pages = [
  ["overview", "Vue d’ensemble", LayoutDashboard],
  ["segments", "Segments & clients", Users],
  ["analysis", "Qualité du modèle", ChartNoAxesCombined],
  ["prediction", "Classer un client", Users],
  ["chat", "Assistant marketing", MessageSquare],
];
async function request(path, options = {}) {
  const res = await fetch("/api/" + path, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Service indisponible.");
  return data;
}
function useData(path) {
  const [state, setState] = useState({ loading: true });
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ path, loading: true });
    request(path, { signal: controller.signal })
      .then((data) => setState({ path, data, loading: false }))
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({ path, error: error.message, loading: false });
      });
    return () => controller.abort();
  }, [path, version]);
  return {
    ...(state.path === path ? state : { loading: true }),
    retry: () => setVersion((v) => v + 1),
  };
}
function State({ resource, children }) {
  if (resource.loading)
    return (
      <div className="empty" role="status">
        <RefreshCw className="spin" /> Chargement des données…
      </div>
    );
  if (resource.error)
    return (
      <div className="empty" role="alert">
        <CircleHelp />
        <p>{resource.error}</p>
        <button onClick={resource.retry}>Réessayer</button>
      </div>
    );
  return children(resource.data);
}
function download(rows, name) {
  if (!rows?.length) return;
  const keys = Object.keys(rows[0]);
  const cell = (v) =>
    '"' +
    String(v ?? "")
      .replace(/^[=+@-]/, "'$&")
      .replaceAll('"', '""') +
    '"';
  const content = [keys, ...rows.map((row) => keys.map((k) => row[k]))]
    .map((row) => row.map(cell).join(";"))
    .join("\r\n");
  const url = URL.createObjectURL(
    new Blob(["\ufeff" + content], { type: "text/csv;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function Table({ rows }) {
  if (!rows?.length)
    return <p className="empty">Aucune donnée pour cette sélection.</p>;
  const keys = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k}>{k.replaceAll("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {keys.map((k) => (
                <td key={k}>
                  {typeof row[k] === "number"
                    ? number(row[k], 4)
                    : String(row[k] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Metric({ label, value, detail }) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}
function Overview({ summary, audit, navigate, ask }) {
  return (
    <State resource={summary}>
      {(payload) => {
        const rows = payload.data;
        const a = audit.data?.audit?.data?.[0];
        return (
          <>
            <div className="hero">
              <div>
                <span className="eyebrow">DE LA DONNÉE À LA DÉCISION</span>
                <h2>
                  Comprendre vos clients.
                  <br />
                  Concentrer vos efforts.
                </h2>
                <p>
                  Explorez les comportements d’achat et identifiez les actions
                  adaptées à chaque segment.
                </p>
                <button
                  className="primary"
                  onClick={() => navigate("segments")}
                >
                  Explorer les segments <ArrowRight size={17} />
                </button>
              </div>
              <div className="hero-art" aria-hidden="true">
                <div className="orbit one" />
                <div className="orbit two" />
                <div className="orbit three" />
                <div className="art-label">
                  R<span>F</span>M
                </div>
                <small>Une lecture à trois dimensions</small>
              </div>
            </div>
            <div className="metrics">
              <Metric
                label="Clients segmentés"
                value={number(rows.reduce((n, r) => n + r.Effectif, 0))}
                detail="Clients avec achats positifs"
              />
              <Metric
                label="Chiffre d’affaires"
                value={money(a?.gross_amount_GBP)}
                detail="Achats positifs, périmètre analysé"
              />
              <Metric
                label="Segments"
                value={rows.length}
                detail="Une segmentation à vocation commerciale"
              />
              <Metric
                label="Montants retournés"
                value={
                  a ? number(a.returns_pct_gross, 2) + " %" : "Non disponible"
                }
                detail="Part du chiffre d’affaires positif"
              />
            </div>
            {audit.error && (
              <p className="notice">
                Le périmètre monétaire est indisponible.{" "}
                <button onClick={audit.retry}>Réessayer</button>
              </p>
            )}
            <div className="split">
              <section className="card">
                <div className="section-title">
                  <div>
                    <h3>Où se concentre la valeur ?</h3>
                    <p>Part du chiffre d’affaires par segment</p>
                  </div>
                  <span className="tag">Achats positifs</span>
                </div>
                <div className="bars">
                  {rows.map((r, i) => (
                    <button
                      className="bar-row"
                      key={r.Segment}
                      onClick={() => navigate("segments", r.Segment)}
                    >
                      <span>
                        <i style={{ background: colors[i % 5] }} />
                        {r.Segment}
                      </span>
                      <div className="track">
                        <div
                          style={{
                            width: `${r.Pct_CA}%`,
                            background: colors[i % 5],
                          }}
                        />
                      </div>
                      <b>{number(r.Pct_CA, 1)} %</b>
                    </button>
                  ))}
                </div>
                <p className="source">Source : {payload.source_file}</p>
              </section>
              <section className="card insight">
                <span className="eyebrow">PASSER À L’ACTION</span>
                <h3>
                  Les bons leviers,
                  <br />
                  pour les bons clients.
                </h3>
                <p>
                  Consultez les recommandations issues de l’analyse, puis
                  approfondissez avec l’assistant.
                </p>
                <button
                  onClick={() =>
                    ask(
                      "Quelles actions marketing prioriser selon les segments ?",
                    )
                  }
                >
                  Identifier mes priorités <ArrowUpRight size={18} />
                </button>
                <div className="note">
                  <CircleHelp size={18} />
                  <span>
                    Les recommandations sont des pistes à tester, pas des
                    résultats de campagne.
                  </span>
                </div>
              </section>
            </div>
          </>
        );
      }}
    </State>
  );
}
function Segments({ summary, selected, setSelected, ask }) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const clients = useData(
    `rfm-clients-segments?limit=25&offset=${page * 25}${selected ? "&segment=" + encodeURIComponent(selected) : ""}`,
  );
  const detail = useData(
    selected
      ? "segments/" + encodeURIComponent(selected)
      : "recommandations-segments",
  );
  function select(value) {
    setSelected(value);
    setPage(0);
    setQuery("");
  }
  return (
    <>
      <div className="section-title">
        <div>
          <h2>À chaque segment, une stratégie.</h2>
          <p>
            Comparez les profils et consultez les clients du groupe sélectionné.
          </p>
        </div>
      </div>
      <State resource={summary}>
        {(p) => (
          <div className="segment-grid">
            {p.data.map((r, i) => (
              <button
                key={r.Segment}
                className={
                  "segment-card " + (selected === r.Segment ? "selected" : "")
                }
                onClick={() => select(r.Segment)}
              >
                <i style={{ background: colors[i % 5] }} />
                <h3>{r.Segment}</h3>
                <strong>{number(r.Effectif)}</strong>
                <span>clients · {number(r.Pct_CA, 1)} % du CA</span>
              </button>
            ))}
          </div>
        )}
      </State>
      <section className="card">
        <div className="section-title">
          <h3>{selected || "Recommandations marketing"}</h3>
          {selected && (
            <button
              onClick={() =>
                ask(
                  `Quelle action recommandes-tu pour le segment ${selected} ?`,
                )
              }
            >
              Approfondir <ArrowUpRight size={16} />
            </button>
          )}
        </div>
        <State resource={detail}>
          {(d) =>
            selected ? (
              <>
                <p className="recommendation">
                  {d.recommandation["Recommandation marketing"]}
                </p>
                <div className="metrics compact">
                  <Metric
                    label="Récence moyenne"
                    value={number(d.synthese.Recence_moy, 1) + " j"}
                    detail="Depuis le dernier achat"
                  />
                  <Metric
                    label="Fréquence moyenne"
                    value={number(d.synthese.Frequence_moy, 1)}
                    detail="Factures par client"
                  />
                  <Metric
                    label="Montant moyen"
                    value={money(d.synthese.Montant_moy)}
                    detail="Achats positifs par client"
                  />
                </div>
                <p>Pays principaux : {d.synthese["Top pays"]}</p>
                <p className="source">
                  Sources : {Object.values(d.sources).join(", ")}
                </p>
              </>
            ) : (
              <Table rows={d.data} />
            )
          }
        </State>
      </section>
      <section className="card">
        <div className="section-title">
          <div>
            <h3>Explorer les clients</h3>
            <p>RFM individuel, sans coordonnées personnelles</p>
          </div>
          <select
            aria-label="Filtrer par segment"
            value={selected}
            onChange={(e) => select(e.target.value)}
          >
            <option value="">Tous les segments</option>
            {summary.data?.data.map((r) => (
              <option key={r.Segment}>{r.Segment}</option>
            ))}
          </select>
        </div>
        <div className="toolbar">
          <label className="search">
            <Search size={17} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher dans cette page"
            />
          </label>
          <button
            disabled={!clients.data?.data?.length}
            onClick={() =>
              download(
                clients.data.data.filter((r) =>
                  JSON.stringify(r).toLowerCase().includes(query.toLowerCase()),
                ),
                "clients-page.csv",
              )
            }
          >
            <Download size={16} />
            Exporter cette page
          </button>
        </div>
        <State resource={clients}>
          {(p) => (
            <>
              <Table
                rows={p.data
                  .filter((r) =>
                    JSON.stringify(r)
                      .toLowerCase()
                      .includes(query.toLowerCase()),
                  )
                  .map((r) => ({
                    Client: r.CustomerID,
                    Segment: r.segment_name,
                    "Récence (j)": r.Recency,
                    Factures: r.Frequency,
                    "Montant (£)": r.Monetary,
                    Pays: r.CountryMode,
                  }))}
              />
              <div className="pagination">
                <span>
                  {number(p.pagination.total)} clients · page {page + 1} sur{" "}
                  {Math.max(1, Math.ceil(p.pagination.total / 25))}
                </span>
                <div>
                  <button
                    disabled={page === 0}
                    onClick={() => setPage((v) => v - 1)}
                  >
                    Précédent
                  </button>
                  <button
                    disabled={(page + 1) * 25 >= p.pagination.total}
                    onClick={() => setPage((v) => v + 1)}
                  >
                    Suivant
                  </button>
                </div>
              </div>
              <p className="source">
                Source : {p.source_file}. Recherche et export limités aux 25
                lignes de la page.
              </p>
            </>
          )}
        </State>
      </section>
    </>
  );
}
function Analysis({ audit }) {
  const evaluation = useData("evaluation-k");
  const choice = useData("choix-k");
  const comparison = useData("comparaison-segmentations");
  return (
    <>
      <h2>Un choix commercial, une analyse mesurée.</h2>
      <p className="subtitle">
        Comparez les critères statistiques et mesurez l’effet des retours.
      </p>
      <div className="split">
        <section className="card">
          <h3>Comment choisir le nombre de groupes ?</h3>
          <p>
            Chaque indice apporte un éclairage différent. Le coude est indicatif
            et le choix commercial doit être validé par des campagnes.
          </p>
          <State resource={choice}>
            {(p) => (
              <>
                <Table rows={p.data} />
                <p className="source">Source : {p.source_file}</p>
              </>
            )}
          </State>
        </section>
        <section className="card">
          <h3>Sensibilité aux annulations et retours</h3>
          <State resource={audit}>
            {(d) => {
              const r = d.comparaison.data[0];
              return (
                <>
                  <div className="metrics compact">
                    <Metric
                      label="Accord des partitions (ARI)"
                      value={number(r.ari, 4)}
                      detail="Comparaison achats positifs / montant net"
                    />
                    <Metric
                      label="Clients changeant de groupe"
                      value={number(r.migrated_pct, 2) + " %"}
                      detail={
                        number(r.migrated_clients) +
                        " clients après appariement"
                      }
                    />
                  </div>
                  <p>
                    La population, R, F et le prétraitement restent fixes. Seul
                    le montant devient net. Un changement de groupe ne signifie
                    pas une perte de valeur ; les noms des groupes nets sont des
                    repères.
                  </p>
                  <p className="source">Source : {d.comparaison.source_file}</p>
                </>
              );
            }}
          </State>
        </section>
      </div>
      <section className="card">
        <div className="section-title">
          <h3>Évaluation de k</h3>
          <button
            disabled={!evaluation.data}
            onClick={() => download(evaluation.data.data, "evaluation-k.csv")}
          >
            <Download size={16} />
            Exporter
          </button>
        </div>
        <State resource={evaluation}>
          {(p) => (
            <>
              <Table
                rows={p.data.map((r) => ({
                  k: r.k,
                  Silhouette: r.silhouette,
                  Inertie: r.inertia,
                  "Calinski-Harabasz": r.calinski_harabasz,
                  "Davies-Bouldin": r.davies_bouldin,
                  "Stabilité ARI": r.stability_ari,
                }))}
              />
              <p className="source">Source : {p.source_file}</p>
            </>
          )}
        </State>
      </section>
      <section className="card">
        <h3>Correspondance entre quatre et cinq groupes</h3>
        <p>
          Chaque cellule compte les clients communs au groupe en ligne (k=4) et
          en colonne (k=5).
        </p>
        <State resource={comparison}>
          {(d) => (
            <>
              <Table rows={d.correspondance_k4_k5.data} />
              <p className="source">
                Source : {d.correspondance_k4_k5.source_file}
              </p>
            </>
          )}
        </State>
      </section>
    </>
  );
}
function Chat({ draft, clearDraft }) {
  const [session, setSession] = useState(() => {
    try {
      return sessionStorage.getItem("rfm-session") || crypto.randomUUID();
    } catch {
      return crypto.randomUUID();
    }
  });
  const [messages, setMessages] = useState(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem("rfm-messages") || "[]");
      return Array.isArray(saved)
        ? saved.filter(
            (m) =>
              ["user", "assistant"].includes(m.role) &&
              typeof m.content === "string",
          )
        : [];
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState(draft || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const end = useRef(null);
  const active = useRef(false);
  useEffect(() => {
    try {
      sessionStorage.setItem("rfm-session", session);
      sessionStorage.setItem("rfm-messages", JSON.stringify(messages));
    } catch {
      /* Storage can be disabled. */
    }
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [session, messages, busy]);
  useEffect(() => {
    if (draft) {
      setInput(draft);
      clearDraft();
    }
  }, [draft, clearDraft]);
  async function send(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || active.current) return;
    active.current = true;
    setBusy(true);
    setError("");
    setInput("");
    setMessages((v) => [...v, { role: "user", content: text }]);
    try {
      const data = await request("chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, sessionId: session }),
        signal: AbortSignal.timeout(320000),
      });
      setMessages((v) => [...v, { role: "assistant", content: data.answer }]);
    } catch (err) {
      setError(err.message);
      setInput(text);
    } finally {
      active.current = false;
      setBusy(false);
    }
  }
  return (
    <section className="chat card">
      <div className="section-title">
        <div>
          <h2>Votre partenaire d’analyse.</h2>
          <p>Des réponses ancrées dans les résultats du projet.</p>
        </div>
        <button
          disabled={busy}
          onClick={() => {
            setSession(crypto.randomUUID());
            setMessages([]);
            setError("");
            setInput("");
          }}
        >
          <Plus size={17} />
          Nouvelle discussion
        </button>
      </div>
      <div className="conversation" role="log" aria-live="polite">
        {!messages.length && (
          <div className="chat-welcome">
            <div className="assistant-mark">
              <Layers />
            </div>
            <h3>Quelle décision souhaitez-vous éclairer ?</h3>
            <p>
              Segments, actions marketing ou choix du modèle : commencez par une
              question.
            </p>
            <div className="suggestions">
              {[
                "Quels segments concentrent le chiffre d’affaires ?",
                "Pourquoi avoir choisi cinq segments ?",
                "Quel est l’impact des retours ?",
              ].map((q) => (
                <button key={q} onClick={() => setInput(q)}>
                  {q}
                  <ArrowUpRight size={16} />
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <article key={i} className={"message " + m.role}>
            <small>{m.role === "user" ? "Vous" : "Marketing AI"}</small>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {m.content}
            </ReactMarkdown>
          </article>
        ))}
        {busy && (
          <p role="status" className="thinking">
            <RefreshCw size={15} className="spin" />
            L’assistant prépare sa réponse…
          </p>
        )}
        <div ref={end} />
      </div>
      {error && (
        <p className="error" role="alert">
          {error} Votre question est conservée dans le champ pour réessayer.
        </p>
      )}
      <form className="composer" onSubmit={send}>
        <textarea
          aria-label="Votre question"
          maxLength={2000}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Posez votre question sur les résultats…"
          disabled={busy}
        />
        <button
          className="primary"
          disabled={busy || !input.trim()}
          aria-label="Envoyer la question"
        >
          <Send size={19} />
        </button>
      </form>
      <p className="source">{input.length}/2 000 caractères</p>
    </section>
  );
}
export default function App() {
  const [page, setPage] = useState(() => {
    try {
      const saved = sessionStorage.getItem("rfm-page");
      return pages.some(([id]) => id === saved) ? saved : "overview";
    } catch {
      return "overview";
    }
  });
  useEffect(() => {
    try {
      sessionStorage.setItem("rfm-page", page);
    } catch {
      // Navigation remains available when browser storage is disabled.
    }
  }, [page]);
  const [selected, setSelected] = useState("");
  const [draft, setDraft] = useState("");
  const summary = useData("tableau-synthese-segments");
  const audit = useData("sensibilite-retours");
  const a = audit.data?.audit?.data?.[0];
  function navigate(p, segment) {
    setPage(p);
    if (segment) setSelected(segment);
  }
  function ask(q) {
    setDraft(q);
    setPage("chat");
  }
  return (
    <div className="app">
      <a className="skip" href="#content">
        Aller au contenu
      </a>
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("overview");
          }}
        >
          <span className="brand-icon">
            <Layers size={23} />
          </span>
          <span>
            RFM<span className="brand-light"> studio</span>
            <small>CUSTOMER INTELLIGENCE</small>
          </span>
        </a>
        <p className="nav-label">ESPACE D’ANALYSE</p>
        <nav aria-label="Navigation principale">
          {pages.map(([id, label, Icon]) => (
            <button
              aria-current={page === id ? "page" : undefined}
              className={page === id ? "active" : ""}
              key={id}
              onClick={() => navigate(id)}
            >
              <Icon size={19} />
              {label}
              {id === "chat" && <span className="ai-badge">AI</span>}
            </button>
          ))}
        </nav>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            Plateforme RFM <span>/</span>{" "}
            <b>{pages.find((p) => p[0] === page)[1]}</b>
          </div>
          <span className="status">
            <i className={summary.error ? "offline" : ""} />
            {summary.loading
              ? "Connexion…"
              : summary.error
                ? "API indisponible"
                : "Données connectées"}
          </span>
        </header>
        <main id="content">
          <div className="page-header">
            <div>
              <span className="eyebrow">INTELLIGENCE CLIENT</span>
              <h1>{pages.find((p) => p[0] === page)[1]}</h1>
            </div>
            <div className="period">
              <span>PÉRIODE D’OBSERVATION</span>
              <b>
                {a
                  ? a.window_start.slice(0, 10).split("-").reverse().join("/") +
                    " au " +
                    a.window_end.slice(0, 10).split("-").reverse().join("/")
                  : "Période indisponible"}
              </b>
              <small>Données historiques</small>
            </div>
          </div>
          {page === "overview" && (
            <Overview
              summary={summary}
              audit={audit}
              navigate={navigate}
              ask={ask}
            />
          )}
          {page === "segments" && (
            <Segments
              summary={summary}
              selected={selected}
              setSelected={setSelected}
              ask={ask}
            />
          )}
          {page === "analysis" && <Analysis audit={audit} />}
          {page === "prediction" && <Prediction ask={ask} />}
          <div hidden={page !== "chat"}>
            <Chat draft={draft} clearDraft={() => setDraft("")} />
          </div>
          <footer>
            RFM studio · Analyse des achats positifs · Montants en livres
            sterling (£)
          </footer>
        </main>
      </div>
    </div>
  );
}
