import PieChart from './PieChart.jsx';
export default function RiskChart({patients}) {
 return <PieChart title="Risk assessment" subtitle="Incomplete assessments are shown separately" items={['Low','Intermediate','High'].map((label,i)=>({label,value:patients.filter(p=>p.risk.category===label).length,color:['#27845d','#d8a510','#c34351'][i]}))}/>;
}
