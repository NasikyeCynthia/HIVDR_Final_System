import PieChart from './PieChart.jsx';
export default function DecisionChart({patients}) {
 return <PieChart title="Decisions made" subtitle="Among patients with a recorded decision" items={['Maintained','Substituted','Switched'].map((label,i)=>({label,value:patients.filter(p=>p.decision===label).length,color:['#27845d','#d8a510','#c34351'][i]}))}/>;
}
