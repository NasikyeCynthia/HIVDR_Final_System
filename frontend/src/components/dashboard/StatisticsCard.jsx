import { Link } from 'react-router-dom';
import { formatNumber } from '../../utils/format.js';
// tone: blue | crimson | teal | amber | violet | rose — colour accent for the tile.
export default function StatisticsCard({ title, value, description, icon, filter = '', tone = 'blue' }) {
  return <Link className={`stat tone-${tone}`} to={`/patients?filter=${encodeURIComponent(filter)}`}><div className="stat-label">{title}</div><div className="stat-number">{formatNumber(value)}</div><div className="stat-note">{description}</div><div className="stat-icon">{icon}</div></Link>;
}
