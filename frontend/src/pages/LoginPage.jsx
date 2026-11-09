import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext.jsx';
import FormField from '../components/common/FormField.jsx';
import Feedback from '../components/common/Feedback.jsx';
export default function LoginPage() {
  const { login, connectionError } = useAuth();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { await login(Object.fromEntries(new FormData(event.currentTarget))); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <div className="login"><section className="login-art"><div className="brand"><span className="brand-mark">+</span><div>HIVDR<small>SURVEILLANCE SYSTEM</small></div></div><h1>Better visibility.<br />Timely decisions.<br />Connected care.</h1><p>A shared workspace for patient monitoring, laboratory follow-through and clinical review.</p></section><section className="login-form-wrap"><form className="login-form" onSubmit={submit}><div className="eyebrow">HIVDR surveillance</div><h2>Welcome back</h2><p className="muted">Sign in to your care team workspace.</p><FormField label="Username" name="username" autoComplete="username" required /><FormField label="Password" name="password" type="password" autoComplete="current-password" required /><button className="btn" disabled={busy}>{busy ? 'Signing in…' : 'Sign in to workspace →'}</button><Feedback error={error || connectionError} /><p className="tiny muted" style={{ marginTop: 24 }}>Demo accounts: admin, nurse, counsellor, lab, clinician. The generated password is in <b>backend/data/local_login.txt</b> after starting the backend.</p></form></section></div>;
}
