import {useState} from 'react';
import {Link} from 'react-router-dom';
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
  return <Card title="Stanford HIVdb" className="section-gap">
    <div className="toolbar"><button type="button" className="btn secondary" disabled={busy} onClick={verify}>{busy?'Checking…':'Check connection'}</button><span role="status" aria-live="polite">{busy?'Checking connection…':check?`Connected · ${check.version.text} · ${new Date(check.checked_at).toLocaleString('en-GB')}`:error?'Connection failed':'Connection not checked'}</span><Link className="text-link" to="/help#analysis-problems">Help</Link></div>
    {error&&<p className="notice error" role="alert">{error}</p>}
  </Card>;
}
