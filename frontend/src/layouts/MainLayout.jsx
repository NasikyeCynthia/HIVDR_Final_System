import { Outlet } from 'react-router-dom';
import Sidebar from '../components/layout/Sidebar.jsx';
import Topbar from '../components/layout/Topbar.jsx';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';

export default function MainLayout() {
  const {
    facility, setFacility, facilities, canAccessAll, source, loading, error, refresh,
  } = useWorkspace();
  const facilityValue = facility === 'all' || facilities.includes(facility) ? facility : '';

  return <div className="shell">
    <Sidebar />
    <main className="main">
      <Topbar />
      <div className="content">
        <div className="toolbar">
          <span className="tiny muted"><b>Dataset in use:</b> {source === 'synthetic' ? 'Synthetic demo' : 'Original data'}</span>
          <label htmlFor="facility-scope">Healthcare facility</label>
          <select id="facility-scope" value={facilityValue} disabled={!canAccessAll && !facilities.length} onChange={event => setFacility(event.target.value)}>
            {canAccessAll && <option value="all">All facilities (view only)</option>}
            {facilities.length
              ? facilities.map(name => <option key={name} value={name}>{name}</option>)
              : <option value="">No facilities in this dataset for your account</option>}
          </select>
          <button className="text-link" disabled={loading} onClick={() => refresh().catch(() => {})}>
            {loading ? 'Refreshing…' : '↻ Refresh'}
          </button>
        </div>
        {!canAccessAll && !facilities.length && <p className="notice info">
          Your assigned facility has no records in the selected dataset. An administrator can assign your account to an Original-data facility.
          Viewing access does not grant permission to edit or approve at other facilities.
        </p>}
        {error && <p role="alert" className="notice error">{error}</p>}
        <Outlet />
      </div>
    </main>
  </div>;
}
