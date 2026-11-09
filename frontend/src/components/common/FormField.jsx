export default function FormField({ label, name, children, full = false, ...props }) {
  return <div className={`field ${full ? 'full' : ''}`}>
    <label htmlFor={name}>{label}</label>
    {children || <input id={name} name={name} {...props} />}
  </div>;
}
