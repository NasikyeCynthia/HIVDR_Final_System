import { useAuth } from './AuthContext.jsx';
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
  const { user } = useAuth();
  const canAccessAll = true; // everyone can view all facilities; edits stay limited to their own facility
  const canManageDataset = user.role === 'admin';
  const [source, setSourceState] = useState('original');
  const [datasetSaving, setDatasetSaving] = useState(false);
  const [facility, setFacility] = useState(canAccessAll ? 'all' : user.facility);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refreshDataset = useCallback(async () => {
    const selection = await settingsService.dataset();
    setSourceState(selection.source === 'synthetic' ? 'synthetic' : 'original');
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [records, people, scoringRules, integrationStatus, dataset] = await Promise.all([
        patientService.list(), settingsService.users(), riskService.rules(), settingsService.integrations(), settingsService.dataset(),
      ]);
      setPatients(records);
      setUsers(people);
      setRules(scoringRules);
      setIntegrations(integrationStatus);
      setSourceState(dataset.source === 'synthetic' ? 'synthetic' : 'original');
    } catch (failure) {
      setError(failure.message);
      throw failure;
    } finally {
      setLoading(false);
    }
  }, []);

  const setSource = useCallback(async nextSource => {
    if (!canManageDataset || !['original', 'synthetic'].includes(nextSource)) return;
    setDatasetSaving(true);
    setError('');
    try {
      const result = await settingsService.updateDataset(nextSource);
      setSourceState(result.source);
    } catch (failure) {
      setError(failure.message);
      throw failure;
    } finally {
      setDatasetSaving(false);
    }
  }, [canManageDataset]);

  useEffect(() => { refresh().catch(() => {}); }, [refresh]);

  // Other signed-in roles pick up the administrator's shared dataset choice promptly.
  useEffect(() => {
    const timer = window.setInterval(() => { refreshDataset().catch(() => {}); }, 5000);
    const onFocus = () => { refreshDataset().catch(() => {}); };
    window.addEventListener('focus', onFocus);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', onFocus);
    };
  }, [refreshDataset]);

  const activeSource = source;
  const inActiveSource = patient => patient.source === activeSource || (
    patient.source === 'manual' && (patient.dataset_source || 'original') === activeSource
  );
  const facilities = useMemo(() => [...new Set(
    patients.filter(inActiveSource).map(patient => patient.facility),
  )].filter(Boolean).sort(), [patients, activeSource]);
  const visiblePatients = useMemo(() => patients.filter(patient => (
    inActiveSource(patient) && (facility === 'all' || patient.facility === facility)
  )), [patients, activeSource, facility]);

  useEffect(() => {
    if (canAccessAll && facility !== 'all' && !facilities.includes(facility)) {
      setFacility('all');
    }
  }, [facility, facilities, canAccessAll, user.facility]);

  return <WorkspaceContext.Provider value={{ patients, visiblePatients, users, rules, integrations, source, setSource, datasetSaving, canManageDataset, activeSource, facility, setFacility, facilities, canAccessAll, loading, error, refresh }}>{children}</WorkspaceContext.Provider>;
}

export const useWorkspace = () => useContext(WorkspaceContext);
