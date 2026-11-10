import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
export default function PieChart({title,items,subtitle}) {
 const total=items.reduce((n,x)=>n+x.value,0); let angle=-Math.PI/2;
 const slices=items.filter(x=>x.value>0).map(item=>{const start=angle;angle+=item.value/total*Math.PI*2;const x=100+85*Math.cos(start),y=100+85*Math.sin(start),ex=100+85*Math.cos(angle),ey=100+85*Math.sin(angle);return {...item,path:`M100 100 L${x} ${y} A85 85 0 ${angle-start>Math.PI?1:0} 1 ${ex} ${ey} Z`};});
 return <Card title={title} subtitle={subtitle}><div className="pie-layout"><svg viewBox="0 0 200 200" role="img" aria-label={items.map(x=>`${x.label}: ${x.value}`).join(', ')}>{!total?<circle cx="100" cy="100" r="85" fill="#e9eef0"/>:slices.length===1?<circle cx="100" cy="100" r="85" fill={slices[0].color}/>:slices.map(x=><path key={x.label} d={x.path} fill={x.color} stroke="white" strokeWidth="2"><title>{x.label}: {x.value} ({Math.round(x.value/total*100)}%)</title></path>)}</svg><div className="pie-legend">{items.map(x=><Link key={x.label} to={`/patients?filter=${encodeURIComponent(x.filter||x.label)}`}><i style={{background:x.color}}/><span>{x.label}</span><b>{x.value}</b><small>{total?Math.round(x.value/total*100):0}%</small></Link>)}<p className="tiny muted">{total} records in this chart</p></div></div></Card>;
}
