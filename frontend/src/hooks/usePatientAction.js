import { useState } from 'react';
export default function usePatientAction(onSaved) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  async function run(operation, message = 'Saved successfully') {
    setBusy(true); setError(''); setSuccess('');
    try { await operation(); await onSaved(); setSuccess(message); return true; }
    catch (failure) { setError(failure.message); return false; }
    finally { setBusy(false); }
  }
  return { busy, error, success, run };
}
