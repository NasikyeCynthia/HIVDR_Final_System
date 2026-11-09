import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
export default function DecisionChart({ patients }) {
  const categories = ['Maintained', 'Substituted', 'Switched'];
  const counts = categories.map(category => patients.filter(p => p.decision === category).length);
  const colors = ['#279b79', '#e9bc4b', '#d87075'];
  const total = counts.reduce((sum, count) => sum + count, 0);
  const first = total ? counts[0] / total * 100 : 0;
  const second = total ? first + counts[1] / total * 100 : 0;
  const background = total ? `conic-gradient(${colors[0]} 0 ${first}%, ${colors[1]} ${first}% ${second}%, ${colors[2]} ${second}% 100%)` : '#e9eef0';
  return <Card title="Clinical decisions" subtitle="Final recorded decision per current episode"><div className="donut-wrap"><div className="donut" style={{ background }} role="img" aria-label={`Maintained ${counts[0]}, substituted ${counts[1]}, switched ${counts[2]}`}><div className="donut-center">{total}<small>DECISIONS</small></div></div><div className="legend">{categories.map((category, i) => <Link key={category} to={`/patients?filter=${category}`}><i className="dot" style={{ background: colors[i] }} /><span>{category}</span><b>{counts[i]}</b></Link>)}</div></div></Card>;
}
