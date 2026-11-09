export default function Feedback({ error, success }) {
  return <>{error && <p role="alert" className="notice error">{error}</p>}{success && <p role="status" className="notice info">{success}</p>}</>;
}
