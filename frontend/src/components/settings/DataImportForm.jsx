import { useState } from 'react';
import { settingsService } from '../../services/settingsService.js';
import { useWorkspace } from '../../contexts/WorkspaceContext.jsx';
import Feedback from '../common/Feedback.jsx';
export default function DataImportForm() {
  const { refresh } = useWorkspace();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(''); setSuccess('');
    const form = new FormData(event.currentTarget);
    const file = form.get('file');
    try {
      if (file.size > 40000000) throw new Error('Choose a CSV smaller than 40 MB.');
      const result = await settingsService.importCsv({ source: form.get('source'), csv: await file.text() });
      await refresh(); setSuccess(`${result.added} records imported; ${result.skipped} duplicates skipped.`);
    } catch (failure) { setError(failure.message); } finally { setBusy(false); }
  }
  return <form onSubmit={submit}><Feedback error={error} success={success} /><label htmlFor="source">Data provenance</label><select id="source" name="source"><option value="original">Original dataset</option><option value="synthetic">Synthetic demo dataset</option></select><label htmlFor="file" style={{ marginTop: 15 }}>CSV file</label><input id="file" name="file" type="file" accept=".csv" required /><div className="form-actions"><button className="btn" disabled={busy}>{busy ? 'Importing…' : 'Import CSV'}</button></div></form>;
}
