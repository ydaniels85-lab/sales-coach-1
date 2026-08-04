import { useState, type ReactNode } from "react";
import { buildSalesOpportunity } from "../services/salesOpportunityEngine";

export function SalesOpportunityPanel({ parsedReport }: { parsedReport: any }) {
  const [copied, setCopied] = useState(false);
  const opportunity = buildSalesOpportunity(parsedReport);
  const priorityBadge = opportunity.priority === "High" ? "badge red" : opportunity.priority === "Low" ? "badge green" : "badge";

  const copyScript = async () => {
    const text = ["SALES OPPORTUNITY", `Best Service: ${opportunity.recommendedService}`, `Sales Angle: ${opportunity.salesAngle}`, "Pain Points:", ...opportunity.painPoints.map(i => `- ${i}`), "Accounts to Mention:", ...opportunity.accountsToMention.map(i => `- ${i}`), "Questions:", ...opportunity.questionsToAsk.map((i,n) => `${n+1}. ${i}`), "Next Actions:", ...opportunity.nextBestActions.map((i,n) => `${n+1}. ${i}`), `Compliance: ${opportunity.complianceNote}`].join("
");
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { alert("Could not copy script."); }
  };

  return <div className="card sales-box">
    <div style={{display:"flex", justifyContent:"space-between", gap:12, flexWrap:"wrap"}}>
      <div><h2>Sales Opportunity Coach</h2><p className="muted">Rule-based sales advice generated from the parsed credit report.</p></div>
      <div style={{display:"flex", gap:8, alignItems:"center", flexWrap:"wrap"}}><span className={priorityBadge}>{opportunity.priority} Priority</span><span className="badge green">{opportunity.confidence}% Match</span><button className="btn secondary" onClick={copyScript}>{copied ? "Copied" : "Copy Script"}</button></div>
    </div>
    <div className="sales-banner"><b>Best Service to Sell:</b> {opportunity.recommendedService}</div>
    <div className="sales-grid"><Section title="Main Sales Angle"><p>{opportunity.salesAngle}</p></Section><List title="Pain Points Found" items={opportunity.painPoints} empty="No major pain points detected." /></div>
    <div className="sales-grid"><List title="Accounts to Mention" items={opportunity.accountsToMention} empty="No account highlights available." /><List title="Questions the Consultant Must Ask" items={opportunity.questionsToAsk} empty="No questions available." ordered /></div>
    <List title="Next Best Actions" items={opportunity.nextBestActions} empty="No next actions available." />
    <div className="sales-warning"><b>Compliance Note</b><p>{opportunity.complianceNote}</p></div>
  </div>;
}
export default SalesOpportunityPanel;
function Section({ title, children }: { title: string; children: ReactNode }) { return <div className="sales-section"><h3>{title}</h3>{children}</div>; }
function List({ title, items, empty, ordered = false }: { title: string; items: string[]; empty: string; ordered?: boolean }) { return <Section title={title}>{items.length === 0 ? <p className="muted">{empty}</p> : ordered ? <ol>{items.map((i,n) => <li key={n}>{i}</li>)}</ol> : <ul>{items.map((i,n) => <li key={n}>{i}</li>)}</ul>}</Section>; }
