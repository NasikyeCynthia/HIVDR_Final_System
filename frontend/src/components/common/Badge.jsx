export default function Badge({ children, color = '' }) {
  return <span className={`badge ${color}`}>{children}</span>;
}
export function RiskBadge({ risk }) {
  const colors = { High: 'red', Moderate: 'yellow', Intermediate: 'yellow', Low: 'green' };
  return <Badge color={colors[risk.category] || ''}>{risk.category}</Badge>;
}
