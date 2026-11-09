import { Link } from 'react-router-dom';
import { formatNumber } from '../../utils/format.js';
export default function StatisticsCard({ title, value, description, icon, filter = '' }) {
  return <Link className="stat" to={`/patients?filter=${encodeURIComponent(filter)}`}><div className="stat-label">{title}</div><div className="stat-number">{formatNumber(value)}</div><div className="stat-note">{description}</div><div className="stat-icon">{icon}</div></Link>;
}
