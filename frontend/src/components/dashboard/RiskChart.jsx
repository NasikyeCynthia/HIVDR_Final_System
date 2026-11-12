import PieChart from './PieChart.jsx';
// Risk of drug resistance (points score) among non-suppressed patients.
export default function RiskChart({ patients }) {
  const cat = p => p.risk?.category || 'Not assessed';
  const items = [['High', '#c34351'], ['Moderate', '#d8a510'], ['Low', '#27845d'], ['Not applicable', '#c9d1d5']]
    .map(([label, color]) => ({ label: label === 'Not applicable' ? 'Suppressed / not scored' : `${label} risk`, filter: `risk:${label}`, value: patients.filter(p => cat(p) === label).length, color }));
  return <PieChart title="Risk assessment" subtitle="Risk of drug resistance (points score); flagged = high risk" items={items} />;
}
