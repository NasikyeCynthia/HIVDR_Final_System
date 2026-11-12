import PieChart from './PieChart.jsx';
// Risk categories from the points score (High / Intermediate / Low / Incomplete).
export default function RiskChart({ patients }) {
  const cat = p => p.risk?.category || 'Incomplete';
  const items = [['High', '#c34351'], ['Intermediate', '#d8a510'], ['Low', '#27845d'], ['Incomplete', '#c9d1d5']]
    .map(([label, color]) => ({ label: label === 'Incomplete' ? 'Incomplete inputs' : `${label} risk`, filter: `risk:${label}`, value: patients.filter(p => cat(p) === label).length, color }));
  return <PieChart title="Risk assessment" subtitle="Points score; high risk is flagged" items={items} />;
}
