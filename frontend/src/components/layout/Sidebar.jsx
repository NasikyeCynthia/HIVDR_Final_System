import { NavLink } from 'react-router-dom';
export const navigation = [
  ['/dashboard', 'Dashboard', '▦'], ['/patients', 'Patient records', '♙'],
  ['/risk-assessment', 'Risk assessment', '◇'], ['/lab-results', 'Lab results', '⌕'],
  ['/resistance-classification', 'Resistance classification', '≋'], ['/discussion', 'Discussion', '☷'],
  ['/notifications', 'Notifications', '♧'], ['/settings', 'Settings', '⚙'],
];
export default function Sidebar() {
  return <aside className="sidebar"><div className="brand"><span className="brand-mark">+</span><div>HIVDR<small>SURVEILLANCE</small></div></div><div className="nav-label">WORKSPACE</div>
    <nav aria-label="Main navigation">{navigation.map(([path, label, icon], index) => <div key={path}>
      {index === 6 && <div className="nav-label">MANAGEMENT</div>}
      <NavLink to={path} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title={label}><span className="icon">{icon}</span><span className="nav-text">{label}</span></NavLink>
    </div>)}</nav>
    <div className="sidebar-footer"><span className="live-dot" />Local prototype<br /><b>Connected care. Informed action.</b><br />React + FastAPI · v0.2</div>
  </aside>;
}
