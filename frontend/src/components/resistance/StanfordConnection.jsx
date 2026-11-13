import {useState} from 'react';
import {request} from '../../services/api.js';
import Card from '../common/Card.jsx';

export default function StanfordConnection() {
  const [check, setCheck] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function verify() {
    setBusy(true); setError(''); setCheck(null);
    try { setCheck(await request('/integrations/stanford/check')); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <Card title="Stanford API connection" className="section-gap">
    <p>Laboratory mutations or sequence → your backend → Stanford HIVdb → drug scores and resistance categories saved to this patient.</p>
    <div className="toolbar"><button type="button" className="btn secondary" disabled={busy} onClick={verify}>{busy ? 'Checking Stanford…' : 'Check live API connection'}</button>
      <span role="status" aria-live="polite">{busy ? 'Contacting Stanford; no patient data is sent.' : check ? `Connected · ${check.version.text} · checked ${new Date(check.checked_at).toLocaleString()}` : error ? 'Connection check failed' : 'Configured · live connection has not been checked here'}</span></div>
    {error && <p className="notice error" role="alert">{error}</p>}
    <p className="tiny muted">This checks the live algorithm version only. Open a patient’s Resistance tab and choose “Analyse with Stanford” to interpret their laboratory result. A recorded dataset result does not mean an API request has been run.</p>
    <details><summary>How the request works</summary><p className="tiny">Connection check: <code>GET /api/integrations/stanford/check</code>. Patient analysis: <code>POST /api/workflow/patients/&#123;id&#125;/interpret</code>. The backend queries <code>https://hivdb.stanford.edu/graphql</code>. Only mutation tokens or sequence bases are sent to Stanford; FASTA headers are stripped locally.</p></details>
  </Card>;
}
