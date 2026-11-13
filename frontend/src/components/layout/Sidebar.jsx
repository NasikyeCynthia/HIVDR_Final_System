import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import Icon from '../common/Icon.jsx';
export const navigation = [
  ['/dashboard', 'Dashboard', 'dashboard'], ['/patients', 'Patient records', 'patients'],
  ['/risk-assessment', 'Risk & eligibility', 'risk'], ['/lab-results', 'Lab results', 'lab'],
  ['/resistance-classification', 'Resistance classification', 'resistance'], ['/discussion', 'Discussion', 'discussion'],
  ['/notifications', 'Notifications', 'bell'], ['/settings', 'Settings', 'settings'], ['/help','Help & support','help'],
];
export default function Sidebar() {
  const { user } = useAuth();
  const visibleNavigation = navigation;
  return <aside className="sidebar"><div className="brand"><span className="brand-mark">+</span><div>HIVDR<small>SURVEILLANCE</small></div></div><div className="nav-label">WORKSPACE</div>
    <nav aria-label="Main navigation">{visibleNavigation.map(([path, label, icon]) => <div key={path}>
      {path === '/notifications' && <div className="nav-label">MANAGEMENT</div>}
      <NavLink to={path} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title={label}><span className="icon"><Icon name={icon}/></span><span className="nav-text">{label}</span></NavLink>
    </div>)}</nav>
    <div className="sidebar-footer"><span className="live-dot" />Local prototype<br /><b>Connected care. Informed action.</b><br />Surveillance workspace · v0.3</div>
  </aside>;
}
