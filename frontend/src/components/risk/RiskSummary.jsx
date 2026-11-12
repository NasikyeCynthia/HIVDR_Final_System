import Card from '../common/Card.jsx';
import { Link } from 'react-router-dom';
import Badge, { EligibilityBadge } from '../common/Badge.jsx';
import Feedback from '../common/Feedback.jsx';
import { useAuth, useCan } from '../../contexts/AuthContext.jsx';
import RiskScoreCard from './RiskScoreCard.jsx';
import ModelResults from './ModelResults.jsx';
import ViewOnly from '../common/ViewOnly.jsx';
import { riskService } from '../../services/riskService.js';
import usePatientAction from '../../hooks/usePatientAction.js';

// DR-testing eligibility under MoH criteria. The verdict is computed by the backend
// (app/services/eligibility_service.py); this panel only explains it and records IAC.
const MARK = { met: ['Met', 'green'], not_met: ['Not met', 'red'], unknown: ['Not documented', 'yellow'] };
const TIER = { Good: 'green', Fair: 'yellow', Poor: 'red' };
const fmt = iso => iso ? new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '';
const copies = o => `${o.qualifier || ''}${Number(o.copies).toLocaleString('en-GB')}`;

export default function RiskSummary({ patient, sessions = [], onSaved }) {
  const { user } = useAuth();
  const referral = usePatientAction(onSaved);
  const override = usePatientAction(onSaved);
  const iac = usePatientAction(onSaved);
  const e = patient.eligibility || {};
  const can = useCan();
  const canIac = can('record_iac', patient);
  const canRequest = can('request_dr_test', patient);
  const canOverride = can('refer_on_clinical_indication', patient);
  const referred = Boolean(patient.referred_at);
  const today = new Date().toISOString().slice(0, 10);

  function addSession(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    data.adherence_pct = Number(data.adherence_pct);
    iac.run(() => riskService.addIac(patient.id, data), 'IAC session recorded').then(ok => ok && form.reset());
  }
  function referOverride(event) {
    event.preventDefault();
    const reason = new FormData(event.currentTarget).get('reason');
    override.run(() => riskService.refer(patient.id, { basis: 'clinician_override', reason }), 'DR test requested with the stated indication');
  }

  return <>
    <RiskScoreCard risk={patient.risk} />
    <ModelResults patient={patient} />
    <Card title="DR-testing eligibility" subtitle={`MoH and WHO criteria · ${e.rule_version || ''}`}>
      <div className="split-heading"><div><EligibilityBadge patient={patient} />{e.pathway && <p className="tiny muted" style={{ margin: '8px 0 0' }}>{e.pathway}</p>}</div><span className="tiny muted">{e.indication}</span></div>
      {e.next_step && <p className="notice info" style={{ marginTop: 16 }}><b>Next step: </b>{e.next_step}</p>}
      {referred && <p className="notice info">Referred {fmt(String(patient.referred_at).slice(0, 10))}{patient.referral_basis ? ` — ${patient.referral_basis}` : ''}</p>}
      {(e.warnings || []).map(w => <p key={w} className="notice">{w}</p>)}
      {(e.info || []).map(w => <p key={w} className="notice info">{w}</p>)}

      <h3>Criteria</h3>
      <div className="table-wrap"><table><thead><tr><th>Criterion</th><th>Status</th><th>Evidence</th></tr></thead><tbody>
        {(e.criteria || []).map(c => <tr key={c.key}><td>{c.label}<div className="tiny muted">{e.sources?.[c.source]}</div></td><td><Badge color={MARK[c.status]?.[1]}>{MARK[c.status]?.[0]}</Badge></td><td>{c.detail}</td></tr>)}
      </tbody></table></div>
      {e.log_drop && <p className="tiny muted">Log drop: {e.log_drop.text}</p>}

      <h3 style={{ marginTop: 20 }}>Viral load results used</h3>
      {e.timeline?.length ? <div className="table-wrap"><table><thead><tr><th>Date</th><th>Copies/mL</th><th>1000 or more</th><th>Source column</th></tr></thead><tbody>
        {e.timeline.map((o, i) => <tr key={i}><td>{fmt(o.date)}</td><td>{copies(o)}</td><td>{o.kind === 'post' ? 'Post-decision' : o.nonsuppressed ? 'Yes' : 'No'}</td><td>{o.source}{o.also_in?.length ? <div className="tiny muted">also in {o.also_in.join(', ')}</div> : null}</td></tr>)}
      </tbody></table></div> : <p className="muted">No dated viral load results. Add them under Viral load history.</p>}
      <p className="tiny muted">Results are ordered by their own test dates; the same value recorded twice within 45 days is counted once.</p>

      <Feedback error={referral.error} success={referral.success} />
      {!referred && <div className="form-actions">{e.eligible ? <span>Eligible: the DR test is requested by laboratory staff on the <Link className="text-link" to={`/patients/${patient.id}?tab=laboratory`}>Laboratory tab →</Link></span> : <span className="tiny muted">The laboratory requests the test once the criteria are met.</span>}</div>}
    </Card>

    <Card title="Intensive adherence counselling" subtitle="Adherence by pill count: Good ≥95% · Fair 85–94% · Poor <85% · >105% investigate">
      <Feedback error={iac.error} success={iac.success} />
      {sessions.length ? <div className="table-wrap"><table><thead><tr><th>Date</th><th>Adherence</th><th>Rating</th><th>Method</th><th>Barriers / plan</th><th>Recorded by</th><th /></tr></thead><tbody>
        {sessions.map(s => { const tier = s.adherence_pct > 105 ? 'Investigate' : s.adherence_pct >= 95 ? 'Good' : s.adherence_pct >= 85 ? 'Fair' : 'Poor';
          return <tr key={s.id}><td>{fmt(s.session_date)}</td><td>{s.adherence_pct}%</td><td><Badge color={TIER[tier] || 'yellow'}>{tier}</Badge></td><td>{s.method}</td><td>{s.barriers}</td><td>{s.actor}</td>
            <td>{canIac && !referred && <button className="btn small secondary" disabled={iac.busy} onClick={() => iac.run(() => riskService.removeIac(patient.id, s.id), 'IAC session removed')}>Remove</button>}</td></tr>; })}
      </tbody></table></div> : <p className="muted">No IAC sessions recorded.</p>}
      {!canIac && <ViewOnly action="record_iac" />}
      {canIac && !referred && <form onSubmit={addSession} style={{ marginTop: 18 }}><div className="form-grid">
        <div className="field"><label htmlFor="iac-date">Session date</label><input id="iac-date" name="session_date" type="date" max={today} required /></div>
        <div className="field"><label htmlFor="iac-pct">Adherence (%)</label><input id="iac-pct" name="adherence_pct" type="number" min="0" max="150" step="0.1" required /></div>
        <div className="field"><label htmlFor="iac-method">Method</label><select id="iac-method" name="method" defaultValue="Pill count"><option>Pill count</option><option>Self-report</option><option>Pharmacy refill</option></select></div>
        <div className="field"><label htmlFor="iac-barriers">Barriers and agreed plan</label><input id="iac-barriers" name="barriers" maxLength="5000" /></div>
      </div><p className="tiny muted">Adherence % = pills taken ÷ pills expected × 100. Continue IAC until 3 consecutive sessions are good, then repeat the viral load.</p>
      <div className="form-actions"><button className="btn" disabled={iac.busy}>Record IAC session</button></div></form>}
    </Card>


  </>;
}
