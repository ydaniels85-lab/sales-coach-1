import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, CheckCircle2, ClipboardList, FileUp, Handshake, RefreshCcw, Send, ShieldCheck, Sparkles, WalletCards } from 'lucide-react';
import { createManualLead, fetchHandoffs, fetchLeads, health, leadAction, uploadCreditReport } from './lib/api';

type Lead = any;
type Handoff = any;

const tabs = [
  { id: 'upload', label: 'Upload', icon: FileUp },
  { id: 'coach', label: 'Sales Coach', icon: Sparkles },
  { id: 'closing', label: 'Closing Desk', icon: Handshake },
  { id: 'admin', label: 'Admin Handoff', icon: ClipboardList },
];

function money(value: any) {
  const amount = Number(value || 0);
  return amount.toLocaleString('en-ZA', { style: 'currency', currency: 'ZAR' });
}

function badgeClass(value: string) {
  const low = (value || '').toLowerCase();
  if (low.includes('hot')) return 'badge hot';
  if (low.includes('warm')) return 'badge warm';
  if (low.includes('risk')) return 'badge risk';
  return 'badge';
}

export default function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [leads, setLeads] = useState<Lead[]>([]);
  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [selectedLeadId, setSelectedLeadId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [apiStatus, setApiStatus] = useState('checking');

  const selectedLead = useMemo(() => leads.find((lead) => lead.id === selectedLeadId) || leads[0], [leads, selectedLeadId]);

  async function reload() {
    setError('');
    try {
      const [leadData, handoffData] = await Promise.all([fetchLeads(), fetchHandoffs()]);
      setLeads(leadData.leads || []);
      setHandoffs(handoffData.handoffs || []);
      if (!selectedLeadId && leadData.leads?.[0]?.id) setSelectedLeadId(leadData.leads[0].id);
    } catch (err: any) {
      setError(err.message || 'Could not load data. Make sure backend is running on port 5000.');
    }
  }

  useEffect(() => {
    health()
      .then(() => setApiStatus('online'))
      .catch(() => setApiStatus('offline'))
      .finally(reload);
  }, []);

  async function runAction(action: string, payload: any = {}, successText = 'Done') {
    if (!selectedLead?.id) return;
    setLoading(true);
    setError('');
    setMessage('');
    try {
      await leadAction(selectedLead.id, action, payload);
      setMessage(successText);
      await reload();
    } catch (err: any) {
      setError(err.message || 'Action failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark">FT</div>
          <div>
            <h1>Fin-Tastic</h1>
            <p>Sales Coach</p>
          </div>
        </div>

        <div className="statusCard">
          <span className={apiStatus === 'online' ? 'dot online' : 'dot offline'} />
          API {apiStatus}
        </div>

        <nav>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button key={tab.id} className={activeTab === tab.id ? 'navBtn active' : 'navBtn'} onClick={() => setActiveTab(tab.id)}>
                <Icon size={18} />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">Consultant closing desk</p>
            <h2>{activeTab === 'upload' ? 'Upload & Parse Credit Report' : activeTab === 'coach' ? 'Sales Coach' : activeTab === 'closing' ? 'Close The Sale' : 'Admin Handoff Queue'}</h2>
          </div>
          <button className="ghostBtn" onClick={reload}><RefreshCcw size={16} /> Refresh</button>
        </header>

        {message && <div className="notice success"><CheckCircle2 size={18} /> {message}</div>}
        {error && <div className="notice error"><AlertCircle size={18} /> {error}</div>}

        {activeTab === 'upload' && <UploadScreen onUploaded={async (leadId) => { await reload(); setSelectedLeadId(leadId); setActiveTab('coach'); }} setError={setError} setMessage={setMessage} setLoading={setLoading} loading={loading} />}
        {activeTab === 'coach' && <CoachScreen leads={leads} selectedLead={selectedLead} setSelectedLeadId={setSelectedLeadId} />}
        {activeTab === 'closing' && <ClosingScreen selectedLead={selectedLead} loading={loading} runAction={runAction} />}
        {activeTab === 'admin' && <AdminScreen handoffs={handoffs} />}
      </main>
    </div>
  );
}

function UploadScreen({ onUploaded, setError, setMessage, setLoading, loading }: any) {
  const [file, setFile] = useState<File | null>(null);
  const [clientName, setClientName] = useState('');
  const [manual, setManual] = useState({ client_name: '', phone: '', email: '', credit_score: '', debt_review_flag: false, active_balance_total: '', arrears_total: '' });

  async function submitUpload(e: any) {
    e.preventDefault();
    if (!file) return setError('Choose a PDF credit report first.');
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const data = await uploadCreditReport(file, clientName);
      setMessage('Credit report parsed and lead created.');
      onUploaded(data.lead.id);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setLoading(false);
    }
  }

  async function submitManual(e: any) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const payload = { ...manual, credit_score: manual.credit_score === '' ? null : Number(manual.credit_score), active_balance_total: Number(manual.active_balance_total || 0), arrears_total: Number(manual.arrears_total || 0) };
      const data = await createManualLead(payload);
      setMessage('Manual lead created.');
      onUploaded(data.lead.id);
    } catch (err: any) {
      setError(err.message || 'Manual lead failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid two">
      <section className="card heroCard">
        <h3>Parse PDF Credit Report</h3>
        <p>Upload a Datanamix, XDS, TransUnion, Experian or Compuscan-style PDF. The backend extracts the client, accounts, balances, arrears and debt review signals.</p>
        <form onSubmit={submitUpload} className="stack">
          <label>Client name override, optional</label>
          <input value={clientName} onChange={(e) => setClientName(e.target.value)} placeholder="Example: Yusuf Daniels" />
          <label>PDF credit report</label>
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button className="primaryBtn" disabled={loading}>{loading ? 'Working...' : 'Upload & Coach Lead'}</button>
        </form>
      </section>

      <section className="card">
        <h3>Create Manual Test Lead</h3>
        <p>Use this when you want to test the sales coach without uploading a PDF.</p>
        <form onSubmit={submitManual} className="stack">
          <input placeholder="Client name" value={manual.client_name} onChange={(e) => setManual({ ...manual, client_name: e.target.value })} />
          <input placeholder="Phone" value={manual.phone} onChange={(e) => setManual({ ...manual, phone: e.target.value })} />
          <input placeholder="Email" value={manual.email} onChange={(e) => setManual({ ...manual, email: e.target.value })} />
          <input placeholder="Credit score, e.g. 0" value={manual.credit_score} onChange={(e) => setManual({ ...manual, credit_score: e.target.value })} />
          <input placeholder="Total active balance" value={manual.active_balance_total} onChange={(e) => setManual({ ...manual, active_balance_total: e.target.value })} />
          <input placeholder="Total arrears" value={manual.arrears_total} onChange={(e) => setManual({ ...manual, arrears_total: e.target.value })} />
          <label className="checkRow"><input type="checkbox" checked={manual.debt_review_flag} onChange={(e) => setManual({ ...manual, debt_review_flag: e.target.checked })} /> Debt review flag</label>
          <button className="secondaryBtn" disabled={loading}>Create Manual Lead</button>
        </form>
      </section>
    </div>
  );
}

function LeadPicker({ leads, selectedLead, setSelectedLeadId }: any) {
  return (
    <div className="leadPicker">
      <label>Selected lead</label>
      <select value={selectedLead?.id || ''} onChange={(e) => setSelectedLeadId(e.target.value)}>
        {leads.map((lead: any) => <option key={lead.id} value={lead.id}>{lead.client_name} — {lead.recommended_service}</option>)}
      </select>
    </div>
  );
}

function CoachScreen({ leads, selectedLead, setSelectedLeadId }: any) {
  if (!selectedLead) return <Empty title="No leads yet" text="Upload a credit report or create a manual lead first." />;
  const coach = selectedLead.sales_coach || {};
  const parsed = selectedLead.parsed || {};
  const totals = parsed.totals || {};
  const report = parsed.report || {};
  return (
    <div className="stack gapLarge">
      <LeadPicker leads={leads} selectedLead={selectedLead} setSelectedLeadId={setSelectedLeadId} />
      <section className="coachHero">
        <div>
          <p className="eyebrow">Recommended sale</p>
          <h3>{coach.service_recommendation}</h3>
          <p>{coach.reason}</p>
        </div>
        <span className={badgeClass(coach.lead_temperature)}>{coach.lead_temperature}</span>
      </section>

      <div className="statsGrid">
        <Stat label="Credit score" value={report.credit_score ?? 'Not found'} />
        <Stat label="Debt review" value={report.debt_review_flag ? 'Detected' : 'Not detected'} />
        <Stat label="Balance total" value={money(totals.active_balance_total)} />
        <Stat label="Suggested reduced" value={money(totals.reduced_total)} />
      </div>

      <div className="grid two">
        <section className="card scriptCard">
          <h3>Opening Script</h3>
          <p>{coach.opening_script}</p>
        </section>
        <section className="card scriptCard important">
          <h3>Mediation Explanation</h3>
          <p>{coach.mediation_explanation}</p>
        </section>
      </div>

      <div className="grid three">
        <ListCard title="Questions to ask" items={coach.key_questions || []} />
        <ListCard title="Next best actions" items={coach.next_best_actions || []} />
        <ListCard title="Compliance warnings" items={coach.compliance_warnings || []} warning />
      </div>

      <section className="card">
        <h3>Objection Handling</h3>
        <div className="objections">
          {(coach.objections || []).map((item: any, index: number) => (
            <div className="objection" key={index}>
              <strong>{item.objection}</strong>
              <p>{item.reply}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h3>Parsed Accounts</h3>
        <div className="tableWrap">
          <table>
            <thead>
              <tr><th>Creditor</th><th>Current</th><th>Arrears</th><th>Installment</th><th>Reduced</th><th>Status</th><th>Last Paid</th></tr>
            </thead>
            <tbody>
              {(parsed.accounts || []).map((acc: any) => (
                <tr key={acc.id}>
                  <td>{acc.creditor}{acc.furniture_account ? <span className="miniTag">Furniture</span> : null}</td>
                  <td>{money(acc.current_balance)}</td>
                  <td>{money(acc.arrears)}</td>
                  <td>{money(acc.monthly_installment)}</td>
                  <td>{money(acc.reduced_amount)}</td>
                  <td>{acc.status}</td>
                  <td>{acc.last_paid_date || '-'}</td>
                </tr>
              ))}
              {(!parsed.accounts || parsed.accounts.length === 0) && <tr><td colSpan={7}>No account rows extracted. This PDF may need OCR or parser tuning.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function ClosingScreen({ selectedLead, loading, runAction }: any) {
  const [amount, setAmount] = useState('');
  const [debitDay, setDebitDay] = useState('');
  const [note, setNote] = useState('Sale closed and ready for admin workflow/PDA processing.');
  if (!selectedLead) return <Empty title="No lead selected" text="Upload or select a lead first." />;
  const actions = selectedLead.actions || {};
  const suggested = selectedLead.sales_coach?.money_summary?.suggested_reduced_total || 0;

  return (
    <div className="grid closingGrid">
      <section className="card">
        <p className="eyebrow">Current lead</p>
        <h3>{selectedLead.client_name}</h3>
        <p>{selectedLead.recommended_service}</p>
        <div className="statusList">
          <StatusLine label="Signature link" done={!!actions.signature_link} />
          <StatusLine label="Document upload link" done={!!actions.document_link} />
          <StatusLine label="NuPay mandate" done={!!actions.nupay_mandate} />
          <StatusLine label="Sale closed" done={!!actions.sale_closed} />
          <StatusLine label="Admin handoff" done={!!actions.admin_handoff} />
        </div>
      </section>

      <section className="card actionPanel">
        <h3>Close the Sale</h3>
        <p className="muted">Use these buttons in order while speaking to the client.</p>
        <button className="actionBtn" disabled={loading} onClick={() => runAction('send-signature-link', {}, 'Signature link created.')}><Send size={18} /> Send Signature Link</button>
        <button className="actionBtn" disabled={loading} onClick={() => runAction('send-document-link', {}, 'Document upload link created.')}><FileUp size={18} /> Send Document Upload Link</button>
        <div className="mandateBox">
          <label>NuPay amount</label>
          <input placeholder={money(suggested)} value={amount} onChange={(e) => setAmount(e.target.value)} />
          <label>Debit day</label>
          <input placeholder="1 to 31" value={debitDay} onChange={(e) => setDebitDay(e.target.value)} />
          <button className="actionBtn" disabled={loading} onClick={() => runAction('send-nupay-mandate', { amount: Number(amount || suggested), debit_day: debitDay }, 'NuPay mandate placeholder created.')}><WalletCards size={18} /> Send NuPay Mandate</button>
        </div>
        <label>Consultant/Admin note</label>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} />
        <button className="primaryBtn" disabled={loading} onClick={() => runAction('close-sale', { note }, 'Sale marked as closed.')}><CheckCircle2 size={18} /> Mark Sale as Closed</button>
        <button className="secondaryBtn" disabled={loading} onClick={() => runAction('pass-to-admin', { note }, 'Lead passed to admin.')}><ShieldCheck size={18} /> Pass to Admin</button>
      </section>

      <section className="card scriptCard">
        <h3>Closing Script</h3>
        <p>{selectedLead.sales_coach?.closing_script}</p>
        <h4>Remember</h4>
        <p>Do not guarantee court removal. Say mediation supports the application by showing affordability, creditor engagement, and a plan for remaining balances.</p>
      </section>
    </div>
  );
}

function AdminScreen({ handoffs }: any) {
  if (!handoffs.length) return <Empty title="No admin handoffs yet" text="Once a consultant passes a sale to admin, it will appear here." />;
  return (
    <div className="stack">
      {handoffs.map((handoff: any) => (
        <section className="card handoff" key={handoff.id}>
          <div>
            <p className="eyebrow">{handoff.admin_stage}</p>
            <h3>{handoff.client_name}</h3>
            <p>{handoff.recommended_service}</p>
            <p className="muted">{handoff.handoff_note}</p>
          </div>
          <div className="handoffMeta">
            <span className={badgeClass(handoff.lead_temperature)}>{handoff.lead_temperature}</span>
            <span>{new Date(handoff.created_at).toLocaleString()}</span>
          </div>
        </section>
      ))}
    </div>
  );
}

function Stat({ label, value }: any) {
  return <section className="stat"><span>{label}</span><strong>{value}</strong></section>;
}

function ListCard({ title, items, warning = false }: any) {
  return <section className={warning ? 'card warningCard' : 'card'}><h3>{title}</h3><ul>{items.map((item: string, index: number) => <li key={index}>{item}</li>)}</ul></section>;
}

function StatusLine({ label, done }: any) {
  return <div className="statusLine"><span className={done ? 'statusIcon done' : 'statusIcon'}>{done ? '✓' : '•'}</span>{label}</div>;
}

function Empty({ title, text }: any) {
  return <section className="empty"><h3>{title}</h3><p>{text}</p></section>;
}
