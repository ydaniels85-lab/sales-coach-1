import { useState } from "react";
import { MockCase } from "../types";
import { SalesOpportunityPanel } from "./SalesOpportunityPanel";

const API_URL = "http://localhost:5000";

function getParsedPayload(data: any) {
  return data?.parsed_data || data?.parsedReport || data?.report || data?.result || data?.data || data?.client || data;
}

export function UploadView({ onImported }: { onImported: (lead: MockCase) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [parsedReport, setParsedReport] = useState<any>(null);

  const upload = async () => {
    if (!file) { setMessage("Choose a PDF first."); return; }
    setLoading(true); setMessage(""); setParsedReport(null);
    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch(`${API_URL}/upload`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.error || "Upload failed");

      const c = data.client;
      setParsedReport(getParsedPayload(data));

      onImported({
        id: c.id,
        tenantId: "tenant-liberty",
        clientName: c.primary_applicant?.full_name || c.id,
        title: `${c.primary_applicant?.full_name || c.id} Credit Report`,
        subtitle: c.workflow_stage,
        totalDebt: c.included_totals?.included_balance || 0,
        currentInstallment: c.current_instalment || 0,
        debtReviewFlag: !!c.summary?.debt_review,
        selectedService: c.service,
        accounts: (c.accounts || []).map((a: any) => ({
          creditor: a.creditor,
          account_number: a.account_number,
          account_type: a.account_type,
          current_balance: a.current_balance,
          monthly_instalment: a.monthly_instalment,
          arrears: a.arrears,
          reduced_amount: a.reduced_amount,
          status: a.status,
          included: a.included,
          is_furniture: a.is_furniture
        })),
        description: `Parsed by ${data.parsed_data?.bureau || "Unknown"} parser`
      });

      setMessage("Credit report uploaded and client created.");
    } catch (e: any) {
      setMessage(e.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return <>
    <div className="card">
      <h2>Credit Report Upload</h2>
      <p className="muted">Upload a PDF report to the Flask parser backend. No AI is used in this restored version.</p>
      <div className="drop">
        <input type="file" accept="application/pdf" onChange={e => setFile(e.target.files?.[0] || null)} />
        <p>{file?.name || "No PDF selected"}</p>
      </div>
      <br/>
      <button className="btn green" onClick={upload} disabled={loading}>{loading ? "Analyzing..." : "Analyze Report"}</button>
      {message && <p className="muted">{message}</p>}
      <p className="muted">Endpoint: {API_URL}/upload</p>
    </div>

    {parsedReport && <SalesOpportunityPanel parsedReport={parsedReport} />}
  </>;
}
