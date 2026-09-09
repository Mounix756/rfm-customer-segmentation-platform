import { useEffect, useState } from 'react';
import { Search, Download, RefreshCw } from 'lucide-react';
const format = value => new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(value);
const defaults = { q:'', country:'', recency_min:'', recency_max:'', frequency_min:'', frequency_max:'', monetary_min:'', monetary_max:'', sort_by:'CustomerID', order:'asc' };

export default function ClientsTable({ selected, onSegmentChange, segments }) {
  const [filters, setFilters] = useState(defaults);
  const [paging, setPaging] = useState({ key:'', offset:0 });
  const [resource, setResource] = useState({});
  const [countries, setCountries] = useState([]);
  const [retry, setRetry] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');
  const params = new URLSearchParams(Object.entries({...filters, segment:selected}).filter(([,v]) => v !== ''));
  const filterKey = params.toString();
  const offset = paging.key === filterKey ? paging.offset : 0;
  const path = `rfm-clients-segments?${filterKey}&limit=25&offset=${offset}`;
  const ready = resource.path === path;
  const data = ready ? resource.data : null;
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/clients/filters', {signal:controller.signal}).then(async r => { if(r.ok) setCountries((await r.json()).countries); }).catch(()=>{});
    return () => controller.abort();
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setResource({path});
    fetch('/api/'+path, {signal:controller.signal}).then(async r => {
      const body=await r.json(); if(!r.ok) throw Error(body.error || 'Vérifiez les filtres : minimum inférieur au maximum.');
      setResource({path,data:body});
    }).catch(e => { if(!controller.signal.aborted) setResource({path,error:e.message}); });
    return () => controller.abort();
  }, [path,retry]);
  function change(key,value) { setFilters(v=>({...v,[key]:value}));setExportError(''); }
  async function exportAll() {
    setExporting(true);setExportError('');
    try {
      const r=await fetch('/api/clients/export?'+filterKey, {signal:AbortSignal.timeout(30000)});
      if(!r.ok) throw Error('Export indisponible. Vérifiez les filtres et réessayez.');
      const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download='clients-selection.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    } catch(e) { setExportError(e.message); } finally { setExporting(false); }
  }
  return <section className="card"><div className="section-title"><div><h3>Explorer les clients</h3><p>Recherche et filtres sur tous les clients, export complet de la sélection.</p></div><button disabled={!data || exporting} onClick={exportAll}><Download size={16}/>{exporting ? 'Export en cours…' : 'Exporter toute la sélection'}</button></div><div className="toolbar"><label className="search"><Search size={17}/><input aria-label="Rechercher tous les clients" value={filters.q} onChange={e=>change('q',e.target.value)} placeholder="Identifiant, pays ou segment" maxLength={150}/></label><select aria-label="Filtrer par segment" value={selected} onChange={e=>onSegmentChange(e.target.value)}><option value="">Tous les segments</option>{segments.map(s=><option key={s}>{s}</option>)}</select><select aria-label="Filtrer par pays" value={filters.country} onChange={e=>change('country',e.target.value)}><option value="">Tous les pays</option>{countries.map(c=><option key={c}>{c}</option>)}</select></div><details className="filter-details"><summary>Filtres RFM et tri</summary><div className="filter-grid">{[['recency','Récence (jours)',0],['frequency','Fréquence (factures)',1],['monetary','Montant (GBP)',0]].map(([key,label,min])=><fieldset key={key}><legend>{label}</legend>{['min','max'].map(bound=><label key={bound}>{bound === 'min' ? 'Minimum' : 'Maximum'}<input type="number" min={min} step={key==='monetary'?'any':1} value={filters[key+'_'+bound]} onChange={e=>change(key+'_'+bound,e.target.value)}/></label>)}</fieldset>)}</div><div className="toolbar"><label>Trier par <select value={filters.sort_by} onChange={e=>change('sort_by',e.target.value)}>{[['CustomerID','Identifiant'],['Recency','Récence'],['Frequency','Fréquence'],['Monetary','Montant'],['CountryMode','Pays'],['segment_name','Segment']].map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><select aria-label="Ordre du tri" value={filters.order} onChange={e=>change('order',e.target.value)}><option value="asc">Croissant</option><option value="desc">Décroissant</option></select><button onClick={()=>{setFilters(defaults);onSegmentChange('');setExportError('');}}>Effacer les filtres</button></div></details>{exportError && <p className="error" role="alert">{exportError}</p>}{ready && resource.error ? <div className="empty" role="alert"><p>{resource.error}</p><button onClick={()=>setRetry(v=>v+1)}>Réessayer</button></div> : !data ? <p role="status"><RefreshCw size={16} className="spin"/> Chargement…</p> : <><div className="table-wrap"><table><thead><tr>{['Client','Segment','Récence (j)','Factures','Montant (GBP)','Pays'].map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{data.data.map(r=><tr key={r.CustomerID}><td>{r.CustomerID}</td><td>{r.segment_name}</td><td>{format(r.Recency)}</td><td>{format(r.Frequency)}</td><td>{format(r.Monetary)}</td><td>{r.CountryMode}</td></tr>)}</tbody></table></div>{!data.data.length && <p>Aucun client ne correspond à ces critères.</p>}<div className="pagination"><span>{format(data.pagination.total)} clients · page {Math.floor(offset/25)+1} sur {Math.max(1,Math.ceil(data.pagination.total/25))}</span><div><button disabled={offset===0} onClick={()=>setPaging({key:filterKey,offset:Math.max(0,offset-25)})}>Précédent</button><button disabled={offset+25>=data.pagination.total} onClick={()=>setPaging({key:filterKey,offset:offset+25})}>Suivant</button></div></div><p className="source">Source : {data.source_file}. {format(data.statistics.numeric?.Monetary?.sum || 0)} GBP d’achats positifs dans la sélection. Les 25 lignes affichées sont une page du résultat global.</p></>}</section>;
}
