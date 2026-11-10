import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
export const navigation = [
  ['/dashboard', 'Dashboard', '▦'], ['/patients', 'Patient records', '♙'],
  ['/risk-assessment', 'Risk assessment', '◇'], ['/lab-results', 'Lab results', '⌕'],
  ['/resistance-classification', 'Resistance classification', '≋'], ['/discussion', 'Discussion', '☷'],
  ['/notifications', 'Notifications', '♧'], ['/settings', 'Settings', '⚙'],
];
export default function Sidebar() {
  const { user } = useAuth();
  const visibleNavigation = navigation.filter(([path]) => (
    user.role !== 'nurse' || !['/lab-results', '/resistance-classification', '/discussion'].includes(path)
  ));
  return <aside className="sidebar"><div className="brand"><span className="brand-mark">+</span><div>HIVDR<small>SURVEILLANCE</small></div></div><div className="nav-label">WORKSPACE</div>
    <nav aria-label="Main navigation">{visibleNavigation.map(([path, label, icon]) => <div key={path}>
      {path === '/notifications' && <div className="nav-label">MANAGEMENT</div>}
      <NavLink to={path} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title={label}><span className="icon">{icon}</span><span className="nav-text">{label}</span></NavLink>
    </div>)}</nav>
    <div className="sidebar-footer"><span className="live-dot" />Local prototype<br /><b>Connected care. Informed action.</b><br />Surveillance workspace · v0.3</div>
  </aside>;
}
