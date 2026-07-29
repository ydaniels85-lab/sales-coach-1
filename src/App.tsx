
import React, { useMemo, useState } from "react";

type Role = "consultant" | "admin" | "manager";
type View = "dashboard" | "consultant" | "admin";
type Service = "debt_review" | "debt_review_removal" | "debt_mediation" | "double_sale";
type StepStatus = "not_started" | "in_progress" | "blocked" | "done";

type User = { id: string; name: string; role: Role; team: string };
type Account = {
  id: string;
  creditor: string;
  accountNo: string;
  type: string;
  openingBalance: number;
  currentBalance: number;
  arrears: number;
  monthlyInstallment: number;
  reducedInstallment: number;
  monthsInArrears: number;
  lastPaid: string;
  openDate: string;
  status: string;
  include: boolean;
  furniture: boolean;
};
type Doc = {
  id: string;
  name: string;
  category: string;
  required: boolean;
  received: boolean;
  verified: boolean;
  receivedAt?: string;
  fileName?: string;
  note?: string;
};
type LinkStatus = {
  url: string;
  token: string;
  sentAt: string;
  sentVia: string;
  sentTo: string;
  signatureReceived: boolean;
  docsReceived: boolean;
  signedName?: string;
  signedAt?: string;
};
type Mandate = {
  status: "not_sent" | "sent" | "signed" | "failed";
  ref?: string;
  sentAt?: string;
  signedAt?: string;
};
type GeneratedDoc = {
  id: string;
  type: "17.1" | "17.2" | "17.3" | "19" | "court_pack" | "mandate" | "client_link";
  title: string;
  createdAt: string;
  status: "draft" | "generated" | "sent" | "signed";
  content: string;
};
type Client = {
  id: string;
  fullName: string;
  idNumber: string;
  applicationType: "single" | "joint";
  phone: string;
  whatsapp: string;
  email: string;
  address: string;
  employer: string;
  occupation: string;
  dateEmployed: string;
  salaryFrequency: string;
  grossSalary: number;
  nettSalary: number;
  bankName: string;
  accountHolder: string;
  accountType: string;
  branchCode: string;
  accountNumber: string;
  spouseName: string;
  spouseId: string;
  spousePhone: string;
  spouseEmail: string;
  creditScore: number;
  confirmedDebtReview: boolean;
  homeLoan: boolean;
  vehicleFinance: boolean;
  reportName: string;
  uploadedAt: string;
  accounts: Account[];
  selectedService: Service;
  coachAdvice: string;
  coachWarnings: string[];
  docs: Doc[];
  generatedDocs: GeneratedDoc[];
  oneLink?: LinkStatus;
  mandate: Mandate;
  forms: Record<string, StepStatus>;
  courtPack: Record<string, boolean>;
  bureau: string;
  parseConfidence: number;
  parseWarnings: string[];
  adminNotes: string;
};
type AdminCase = {
  id: string;
  clientId: string;
  consultant: string;
  status: string;
  priority: string;
  createdAt: string;
  stepStatus: Record<string, StepStatus>;
  audit: { at: string; user: string; action: string; note?: string }[];
};
type ParsedUpload = {
  success?: boolean;
  filename?: string;
  parsed?: {
    bureau?: string;
    confidence?: number;
    warnings?: string[];
    client?: Partial<Client>;
    accounts?: Partial<Account>[];
  };
  error?: string;
};

type Creditor = { name: string; department: string; email: string; phone: string; process: string; nca: string[] };

const USERS: User[] = [
  { id: "u1", name: "Sales Consultant", role: "consultant", team: "Sales" },
  { id: "u2", name: "Admin Team", role: "admin", team: "Admin" },
  { id: "u3", name: "Back Office Manager", role: "manager", team: "Back Office" }
];

const CLIENTS_KEY = "ft_clients_v5";
const CASES_KEY = "ft_cases_v5";
const courtItems = ["Notice of Motion", "Founding Affidavit", "Latest Credit Report", "Debt Review Form History", "Paid-up / Balance Proof", "Income and Expense Proof", "Draft Court Order"];
const formList = ["17.1", "17.2", "17.3", "19"] as const;

const creditors: Creditor[] = [
  { name: "ABSA", department: "Debt Review / Collections", email: "verify-before-use@absa.example", phone: "Verify", process: "Send statutory notice / COB request to verified debt review department, then log proof of delivery.", nca: ["Verify correct credit provider details before sending", "Attach correct client authority/statutory form", "Log sent date and response date"] },
  { name: "Capitec", department: "Debt Review", email: "verify-before-use@capitec.example", phone: "Verify", process: "Use verified debt review channel for Form 17.1, COB and proposal communication.", nca: ["Confirm account number", "Keep delivery proof", "Capture COB response"] },
  { name: "FNB", department: "Debt Counselling", email: "verify-before-use@fnb.example", phone: "Verify", process: "Send debt counselling documents to verified creditor channel only.", nca: ["No employer disclosure", "Use client consent", "Track creditor response"] },
  { name: "Nedbank", department: "Debt Review", email: "verify-before-use@nedbank.example", phone: "Verify", process: "Send statutory forms, COB requests and proposals to verified debt review inbox.", nca: ["Verify legal entity", "Use correct reference", "Follow up overdue COB"] },
  { name: "Standard Bank", department: "Debt Review", email: "verify-before-use@standardbank.example", phone: "Verify", process: "Send notices and COB requests through verified debt review process.", nca: ["Check account number", "Keep proof", "Update proposal status"] },
  { name: "Unknown Creditor", department: "Manual Review", email: "", phone: "", process: "Do not auto-send. Admin must verify the creditor's official debt review contact first.", nca: ["Verify creditor identity", "Verify department details", "Record source of contact details"] }
];

