import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import Badge from '../common/Badge.jsx';
import { navigation } from './Sidebar.jsx';
export default function Topbar() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const title = navigation.find(([path]) => pathname.startsWith(path))?.[1] || 'Workspace';
  return <header className="topbar"><div className="breadcrumb">Workspace / <strong>{title}</strong></div><div className="top-actions"><Badge color="teal">LOCAL PROTOTYPE</Badge><Link to="/notifications" title="Notifications">♧</Link><div className="account"><div className="avatar">{user.name.split(' ').map(word => word[0]).slice(0, 2).join('')}</div><div><b>{user.name}</b><small>{user.role} · {user.facility}</small></div></div><button className="text-link" onClick={() => logout().catch(() => {})}>Sign out</button></div></header>;
}
