export default function PageHeader({ title, description, action }) {
  return <div className="heading"><div><div className="eyebrow">Surveillance workspace</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