const workflowByService: Record<Service, { id: string; title: string; description: string }[]> = {
  debt_review: [
    { id: "docs", title: "Docs + Signature Review", description: "Verify client signature, Form 16, ID, income, bank statements, proof of address and joint documents if applicable." },
    { id: "form17_1", title: "Form 17.1", description: "Generate and send 17.1 to credit providers and bureaus. Log delivery proof and COB requests." },
    { id: "cob", title: "COB + Creditor Work", description: "Capture COB balances, arrears, monthly installments and creditor responses." },
    { id: "form17_2", title: "Form 17.2", description: "Prepare 17.2 accepted/rejected decision workflow after assessment." },
    { id: "form17_3", title: "Form 17.3", description: "Generate where route requires rejection/termination/cancellation workflow handling." },
    { id: "pda", title: "PDA API", description: "Submit verified payment and mandate details to PDA/API workflow." },
    { id: "form19", title: "Form 19", description: "Generate clearance certificate only where client qualifies." }
  ],
  debt_review_removal: [
    { id: "docs", title: "Docs + Signature Review", description: "Verify removal mandate, signed authority, ID, report and proof documents." },
    { id: "route", title: "Removal Route Decision", description: "Choose bureau correction, paid-up clearance, NCT or court route." },
    { id: "creditors", title: "Creditor Clearance", description: "Verify balances, paid-up letters and settlement proof." },
    { id: "court", title: "Court Removal Pack", description: "Compile Notice of Motion, affidavit, form history, proof docs and draft order." },
    { id: "pda", title: "Payment / PDA API", description: "Track R7,000 DRR fee, payment plan and mandate/PDA status." },
    { id: "bureau", title: "Bureau Follow-up", description: "Track final bureau/NCR update after successful route." }
  ],
  debt_mediation: [
    { id: "docs", title: "Docs + Signature Review", description: "Verify signed mediation authority, ID, income, banking and documents." },
    { id: "creditors", title: "Creditor Proposals", description: "Use creditor directory to send proposals and track accept/reject/counteroffer." },
    { id: "pda", title: "NuPay / PDA API", description: "Submit debit order mandate and payment plan to NuPay/PDA workflow." },
    { id: "monitor", title: "Active Monitoring", description: "Monitor payments, missed payments and creditor feedback." }
  ],
  double_sale: [
    { id: "docs", title: "Docs + Signature Review", description: "Verify docs and signature for both DRR and mediation routes." },
    { id: "removal", title: "Removal Route", description: "Process bureau/NCT/court removal route." },
    { id: "mediation", title: "Mediation Route", description: "Prepare proposals for remaining active balances." },
    { id: "creditors", title: "Creditor Workflow", description: "Track COB/proposal process per creditor." },
    { id: "court", title: "Court Pack", description: "Compile removal court pack where required." },
    { id: "pda", title: "PDA / NuPay API", description: "Submit mandate, allocation and payment details." }
  ]
};

