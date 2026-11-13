import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import Badge from '../common/Badge.jsx';
import { navigation } from './Sidebar.jsx';
import Icon from '../common/Icon.jsx';
import {useNotifications} from '../../contexts/NotificationsContext.jsx';
export default function Topbar() {
  const { user, logout } = useAuth();
  const {unread}=useNotifications();
  const { pathname } = useLocation();
  const title = navigation.find(([path]) => pathname.startsWith(path))?.[1] || 'Workspace';
  const role = { nurse: 'Nurse', counsellor: 'Counsellor', lab: 'Laboratory', clinician: 'Clinician', admin: 'Administrator' }[user.role] || user.role;
  const accountScope = user.edit_any_facility ? `${role} · All facilities` : `${role} · ${user.facility}`;
  return <header className="topbar"><div className="breadcrumb">Workspace / <strong>{title}</strong></div><div className="top-actions"><Link to="/help" className="icon-button" aria-label="Help and support" title="Help and support"><Icon name="help"/></Link><Link to="/notifications" className="icon-button notification-bell" aria-label={`Notifications, ${unread} unread`} title="Notifications"><Icon name="bell"/>{unread>0&&<span className="notification-count">{unread>99?'99+':unread}</span>}</Link><Link to="/settings" className="account"><div className="avatar">{user.name.split(' ').map(word => word[0]).slice(0, 2).join('')}</div><div><b>{user.name}</b><small>{accountScope}</small></div></Link><button className="text-link" onClick={() => logout().catch(() => {})}><Icon name="logout" size={17}/> Sign out</button></div></header>;
}
