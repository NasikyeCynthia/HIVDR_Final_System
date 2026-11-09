import { useState } from 'react';
import Card from '../common/Card.jsx';
export default function SourceRecord({ original }) {
  const [query, setQuery] = useState('');
  return <Card title="Original source columns"><p className="tiny muted">Imported columns are preserved here, including empty fields. Profile changes are stored separately.</p><input aria-label="Search source columns" placeholder="Find a source field…" value={query} onChange={event => setQuery(event.target.value)} />{Object.entries(original).filter(([key, value]) => `${key} ${value}`.toLowerCase().includes(query.toLowerCase())).map(([key, value]) => <div className="raw-field" key={key}><span>{key}</span><span>{value || <i className="muted">Not recorded</i>}</span></div>)}</Card>;
}