function isAdmin(user: User) { return user.role === "admin" || user.role === "manager"; }
function isConsultant(user: User) { return user.role === "consultant"; }
function pretty(v?: string) { return String(v || "-").replace(/_/g, " ").replace(/\b\w/g, s => s.toUpperCase()); }
function serviceLabel(s: Service) { return ({ debt_review: "Debt Review", debt_review_removal: "Debt Review Removal", debt_mediation: "Debt Mediation", double_sale: "DRR + Mediation" } as Record<Service, string>)[s]; }
function money(n?: number) { return Number(n || 0).toLocaleString("en-ZA", { style: "currency", currency: "ZAR", maximumFractionDigits: 0 }); }
function now() { return new Date().toISOString(); }
function load<T>(key: string, fallback: T): T { try { const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; } catch { return fallback; } }
function saveLocal<T>(key: string, data: T) { localStorage.setItem(key, JSON.stringify(data)); }
function clientDisplayName(c?: Client) { return c?.fullName?.trim() || "Name not parsed — capture manually"; }
function totals(accounts: Account[]) {
  const inc = accounts.filter(a => a.include);
  return { count: inc.length, balance: inc.reduce((s,a)=>s+Number(a.currentBalance||0),0), arrears: inc.reduce((s,a)=>s+Number(a.arrears||0),0), monthly: inc.reduce((s,a)=>s+Number(a.monthlyInstallment||0),0), reduced: inc.reduce((s,a)=>s+Number(a.reducedInstallment||0),0) };
}
function recommended(c: Client): { service: Service; advice: string; warnings: string[] } {
  const t = totals(c.accounts);
  const warnings: string[] = [];
  if (!c.fullName) warnings.push("Client name is missing. Capture it before sending any link or statutory document.");
  if (!c.idNumber) warnings.push("ID number is missing. Admin cannot complete statutory documents safely without it.");
  if (!c.accounts.length) warnings.push("No accounts were parsed. Upload a clearer report or capture accounts manually.");

  if (c.confirmedDebtReview && t.balance > 0) return { service: "double_sale", advice: "Client is confirmed under debt review and still has active balances. Recommend DRR + Mediation: removal route for the listing/status plus mediation for active balances.", warnings };
  if (c.confirmedDebtReview) return { service: "debt_review_removal", advice: "Client is confirmed under debt review. Recommend Debt Review Removal. Admin must verify listing, paid-up position and whether bureau, NCT or court route applies.", warnings };
  if (!c.confirmedDebtReview && (c.homeLoan || c.vehicleFinance)) return { service: "debt_review", advice: "Client has home loan or vehicle finance asset exposure and is not confirmed under debt review. Recommend Debt Review where eligible and compliant because it may protect important assets.", warnings };
  return { service: "debt_mediation", advice: "No confirmed debt review listing and no home/vehicle asset trigger. Recommend Debt Mediation only. Do not recommend Debt Review Removal unless debt-review status is confirmed.", warnings };
}
function requiredDocs(c: Client, service: Service): Doc[] {
  const base: Doc[] = [
    { id: "id", name: "ID Copy", category: "Identity", required: true, received: false, verified: false },
    { id: "address", name: "Proof of Address", category: "Address", required: true, received: false, verified: false },
    { id: "income", name: "Payslip / Proof of Income", category: "Income", required: true, received: false, verified: false },
    { id: "bank", name: "Bank Statements", category: "Banking", required: true, received: false, verified: false },
    { id: "popia", name: "Signed Authority / POPIA Consent", category: "Signature", required: true, received: false, verified: false },
    { id: "mandate", name: "NuPay Debit Order Mandate", category: "Mandate", required: true, received: false, verified: false }
  ];
  if (c.applicationType === "joint") {
    base.push({ id: "spouse-id", name: "Spouse / Co-applicant ID", category: "Identity", required: true, received: false, verified: false });
    base.push({ id: "marriage", name: "Marriage / COP Document", category: "Joint Application", required: true, received: false, verified: false });
  }
  if (service === "debt_review" || service === "double_sale") {
    base.push({ id: "form16", name: "Form 16", category: "Statutory", required: true, received: false, verified: false });
    base.push({ id: "budget", name: "Income & Expense Budget", category: "Affordability", required: true, received: false, verified: false });
  }
  if (service === "debt_review_removal" || service === "double_sale") {
    base.push({ id: "removal-mandate", name: "Debt Review Removal Mandate", category: "Removal", required: true, received: false, verified: false });
    base.push({ id: "paid-up", name: "Paid-up Letters / Settlement Proof", category: "Removal", required: false, received: false, verified: false });
    base.push({ id: "court-support", name: "Court Removal Support Documents", category: "Court", required: true, received: false, verified: false });
  }
  return base;
}
function normaliseAccount(raw: Partial<Account>, index: number): Account {
  const creditor = String((raw as any).creditor || (raw as any).creditorName || "").trim();
  const type = String(raw.type || "").trim();
  return {
    id: raw.id || `acc-${index + 1}-${Date.now()}`,
    creditor,
    accountNo: String((raw as any).accountNo || (raw as any).accountNumber || "").trim(),
    type,
    openingBalance: Number(raw.openingBalance || 0),
    currentBalance: Number(raw.currentBalance || 0),
    arrears: Number(raw.arrears || 0),
    monthlyInstallment: Number(raw.monthlyInstallment || 0),
    reducedInstallment: Number(raw.reducedInstallment || Math.round(Number(raw.monthlyInstallment || 0) * 0.5)),
    monthsInArrears: Number(raw.monthsInArrears || 0),
    lastPaid: String((raw as any).lastPaid || ""),
    openDate: String(raw.openDate || ""),
    status: String(raw.status || ""),
    include: raw.include !== false,
    furniture: Boolean(raw.furniture || /furniture|bradlows|russells|beares|lewis|ok furniture|fair price/i.test(`${creditor} ${type}`))
  };
}
function emptyClient(fileName = "Manual capture"): Client {
  const c: Client = {
    id: `client-${Date.now()}`,
    fullName: "", idNumber: "", applicationType: "single", phone: "", whatsapp: "", email: "", address: "", employer: "", occupation: "", dateEmployed: "", salaryFrequency: "Monthly", grossSalary: 0, nettSalary: 0, bankName: "", accountHolder: "", accountType: "", branchCode: "", accountNumber: "", spouseName: "", spouseId: "", spousePhone: "", spouseEmail: "", creditScore: 0, confirmedDebtReview: false, homeLoan: false, vehicleFinance: false, reportName: fileName, uploadedAt: now(), accounts: [], selectedService: "debt_mediation", coachAdvice: "", coachWarnings: [], docs: [], generatedDocs: [], mandate: { status: "not_sent" }, forms: { "17.1": "not_started", "17.2": "not_started", "17.3": "not_started", "19": "not_started" }, courtPack: Object.fromEntries(courtItems.map(i => [i, false])), bureau: "Unknown", parseConfidence: 0, parseWarnings: [], adminNotes: ""
  };
  const rec = recommended(c);
  c.selectedService = rec.service;
  c.coachAdvice = rec.advice;
  c.coachWarnings = rec.warnings;
  c.docs = requiredDocs(c, c.selectedService);
  return c;
}
function newClientFromParse(fileName: string, upload?: ParsedUpload): Client {
  const c = emptyClient(fileName);
  const parsed = upload?.parsed;
  const parsedClient = parsed?.client || {};
  const accounts = (Array.isArray(parsed?.accounts) ? parsed!.accounts! : []).map(normaliseAccount).filter(a => a.creditor || a.accountNo || a.currentBalance || a.monthlyInstallment);

  Object.assign(c, {
    fullName: String(parsedClient.fullName || "").trim(),
    idNumber: String(parsedClient.idNumber || "").trim(),
    applicationType: (parsedClient.applicationType as "single" | "joint") || "single",
    phone: String(parsedClient.phone || "").trim(),
    whatsapp: String(parsedClient.whatsapp || parsedClient.phone || "").trim(),
    email: String(parsedClient.email || "").trim(),
    address: String((parsedClient as any).address || "").trim(),
    employer: String(parsedClient.employer || "").trim(),
    occupation: String(parsedClient.occupation || "").trim(),
    dateEmployed: String(parsedClient.dateEmployed || "").trim(),
    salaryFrequency: String(parsedClient.salaryFrequency || "Monthly"),
    grossSalary: Number(parsedClient.grossSalary || 0),
    nettSalary: Number(parsedClient.nettSalary || 0),
    bankName: String(parsedClient.bankName || "").trim(),
    accountHolder: String(parsedClient.accountHolder || parsedClient.fullName || "").trim(),
    accountType: String(parsedClient.accountType || "").trim(),
    branchCode: String(parsedClient.branchCode || "").trim(),
    accountNumber: String(parsedClient.accountNumber || "").trim(),
    spouseName: String(parsedClient.spouseName || "").trim(),
    spouseId: String(parsedClient.spouseId || "").trim(),
    spousePhone: String(parsedClient.spousePhone || "").trim(),
    spouseEmail: String(parsedClient.spouseEmail || "").trim(),
    creditScore: Number(parsedClient.creditScore || 0),
    confirmedDebtReview: Boolean(parsedClient.confirmedDebtReview),
    homeLoan: Boolean(parsedClient.homeLoan),
    vehicleFinance: Boolean(parsedClient.vehicleFinance),
    bureau: parsed?.bureau || "Unknown",
    parseConfidence: Number(parsed?.confidence || 0),
    parseWarnings: Array.isArray(parsed?.warnings) ? [...parsed!.warnings!] : [],
    accounts
  });

  if (!c.fullName) c.parseWarnings.push("Client name was not confidently parsed. Capture it manually in the Client Details panel.");
  if (!c.idNumber) c.parseWarnings.push("ID number was not confidently parsed. Capture it manually before statutory docs.");
  if (!accounts.length) c.parseWarnings.push("No accounts were imported. Check /api/debug/last-parse or capture accounts manually.");
  const rec = recommended(c);
  c.selectedService = rec.service;
  c.coachAdvice = rec.advice;
  c.coachWarnings = rec.warnings;
  c.docs = requiredDocs(c, c.selectedService);
  return c;
}
function applyRecommendation(c: Client, service?: Service): Client {
  const chosen = service || recommended(c).service;
  const rec = recommended({ ...c, selectedService: chosen });
  return { ...c, selectedService: chosen, coachAdvice: chosen === rec.service ? rec.advice : `Consultant manually selected ${serviceLabel(chosen)}. Admin must verify route before processing.`, coachWarnings: rec.warnings, docs: mergeDocs(c.docs, requiredDocs(c, chosen)) };
}
function mergeDocs(oldDocs: Doc[], newDocs: Doc[]) {
  return newDocs.map(next => {
    const old = oldDocs.find(d => d.id === next.id);
    return old ? { ...next, received: old.received, verified: old.verified, receivedAt: old.receivedAt, fileName: old.fileName, note: old.note } : next;
  });
}
function documentContent(client: Client, type: GeneratedDoc["type"]): string {
  const t = totals(client.accounts);
  if (type === "17.1") return `FORM 17.1 - NOTICE OF APPLICATION FOR DEBT REVIEW\n\nClient: ${clientDisplayName(client)}\nID: ${client.idNumber || "[capture ID]"}\nApplication: ${pretty(client.applicationType)}\nService: ${serviceLabel(client.selectedService)}\nCredit Bureau: ${client.bureau}\n\nCredit Providers / Accounts:\n${client.accounts.map(a => `- ${a.creditor || "Unknown Creditor"} | ${a.accountNo || "No account number"} | Balance ${money(a.currentBalance)} | Arrears ${money(a.arrears)}`).join("\n") || "[No accounts captured]"}\n\nAdmin checklist:\n- Send to verified credit provider contacts only.\n- Send to bureaus where applicable.\n- Log proof of delivery and COB request date.\n`;
  if (type === "17.2") return `FORM 17.2 - DEBT REVIEW ASSESSMENT OUTCOME\n\nClient: ${clientDisplayName(client)}\nID: ${client.idNumber || "[capture ID]"}\nTotal included balance: ${money(t.balance)}\nTotal arrears: ${money(t.arrears)}\nCurrent installment total: ${money(t.monthly)}\nReduced proposal total: ${money(t.reduced)}\n\nOutcome notes:\n[Admin / Debt Counsellor to complete assessment outcome and decision.]\n`;
  if (type === "17.3") return `FORM 17.3 - ROUTE SPECIFIC FOLLOW-UP\n\nClient: ${clientDisplayName(client)}\nID: ${client.idNumber || "[capture ID]"}\nRoute: ${serviceLabel(client.selectedService)}\n\nUse this document only where the client route and status require Form 17.3 handling.\n\nAdmin notes:\n${client.adminNotes || "[No admin notes yet]"}\n`;
  if (type === "19") return `FORM 19 - CLEARANCE CERTIFICATE WORKFLOW\n\nClient: ${clientDisplayName(client)}\nID: ${client.idNumber || "[capture ID]"}\n\nBefore issue, admin must verify that the client qualifies for clearance and that paid-up / settlement proof is complete.\n\nCreditor proof summary:\n${client.accounts.map(a => `- ${a.creditor}: ${a.status || "status not captured"}`).join("\n") || "[No creditor proof captured]"}\n`;
  if (type === "court_pack") return `COURT / REMOVAL PACK SUMMARY\n\nClient: ${clientDisplayName(client)}\nID: ${client.idNumber || "[capture ID]"}\nService: ${serviceLabel(client.selectedService)}\n\nPack items:\n${courtItems.map(item => `- ${item}: ${client.courtPack[item] ? "Ready" : "Outstanding"}`).join("\n")}\n\nDraft order and affidavits must be reviewed by the relevant legal/admin team before filing.\n`;
  if (type === "mandate") return `NUPAY DEBIT ORDER MANDATE\n\nClient: ${clientDisplayName(client)}\nAccount holder: ${client.accountHolder || clientDisplayName(client)}\nBank: ${client.bankName || "[capture bank]"}\nAccount type: ${client.accountType || "[capture type]"}\nAccount number: ${client.accountNumber || "[capture account number]"}\nBranch code: ${client.branchCode || "[capture branch]"}\nReference: ${client.mandate.ref || "[not sent]"}\nStatus: ${pretty(client.mandate.status)}\n`;
  return `CLIENT PORTAL LINK\n\nClient: ${clientDisplayName(client)}\nLink: ${client.oneLink?.url || "[not generated]"}\nSignature: ${client.oneLink?.signatureReceived ? "Received" : "Pending"}\nDocuments: ${client.oneLink?.docsReceived ? "Received" : "Pending"}\n`;
}
function makeGeneratedDoc(client: Client, type: GeneratedDoc["type"]): GeneratedDoc {
  const titles: Record<GeneratedDoc["type"], string> = { "17.1": "Form 17.1", "17.2": "Form 17.2", "17.3": "Form 17.3", "19": "Form 19", court_pack: "Court / Removal Pack", mandate: "NuPay Mandate", client_link: "Client One Link Record" };
  return { id: `doc-${type}-${Date.now()}`, type, title: titles[type], createdAt: now(), status: "generated", content: documentContent(client, type) };
}
function addOrReplaceGeneratedDoc(client: Client, type: GeneratedDoc["type"]): Client {
  const doc = makeGeneratedDoc(client, type);
  const forms = formList.includes(type as any) ? { ...client.forms, [type]: "in_progress" as StepStatus } : client.forms;
  return { ...client, forms, generatedDocs: [doc, ...client.generatedDocs.filter(d => d.type !== type)] };
}
function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "ok" | "warn" | "bad" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function PortalPage() {
  const clientId = window.location.pathname.split("/portal/")[1]?.split("/")[0] || "";
  const [clients, setClients] = useState<Client[]>(() => load(CLIENTS_KEY, []));
  const [signedName, setSignedName] = useState("");
  const client = clients.find(c => c.id === clientId);

  function saveClient(next: Client) {
    const updated = clients.map(c => c.id === next.id ? next : c);
    setClients(updated);
    saveLocal(CLIENTS_KEY, updated);
  }
  function submitSignature() {
    if (!client) return;
    const next: Client = {
      ...client,
      oneLink: { ...(client.oneLink as LinkStatus), signatureReceived: true, signedName: signedName || client.fullName, signedAt: now() },
      docs: client.docs.map(d => d.id === "popia" || d.category === "Signature" ? { ...d, received: true, verified: false, receivedAt: now(), fileName: "Electronic signature received" } : d)
    };
    saveClient(next);
    alert("Signature saved. Admin can now see it as received.");
  }
  function uploadDoc(docId: string, file?: File | null) {
    if (!client || !file) return;
    const docs = client.docs.map(d => d.id === docId ? { ...d, received: true, receivedAt: now(), fileName: file.name } : d);
    const requiredDocs = docs.filter(d => d.required);
    const docsReceived = requiredDocs.every(d => d.received);
    saveClient({ ...client, docs, oneLink: client.oneLink ? { ...client.oneLink, docsReceived } : client.oneLink });
  }

  if (!client) return <div className="portal-page"><div className="portal-card"><h1>Client link not found</h1><p>This link does not match a client in this browser storage.</p></div></div>;

  return <div className="portal-page">
    <div className="portal-card large">
      <p className="eyebrow">Fin-Tastic Client Portal</p>
      <h1>Signature + Document Upload</h1>
      <p className="muted">One link for both client signature and required documents.</p>
      <div className="portal-summary"><div><span>Client</span><strong>{clientDisplayName(client)}</strong></div><div><span>Service</span><strong>{serviceLabel(client.selectedService)}</strong></div><div><span>Signature</span><strong>{client.oneLink?.signatureReceived ? "Received" : "Pending"}</strong></div><div><span>Documents</span><strong>{client.oneLink?.docsReceived ? "Received" : "Pending"}</strong></div></div>
      <section className="portal-section"><h2>1. Electronic Signature</h2><p>Type your name to confirm signature/authority receipt for admin processing.</p><input placeholder="Client full name" value={signedName} onChange={e=>setSignedName(e.target.value)} /><button className="primary" onClick={submitSignature}>Submit Signature</button></section>
      <section className="portal-section"><h2>2. Upload Documents</h2><div className="doc-grid">{client.docs.map(d => <div className="doc-card" key={d.id}><div><strong>{d.name}</strong><span>{d.category} · {d.required ? "Required" : "Optional"}</span>{d.fileName && <small>{d.fileName}</small>}</div><label className="file-mini">{d.received ? "Replace File" : "Upload File"}<input type="file" onChange={e=>uploadDoc(d.id, e.target.files?.[0])} /></label></div>)}</div></section>
      <button className="ghost" onClick={()=>{ window.location.href = "/"; }}>Back to App</button>
    </div>
  </div>;
}

