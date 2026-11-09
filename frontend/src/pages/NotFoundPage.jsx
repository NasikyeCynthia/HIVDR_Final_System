import { Link } from 'react-router-dom';
import PageHeader from '../components/common/PageHeader.jsx';
export default function NotFoundPage() {
  return <><PageHeader title="Page not found" description="Choose a page from the sidebar or return to the dashboard." /><Link className="btn" to="/dashboard">Go to dashboard</Link></>;
}
