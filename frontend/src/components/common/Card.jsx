export default function Card({ title, subtitle, action, children, className = '' }) {
  return <section className={`card ${className}`}>
    {title && <div className="card-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>}
    <div className="card-body">{children}</div>
  </section>;
}
