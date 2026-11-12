import ModelReport from '../components/settings/ModelReport.jsx';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import Card from '../components/common/Card.jsx';
import RiskChart from '../components/dashboard/RiskChart.jsx';
import EligibilityChart from '../components/dashboard/EligibilityChart.jsx';
import PatientList from '../components/patients/PatientList.jsx';

export default function RiskAssessmentPage() {
  const { visiblePatients: patients } = useWorkspace();
  const flagged = patients.filter(p => p.risk?.flagged).length;
  const due = patients.filter(p => p.eligibility?.status === 'eligible' && !p.referred_at).length;
  return <>
    <PageHeader title="Risk assessment" description={`${flagged} patient(s) flagged at high risk of drug resistance · ${due} eligible for a DR test and not yet requested.`} />
    <div className="grid-half"><RiskChart patients={patients} /><EligibilityChart patients={patients} /></div>
    <div className="grid-half">
      <Card title="Risk points score" subtitle="Original project algorithm (prototype 2.1)">
        <table className="rule-table"><thead><tr><th>Input</th><th>Points</th></tr></thead><tbody>
          <tr><td>Viral load ≥1000 copies/mL</td><td>60</td></tr><tr><td>Viral load 200–999</td><td>30</td></tr>
          <tr><td>Adherence below 85%</td><td>60</td></tr><tr><td>Adherence 85–99%</td><td>30</td></tr>
          <tr><td>Third-line regimen</td><td>60</td></tr><tr><td>Second-line regimen</td><td>30</td></tr>
        </tbody></table>
        <p>Low 0 · Intermediate 30–59 · High 60–180 (flagged). 60 known points is enough for High even if another input is missing.</p>
        <p className="tiny muted">Every patient in the original dataset was referred for DR testing with a viral load of 1000 or more, so all of them score High. The flag shows which patients need attention; the eligibility criteria and the laboratory request decide who is tested.</p>
      </Card>
      <Card title="DR-test eligibility (MoH and WHO)" subtitle="The score prioritises; these criteria decide who is tested">
        <table className="rule-table"><tbody>
          <tr><td>All lines</td><td>2 consecutive VL ≥1000 copies/mL, at least 3 months apart, after 3 consecutive good IAC sessions (≥95%); on ART ≥6 months.</td></tr>
          <tr><td>Children &lt;15 on NNRTI first line</td><td>A single VL ≥1000: switch without waiting for IAC.</td></tr>
          <tr><td>Other indications</td><td>Infant of a mother failing treatment, clinical failure or committee request: clinician referral with a written reason.</td></tr>
        </tbody></table>
        <p className="tiny muted">A single VL ≥1000 is not enough on its own (except children on NNRTIs): it starts intensive adherence counselling. Many people re-suppress after IAC, especially on DTG. Sources: MoH presentation (April 2024) slide 65; Job Aid (2020) slides 66, 159–161; WHO 2021 consolidated guidelines.</p>
      </Card>
    </div>
    <ModelReport />
    <PatientList patients={patients} tab="risk" />
  </>;
}
