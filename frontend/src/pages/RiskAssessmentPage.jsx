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
      <Card title="Risk points score" subtitle="Who is most likely to have resistance — used to prioritise">
        <table className="rule-table"><thead><tr><th>Factor</th><th>Points</th></tr></thead><tbody>
          <tr><td>Second- or third-line regimen</td><td>3</td></tr><tr><td>NNRTI-based regimen (EFV/NVP)</td><td>3</td></tr>
          <tr><td>Child under 10 years</td><td>3</td></tr><tr><td>Adolescent 10–19 years</td><td>1</td></tr>
          <tr><td>On ART 5 years or more</td><td>1</td></tr><tr><td>Three or more consecutive VL ≥1000</td><td>1</td></tr>
          <tr><td>Previously exposed to both AZT and ABC</td><td>1</td></tr>
          <tr><td>Still ≥1000 after 3 good IAC sessions (guideline)</td><td>2</td></tr><tr><td>Less than 1-log drop after IAC (guideline)</td><td>1</td></tr>
          <tr><td>Poor adherence on an NNRTI regimen (guideline)</td><td>1</td></tr>
        </tbody></table>
        <p>Only patients with VL ≥1000 copies/mL are scored. Low 0–2 (≈41% had resistance) · Moderate 3–4 (≈67%) · High 5+ (≈78%, flagged)</p>
        <p className="tiny muted">Weights come from 9,934 CPHL records with full resistance results and agree with published African cohorts. AUROC 0.71 on held-out facilities, close to the machine-learning model below (0.72).</p>
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
