import { Outlet } from 'react-router-dom';
import Sidebar from '../components/layout/Sidebar.jsx';
import Topbar from '../components/layout/Topbar.jsx';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
export default function MainLayout() {
  const { source, setSource, visiblePatients, loading, error, refresh } = useWorkspace();
  return <div className="shell"><Sidebar /><main className="main"><Topbar /><div className="content">
    <div className="toolbar source-toolbar"><label htmlFor="data-source">DATA SOURCE</label><select id="data-source" value={source} onChange={event => setSource(event.target.value)}>
      <option value="synthetic">Synthetic demo</option><option value="original">Original imported data</option><option value="manual">Manually registered</option><option value="all">All sources</option>
    </select><span className="count-chip">{visiblePatients.length} records</span><button className="text-link" disabled={loading} onClick={() => refresh().catch(() => {})}>{loading ? 'Refreshing…' : '↻ Refresh'}</button></div>
    {source === 'synthetic' && <div className="notice info">DEMO DATA · 499 source rows are bundled. Care-worker assignments and workflow statuses use a separate fictional demonstration overlay.</div>}
    {error ? <p role="alert" className="notice error">{error}</p> : null}
    <Outlet /><div className="footer-note"><span>HIVDR Surveillance · React frontend / Python API</span><span>Local prototype · v0.2</span></div>
  </div></main></div>;
}
