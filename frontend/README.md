# Frontend — React / JSX / HTML / CSS

Install with `npm install`, run with `npm run dev`, and open http://127.0.0.1:5173. Start the Python backend separately on port 8000. Build with `npm run build`.

| Location | What to edit |
| --- | --- |
| `index.html` | HTML document and React root |
| `src/main.jsx` | React startup and top-level providers |
| `src/App.jsx` | Page URLs and routing |
| `src/pages/` | Individual page implementations |
| `src/components/layout/` | Sidebar and top navigation |
| `src/components/dashboard/` | Statistics, cascades, decision chart and completeness |
| `src/components/patients/` | Patient table, registration, profile, overview and source fields |
| `src/components/lab/` | Laboratory entry form |
| `src/components/risk/` | Patient scoring explanation |
| `src/components/discussion/` | Patient discussion thread |
| `src/components/decisions/` | Approval and implementation forms |
| `src/components/settings/` | CSV import and audit log |
| `src/services/` | HTTP calls to matching backend routes |
| `src/contexts/` | Authentication and shared workspace state |
| `src/styles/global.css` | Responsive styling |
| `src/utils/` | Formatting and record filters |
| `vite.config.js` | Local server and `/api` proxy |

No patient-data mutations happen only in browser storage: forms call the backend, which persists and audits changes. The source selector keeps synthetic, original and manually registered data distinguishable.
