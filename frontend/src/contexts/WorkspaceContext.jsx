import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { patientService } from '../services/patientService.js';
import { riskService } from '../services/riskService.js';
import { settingsService } from '../services/settingsService.js';

const WorkspaceContext = createContext(null);
export function WorkspaceProvider({ children }) {
  const [patients, setPatients] = useState([]);
  const [users, setUsers] = useState([]);
  const [rules, setRules] = useState(null);
  const [integrations, setIntegrations] = useState(null);
  const [source, setSource] = useState('synthetic');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [records, people, scoringRules, integrationStatus] = await Promise.all([
        patientService.list(), settingsService.users(), riskService.rules(), settingsService.integrations(),
      ]);
      setPatients(records); setUsers(people); setRules(scoringRules); setIntegrations(integrationStatus);
    } catch (failure) { setError(failure.message); throw failure; }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { refresh().catch(() => {}); }, [refresh]);
  const visiblePatients = useMemo(() => patients.filter(patient => source === 'all' || patient.source === source), [patients, source]);
  return <WorkspaceContext.Provider value={{ patients, visiblePatients, users, rules, integrations, source, setSource, loading, error, refresh }}>{children}</WorkspaceContext.Provider>;
}
export const useWorkspace = () => useContext(WorkspaceContext);
