import { Outlet } from 'react-router-dom';
import Sidebar from '../components/layout/Sidebar.jsx';
import Topbar from '../components/layout/Topbar.jsx';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';

export default function MainLayout() {
  const {
    facility, setFacility, facilities, canAccessAll, source, loading, error, refresh,
  } = useWorkspace();
  const facilityValue = facility === 'all' || facilities.includes(facility) ? facility : '';
  const { user } = useAuth();

  return <div className="shell">
    <Sidebar />
    <main className="main">
      <Topbar />
      <div className="content">
        <div className="toolbar">
          <span className="tiny muted"><b>Dataset in use:</b> {source === 'synthetic' ? 'Synthetic demo' : 'Original data'}</span>
          <label htmlFor="facility-scope">Healthcare facility</label>
          <select id="facility-scope" value={facilityValue} disabled={!canAccessAll && !facilities.length} onChange={event => setFacility(event.target.value)}>
            {canAccessAll && <option value="all">All facilities</option>}
            {facilities.length
              ? facilities.map(name => <option key={name} value={name}>{name}</option>)
              : <option value="">No facilities in this dataset for your account</option>}
          </select>
          <button className="text-link" disabled={loading} onClick={() => refresh().catch(() => {})}>
            {loading ? 'Refreshing…' : '↻ Refresh'}
          </button>
        </div>
        {canAccessAll && <p className="tiny muted">You can view all facilities or select one. Changes are limited to your role at your own facility ({user.facility}).</p>}
        {!canAccessAll && !facilities.length && <p className="notice info">
          Your assigned facility has no records in the selected dataset. Ask an administrator to assign your account to a facility with records.
          Viewing access does not grant permission to edit or approve at other facilities.
        </p>}
        {error && <p role="alert" className="notice error">{error}</p>}
        {loading && <p role="status" className="notice info"><b>Loading patient records…</b> With the full dataset this can take up to a minute; the counts below fill in when it finishes.</p>}
        <Outlet />
      </div>
    </main>
  </div>;
}