export default function App() {
  if (window.location.pathname.startsWith("/portal/")) return <PortalPage />;

  const [user, setUser] = useState<User>(USERS[0]);
  const [view, setView] = useState<View>("dashboard");
  const [clients, setClients] = useState<Client[]>(() => load(CLIENTS_KEY, []));
  const [cases, setCases] = useState<AdminCase[]>(() => load(CASES_KEY, []));
  const [selectedClientId, setSelectedClientId] = useState<string>(() => load<Client[]>(CLIENTS_KEY, [])[0]?.id || "");
  const [selectedCaseId, setSelectedCaseId] = useState<string>(() => load<AdminCase[]>(CASES_KEY, [])[0]?.id || "");
  const [previewDoc, setPreviewDoc] = useState<GeneratedDoc | null>(null);
  const [adminTab, setAdminTab] = useState("overview");
  const client = clients.find(c => c.id === selectedClientId) || clients[0];
  const adminCase = cases.find(c => c.id === selectedCaseId) || cases[0];
  const adminClient = adminCase ? clients.find(c => c.id === adminCase.clientId) : undefined;

  React.useEffect(() => { saveLocal(CLIENTS_KEY, clients); }, [clients]);
  React.useEffect(() => { saveLocal(CASES_KEY, cases); }, [cases]);
  React.useEffect(() => {
    const sync = () => {
      setClients(load(CLIENTS_KEY, []));
      setCases(load(CASES_KEY, []));
    };
    window.addEventListener("storage", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("focus", sync);
    };
  }, []);
  React.useEffect(() => { if (view === "consultant" && !isConsultant(user)) setView("dashboard"); if (view === "admin" && !isAdmin(user)) setView("dashboard"); }, [user, view]);

  function saveClient(next: Client) {
    const rec = recommended(next);
    const withCoach = { ...next, coachWarnings: rec.warnings };
    setClients(prev => prev.some(c => c.id === next.id) ? prev.map(c => c.id === next.id ? withCoach : c) : [withCoach, ...prev]);
    setSelectedClientId(next.id);
  }
  function patchClient(patch: Partial<Client>) { if (client) saveClient({ ...client, ...patch }); }
  function patchAdminClient(patch: Partial<Client>) { if (adminClient) saveClient({ ...adminClient, ...patch }); }
  async function handleUpload(file?: File | null) {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const response = await fetch("/api/upload/credit-report", { method: "POST", body: fd });
      const data: ParsedUpload = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || "Parser endpoint failed");
      saveClient(newClientFromParse(file.name, data));
    } catch (error: any) {
      saveClient(newClientFromParse(file.name, { success: false, parsed: { bureau: "Unknown", confidence: 0, warnings: ["Backend parser did not return parsed data. Start Flask backend first.", String(error?.message || error || "Upload failed")], client: {}, accounts: [] } }));
    }
  }
  function makeManualClient() { saveClient(emptyClient("Manual capture")); setView("consultant"); }
  function changeService(service: Service) { if (!client) return; saveClient(applyRecommendation(client, service)); }
  function sendNupay() {
    if (!client) return;
    const next = addOrReplaceGeneratedDoc({ ...client, mandate: { status:"sent", ref:`NUPAY-${Date.now()}`, sentAt:now() } }, "mandate");
    saveClient(next);
    fetch("/api/nupay/send-mandate", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(next) }).catch(()=>undefined);
  }
  function sendOneLink() {
    if (!client) return;
    const token = Math.random().toString(36).slice(2, 10);
    const url = `${window.location.origin}/portal/${client.id}?token=${token}`;
    const next = addOrReplaceGeneratedDoc({ ...client, oneLink: { url, token, sentAt:now(), sentVia: client.whatsapp ? "WhatsApp" : client.phone ? "SMS" : client.email ? "Email" : "Manual copy", sentTo: client.whatsapp || client.phone || client.email || "Manual copy", signatureReceived:false, docsReceived:false } }, "client_link");
    saveClient(next);
  }
  function markSignatureDocsFromConsultant(field: "signature" | "docs") {
    if (!client?.oneLink) return;
    if (field === "signature") patchClient({ oneLink: { ...client.oneLink, signatureReceived: true, signedAt: now(), signedName: client.fullName }, docs: client.docs.map(d => d.id === "popia" ? { ...d, received: true, receivedAt: now(), fileName: "Marked received by consultant" } : d) });
    else patchClient({ oneLink: { ...client.oneLink, docsReceived: true }, docs: client.docs.map(d => d.required ? { ...d, received: true, receivedAt: now(), fileName: d.fileName || "Marked received by consultant" } : d) });
  }
  function passToAdmin() {
    if (!client) return;
    const newCase: AdminCase = { id:`case-${Date.now()}`, clientId:client.id, consultant:user.name, status:"new_handover", priority: client.selectedService.includes("removal") || client.selectedService === "double_sale" ? "high" : "normal", createdAt:now(), stepStatus:{ docs:"not_started" }, audit:[{ at:now(), user:user.name, action:"Sale passed to admin", note:serviceLabel(client.selectedService)}] };
    setCases(prev => prev.some(c => c.clientId === client.id) ? prev.map(c => c.clientId === client.id ? { ...c, ...newCase, id:c.id } : c) : [newCase, ...prev]);
    setSelectedCaseId(newCase.id);
    alert("Sale passed to Admin Back Office.");
  }
  function updateAccount(id: string, patch: Partial<Account>) { if (!client) return; saveClient({ ...client, accounts: client.accounts.map(a => a.id === id ? { ...a, ...patch } : a) }); }
  function addAccount() {
    if (!client) return;
    saveClient({ ...client, accounts: [...client.accounts, normaliseAccount({ creditor: "", accountNo: "", include: true }, client.accounts.length)] });
  }
  function updateDoc(docId: string, patch: Partial<Doc>) {
    if (!adminClient) return;
    patchAdminClient({ docs: adminClient.docs.map(d => d.id === docId ? { ...d, ...patch, receivedAt: patch.received ? d.receivedAt || now() : d.receivedAt } : d) });
  }
  function updateCaseStep(step: string, status: StepStatus) {
    if (!adminCase) return;
    setCases(prev => prev.map(c => c.id === adminCase.id ? { ...c, status: status === "done" ? c.status : "admin_review", stepStatus: { ...c.stepStatus, [step]: status }, audit: [{ at:now(), user:user.name, action:"Workflow updated", note:`${step} = ${status}` }, ...c.audit] } : c));
  }
  function generateDoc(type: GeneratedDoc["type"]) {
    if (!adminClient) return;
    const next = addOrReplaceGeneratedDoc(adminClient, type);
    saveClient(next);
    setPreviewDoc(next.generatedDocs[0]);
  }
  function setFormStatus(form: string, status: StepStatus) { if (!adminClient) return; patchAdminClient({ forms: { ...adminClient.forms, [form]: status } }); }
  function compileCourtPack() { if (!adminClient) return; const ready = Object.fromEntries(courtItems.map(i=>[i,true])); const next = addOrReplaceGeneratedDoc({ ...adminClient, courtPack: ready, adminNotes: `${adminClient.adminNotes || ""}\nCourt pack compiled ${new Date().toLocaleString("en-ZA")}`.trim() }, "court_pack"); saveClient(next); setPreviewDoc(next.generatedDocs[0]); }
  function clearAll() { localStorage.removeItem(CLIENTS_KEY); localStorage.removeItem(CASES_KEY); setClients([]); setCases([]); setSelectedClientId(""); setSelectedCaseId(""); }

  const nav = [{id:"dashboard", label:"Dashboard", show:true}, {id:"consultant", label:"Sales Coach", show:isConsultant(user)}, {id:"admin", label:"Admin Back Office", show:isAdmin(user)}] as { id: View; label: string; show: boolean }[];
  const t = client ? totals(client.accounts) : undefined;
  const adminTotals = adminClient ? totals(adminClient.accounts) : undefined;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="mark">FT</div><div><strong>Fin-Tastic</strong><span>Sales Coach</span></div></div>
      <nav>{nav.filter(n=>n.show).map(n => <button key={n.id} className={view===n.id ? "active" : ""} onClick={()=>setView(n.id)}>{n.label}</button>)}</nav>
      <div className="side-note"><strong>Role Split</strong><span>Consultant = Sales Coach. Admin = docs, forms, PDA, creditors, court packs.</span></div>
    </aside>
    <main className="main">
      <header className="topbar"><div><strong>{view === "admin" ? "Admin Back Office" : view === "consultant" ? "Consultant Sales Coach" : "Dashboard"}</strong><span>{user.name} · {user.role}</span></div><div className="top-actions"><label>Test Role<select value={user.role} onChange={e=>{ const next = USERS.find(u=>u.role===e.target.value)!; setUser(next); }}><option value="consultant">Consultant</option><option value="admin">Admin</option><option value="manager">Manager</option></select></label><button className="ghost" onClick={clearAll}>Clear Data</button></div></header>

      {view === "dashboard" && <section className="page"><div className="hero"><div><p className="eyebrow">Reviewed Build v5</p><h1>Sales Coach + Admin Back Office</h1><p>Consultants upload and sell. Admin processes. The client portal link now opens a working local portal page for signature and document upload.</p></div><button className="primary narrow" onClick={makeManualClient}>Create Manual Client</button></div><div className="stats"><div><strong>{clients.length}</strong><span>Clients</span></div><div><strong>{cases.length}</strong><span>Admin Cases</span></div><div><strong>{clients.filter(c=>c.oneLink?.signatureReceived).length}</strong><span>Signatures</span></div><div><strong>{clients.filter(c=>c.oneLink?.docsReceived).length}</strong><span>Docs Received</span></div></div><div className="cards2"><section className="panel"><h2>Consultant View</h2><p>Upload, view accounts, select service, see Sales Coach advice, send NuPay, send one portal link and pass sale to admin.</p></section><section className="panel"><h2>Admin View</h2><p>Back-office only: client file, accounts, docs/signature, generated document preview, 17.1/17.2/17.3/Form 19, PDA, creditors and court pack.</p></section></div></section>}

      {view === "consultant" && isConsultant(user) && <section className="page"><div className="hero"><div><p className="eyebrow">Consultant Sales Coach</p><h1>Upload, Sell, Send Link</h1><p>Upload the credit report, verify parsed data, select the correct service, send NuPay and one signature+documents link, then pass the sale to admin.</p></div><label className="upload">Upload Credit Report<input type="file" accept=".pdf,.txt,.json" onChange={e=>handleUpload(e.target.files?.[0])}/></label></div><div className="layout"><aside className="panel list"><div className="row"><h2>Clients</h2><button className="ghost small" onClick={makeManualClient}>+ Manual</button></div>{clients.length===0 && <p>No clients yet. Upload a report or create manual client.</p>}{clients.map(c=><button key={c.id} className={client?.id===c.id?"card active":"card"} onClick={()=>setSelectedClientId(c.id)}><strong>{clientDisplayName(c)}</strong><span>{serviceLabel(c.selectedService)}</span><small>{c.reportName}</small></button>)}</aside>{client && <main className="stack"><section className="panel coach-panel"><div className="row"><div><p className="eyebrow">Sales Coach Recommendation</p><h2>{serviceLabel(client.selectedService)}</h2></div><Badge tone={client.parseConfidence >= .65 ? "ok" : client.parseConfidence ? "warn" : "bad"}>Parser confidence {Math.round((client.parseConfidence || 0) * 100)}%</Badge></div><p>{client.coachAdvice}</p><div className="coach-grid"><div><span>DR status</span><strong>{client.confirmedDebtReview ? "Confirmed" : "Not confirmed"}</strong></div><div><span>Assets</span><strong>{client.homeLoan || client.vehicleFinance ? "Home/Vehicle trigger" : "No asset trigger"}</strong></div><div><span>Included balance</span><strong>{t ? money(t.balance) : money(0)}</strong></div><div><span>Reduced proposal</span><strong>{t ? money(t.reduced) : money(0)}</strong></div></div>{[...client.parseWarnings, ...client.coachWarnings].length > 0 && <div className="warning-box"><strong>Fix before sending:</strong><ul>{[...client.parseWarnings, ...client.coachWarnings].map((w,i)=><li key={i}>{w}</li>)}</ul></div>}</section><section className="panel"><h2>Client Details</h2><div className="formgrid">{[["fullName","Client Name"],["idNumber","ID Number"],["phone","Phone"],["whatsapp","WhatsApp"],["email","Email"],["address","Physical Address"],["employer","Employer"],["occupation","Occupation"],["dateEmployed","Date Employed"],["salaryFrequency","Salary Frequency"],["bankName","Bank Name"],["accountHolder","Account Holder"],["accountType","Bank Account Type"],["branchCode","Branch Code"],["accountNumber","Account Number"]].map(([k,l])=><label key={k}>{l}<input value={(client as any)[k] || ""} onChange={e=>patchClient({[k]:e.target.value} as any)}/></label>)}<label>Application<select value={client.applicationType} onChange={e=>saveClient(applyRecommendation({...client, applicationType:e.target.value as any}, client.selectedService))}><option value="single">Single</option><option value="joint">Joint</option></select></label><label>Gross Salary<input type="number" value={client.grossSalary || ""} onChange={e=>patchClient({grossSalary:Number(e.target.value||0)})}/></label><label>Nett Salary<input type="number" value={client.nettSalary || ""} onChange={e=>patchClient({nettSalary:Number(e.target.value||0)})}/></label><label className="check"><input type="checkbox" checked={client.confirmedDebtReview} onChange={e=>saveClient(applyRecommendation({...client, confirmedDebtReview:e.target.checked}))}/>Confirmed Debt Review</label><label className="check"><input type="checkbox" checked={client.homeLoan} onChange={e=>saveClient(applyRecommendation({...client, homeLoan:e.target.checked}))}/>Home Loan</label><label className="check"><input type="checkbox" checked={client.vehicleFinance} onChange={e=>saveClient(applyRecommendation({...client, vehicleFinance:e.target.checked}))}/>Vehicle Finance</label>{client.applicationType==="joint" && <><label>Spouse Name<input value={client.spouseName} onChange={e=>patchClient({spouseName:e.target.value})}/></label><label>Spouse ID<input value={client.spouseId} onChange={e=>patchClient({spouseId:e.target.value})}/></label><label>Spouse Phone<input value={client.spousePhone} onChange={e=>patchClient({spousePhone:e.target.value})}/></label><label>Spouse Email<input value={client.spouseEmail} onChange={e=>patchClient({spouseEmail:e.target.value})}/></label></>}</div></section><section className="panel"><div className="row"><h2>Accounts</h2><button className="ghost small" onClick={addAccount}>+ Add Account</button></div><div className="tablewrap"><table><thead><tr><th>Include</th><th>Creditor</th><th>Account No</th><th>Type</th><th>Opening</th><th>Current</th><th>Arrears</th><th>Monthly</th><th>Reduced</th><th>Months</th><th>Last Paid</th><th>Open Date</th><th>Status</th><th>Furniture</th></tr></thead><tbody>{client.accounts.map(a=><tr key={a.id}><td><input type="checkbox" checked={a.include} onChange={e=>updateAccount(a.id,{include:e.target.checked})}/></td><td><input value={a.creditor} onChange={e=>updateAccount(a.id,{creditor:e.target.value})}/></td><td><input value={a.accountNo} onChange={e=>updateAccount(a.id,{accountNo:e.target.value})}/></td><td><input value={a.type} onChange={e=>updateAccount(a.id,{type:e.target.value})}/></td><td><input type="number" value={a.openingBalance || ""} onChange={e=>updateAccount(a.id,{openingBalance:Number(e.target.value||0)})}/></td><td><input type="number" value={a.currentBalance || ""} onChange={e=>updateAccount(a.id,{currentBalance:Number(e.target.value||0)})}/></td><td><input type="number" value={a.arrears || ""} onChange={e=>updateAccount(a.id,{arrears:Number(e.target.value||0)})}/></td><td><input type="number" value={a.monthlyInstallment || ""} onChange={e=>updateAccount(a.id,{monthlyInstallment:Number(e.target.value||0)})}/></td><td><input type="number" value={a.reducedInstallment || ""} onChange={e=>updateAccount(a.id,{reducedInstallment:Number(e.target.value||0)})}/></td><td><input type="number" value={a.monthsInArrears || ""} onChange={e=>updateAccount(a.id,{monthsInArrears:Number(e.target.value||0)})}/></td><td><input value={a.lastPaid} onChange={e=>updateAccount(a.id,{lastPaid:e.target.value})}/></td><td><input value={a.openDate} onChange={e=>updateAccount(a.id,{openDate:e.target.value})}/></td><td><input value={a.status} onChange={e=>updateAccount(a.id,{status:e.target.value})}/></td><td><input type="checkbox" checked={a.furniture} onChange={e=>updateAccount(a.id,{furniture:e.target.checked})}/></td></tr>)}</tbody></table></div>{t && <div className="stats five"><div><strong>{t.count}</strong><span>Included</span></div><div><strong>{money(t.balance)}</strong><span>Balance</span></div><div><strong>{money(t.arrears)}</strong><span>Arrears</span></div><div><strong>{money(t.monthly)}</strong><span>Monthly</span></div><div><strong>{money(t.reduced)}</strong><span>Reduced</span></div></div>}</section><section className="panel"><h2>Select Service</h2><div className="services">{(["debt_review","debt_review_removal","debt_mediation","double_sale"] as Service[]).map(s=><button key={s} className={client.selectedService===s?"service active":"service"} onClick={()=>changeService(s)}><strong>{serviceLabel(s)}</strong><span>{client.selectedService===s?"Selected":"Select"}</span></button>)}</div></section><section className="panel"><h2>Consultant Actions</h2><div className="actions"><div className="action"><h3>NuPay Mandate</h3><p>Status: {pretty(client.mandate.status)}</p>{client.mandate.ref && <p>Ref: {client.mandate.ref}</p>}<button className="primary" onClick={sendNupay}>Send NuPay Mandate</button></div><div className="action"><h3>One Link</h3><p>Working local portal link for signature + documents.</p>{client.oneLink ? <><div className="link">{client.oneLink.url}</div><div className="button-row"><button className="ghost" onClick={()=>navigator.clipboard?.writeText(client.oneLink!.url)}>Copy Link</button><button className="ghost" onClick={()=>window.open(client.oneLink!.url, "_blank")}>Open Portal</button></div><p>Signature: {client.oneLink.signatureReceived?"Received":"Pending"} · Docs: {client.oneLink.docsReceived?"Received":"Pending"}</p><button className="ghost" onClick={()=>markSignatureDocsFromConsultant("signature")}>Mark Signature Received</button><button className="ghost" onClick={()=>markSignatureDocsFromConsultant("docs")}>Mark Docs Received</button></> : <button className="primary" onClick={sendOneLink}>Send 1 Link for Signature + Docs</button>}</div><div className="action"><h3>Pass Sale</h3><p>Send complete case to admin back office.</p><button className="primary" onClick={passToAdmin}>Pass Sale to Admin</button></div></div></section></main>}</div></section>}

      {view === "admin" && isAdmin(user) && <section className="page"><div className="hero"><div><p className="eyebrow">Admin Only</p><h1>Admin Back Office</h1><p>Admin handles documents, signatures, statutory forms, generated documents, PDA/API, creditor process and court packs.</p></div></div><div className="layout"><aside className="panel list"><h2>Admin Cases</h2>{cases.length===0 && <p>No cases passed from consultants.</p>}{cases.map(c=><button key={c.id} className={adminCase?.id===c.id?"card active":"card"} onClick={()=>{setSelectedCaseId(c.id); setAdminTab("overview");}}><strong>{clientDisplayName(clients.find(x=>x.id===c.clientId))}</strong><span>{pretty(c.status)}</span><small>{c.consultant}</small></button>)}</aside>{adminCase && adminClient && <main className="stack"><section className="panel"><div className="row"><div><h2>{clientDisplayName(adminClient)}</h2><p className="muted">{serviceLabel(adminClient.selectedService)} · {pretty(adminClient.applicationType)} · Consultant: {adminCase.consultant}</p></div><Badge tone={adminCase.priority === "high" ? "warn" : "neutral"}>{pretty(adminCase.priority)}</Badge></div><div className="stats six"><div><strong>{adminClient.oneLink?.signatureReceived?"Received":"Pending"}</strong><span>Signature</span></div><div><strong>{adminClient.oneLink?.docsReceived?"Received":"Pending"}</strong><span>Docs</span></div><div><strong>{pretty(adminClient.mandate.status)}</strong><span>Mandate</span></div><div><strong>{adminTotals ? money(adminTotals.balance) : money(0)}</strong><span>Balance</span></div><div><strong>{adminTotals ? money(adminTotals.reduced) : money(0)}</strong><span>Reduced</span></div><div><strong>{adminClient.generatedDocs.length}</strong><span>Generated Docs</span></div></div>{adminClient.oneLink && <div className="link wide">{adminClient.oneLink.url}</div>}</section><section className="panel tabbar">{["overview","accounts","docs","forms","generated","creditors","pda","court"].map(tab=><button key={tab} className={adminTab===tab?"active-tab":""} onClick={()=>setAdminTab(tab)}>{pretty(tab)}</button>)}</section>{adminTab==="overview" && <section className="panel"><h2>Full Client File</h2><div className="details-grid"><div><span>Name</span><strong>{clientDisplayName(adminClient)}</strong></div><div><span>ID</span><strong>{adminClient.idNumber || "Missing"}</strong></div><div><span>Phone</span><strong>{adminClient.phone || "-"}</strong></div><div><span>WhatsApp</span><strong>{adminClient.whatsapp || "-"}</strong></div><div><span>Email</span><strong>{adminClient.email || "-"}</strong></div><div><span>Address</span><strong>{adminClient.address || "-"}</strong></div><div><span>Employer</span><strong>{adminClient.employer || "-"}</strong></div><div><span>Nett Salary</span><strong>{money(adminClient.nettSalary)}</strong></div><div><span>Bank</span><strong>{adminClient.bankName || "-"}</strong></div><div><span>Account Holder</span><strong>{adminClient.accountHolder || "-"}</strong></div><div><span>Account Type</span><strong>{adminClient.accountType || "-"}</strong></div><div><span>Account No</span><strong>{adminClient.accountNumber || "-"}</strong></div></div><h3>Workflow</h3><div className="steps">{workflowByService[adminClient.selectedService].map((s,i)=><div className="step" key={s.id}><b>{i+1}</b><div><h3>{s.title}</h3><p>{s.description}</p><select value={adminCase.stepStatus[s.id] || "not_started"} onChange={e=>updateCaseStep(s.id, e.target.value as StepStatus)}><option value="not_started">Not Started</option><option value="in_progress">In Progress</option><option value="blocked">Blocked</option><option value="done">Done</option></select></div></div>)}</div></section>}{adminTab==="accounts" && <section className="panel"><h2>Accounts and Creditor Balances</h2><div className="tablewrap"><table><thead><tr><th>Include</th><th>Creditor</th><th>Account No</th><th>Type</th><th>Opening</th><th>Current</th><th>Arrears</th><th>Monthly</th><th>Reduced</th><th>Months</th><th>Last Paid</th><th>Open Date</th><th>Status</th><th>Furniture</th></tr></thead><tbody>{adminClient.accounts.map(a=><tr key={a.id}><td>{a.include?"Yes":"No"}</td><td>{a.creditor || "-"}</td><td>{a.accountNo || "-"}</td><td>{a.type || "-"}</td><td>{money(a.openingBalance)}</td><td>{money(a.currentBalance)}</td><td>{money(a.arrears)}</td><td>{money(a.monthlyInstallment)}</td><td>{money(a.reducedInstallment)}</td><td>{a.monthsInArrears || 0}</td><td>{a.lastPaid || "-"}</td><td>{a.openDate || "-"}</td><td>{a.status || "-"}</td><td>{a.furniture?"Yes":"No"}</td></tr>)}</tbody></table></div></section>}{adminTab==="docs" && <section className="panel"><h2>Client Documents + Signature</h2><div className="doc-grid">{adminClient.docs.map(d=><div className="doc-card" key={d.id}><div><strong>{d.name}</strong><span>{d.category} · {d.required?"Required":"Optional"}</span>{d.fileName && <small>{d.fileName}</small>}</div><div className="button-row"><button className={d.received?"ok":"ghost"} onClick={()=>updateDoc(d.id,{received:!d.received})}>{d.received?"Received":"Mark Received"}</button><button className={d.verified?"ok":"ghost"} onClick={()=>updateDoc(d.id,{verified:!d.verified})}>{d.verified?"Verified":"Verify"}</button></div></div>)}</div></section>}{adminTab==="forms" && <section className="panel"><h2>Statutory Forms</h2><div className="forms">{formList.map(f=><div className="form" key={f}><strong>Form {f}</strong><span>{f==="17.1"?"Notice to credit providers/bureaus":f==="17.2"?"Assessment outcome / decision":f==="17.3"?"Route-specific follow-up":"Clearance certificate"}</span><select value={adminClient.forms[f] || "not_started"} onChange={e=>setFormStatus(f, e.target.value as StepStatus)}><option value="not_started">Not Started</option><option value="in_progress">In Progress</option><option value="blocked">Blocked</option><option value="done">Done / Sent</option></select><button className="primary" onClick={()=>generateDoc(f)}>Generate + View</button></div>)}</div></section>}{adminTab==="generated" && <section className="panel"><h2>Generated Documents</h2>{adminClient.generatedDocs.length===0 && <p className="muted">No generated documents yet. Generate a form or court pack first.</p>}<div className="generated-list">{adminClient.generatedDocs.map(d=><button key={d.id} className="generated-card" onClick={()=>setPreviewDoc(d)}><strong>{d.title}</strong><span>{new Date(d.createdAt).toLocaleString("en-ZA")} · {pretty(d.status)}</span></button>)}</div></section>}{adminTab==="creditors" && <section className="panel"><h2>Creditor Contact Info + NCA Process</h2><div className="creditors">{creditors.map(c=><div className="creditor" key={c.name}><h3>{c.name}</h3><p><b>{c.department}</b></p><p>Email: {c.email || "Manual verification required"}</p><p>Phone: {c.phone || "Manual verification required"}</p><p>{c.process}</p><ul>{c.nca.map(x=><li key={x}>{x}</li>)}</ul></div>)}</div></section>}{adminTab==="pda" && <section className="panel"><h2>PDA / API</h2><div className="details-grid"><div><span>Client</span><strong>{clientDisplayName(adminClient)}</strong></div><div><span>Bank</span><strong>{adminClient.bankName || "-"}</strong></div><div><span>Holder</span><strong>{adminClient.accountHolder || "-"}</strong></div><div><span>Type</span><strong>{adminClient.accountType || "-"}</strong></div><div><span>Branch</span><strong>{adminClient.branchCode || "-"}</strong></div><div><span>Account</span><strong>{adminClient.accountNumber || "-"}</strong></div><div><span>Mandate</span><strong>{pretty(adminClient.mandate.status)}</strong></div><div><span>NuPay Ref</span><strong>{adminClient.mandate.ref || "-"}</strong></div></div><button className="primary narrow" onClick={()=>updateCaseStep("pda", "done")}>Submit to PDA API Placeholder</button></section>}{adminTab==="court" && <section className="panel"><h2>Court / Removal Pack</h2><p>Relevant for Debt Review Removal and DRR + Mediation. Admin can mark the pack ready and compile the route-specific documents.</p><div className="doc-grid">{courtItems.map(i=><div className="doc-card" key={i}><strong>{i}</strong><button className={adminClient.courtPack[i]?"ok":"ghost"} onClick={()=>patchAdminClient({courtPack:{...adminClient.courtPack,[i]:!adminClient.courtPack[i]}})}>{adminClient.courtPack[i]?"Ready":"Mark Ready"}</button></div>)}</div><button className="primary narrow" onClick={compileCourtPack}>Compile + View Relevant Court Docs</button></section>}</main>}</div></section>}
    </main>{previewDoc && <div className="modal"><div className="modal-card"><div className="row"><div><p className="eyebrow">Document Preview</p><h2>{previewDoc.title}</h2></div><button className="ghost" onClick={()=>setPreviewDoc(null)}>Close</button></div><pre>{previewDoc.content}</pre></div></div>}
  </div>;
}
