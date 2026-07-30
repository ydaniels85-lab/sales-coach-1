import { useEffect, useMemo, useRef, useState } from 'react';

type BankDetails = {
  accountHolder: string;
  bankName: string;
  accountType: string;
  branchCode: string;
  accountNumber: string;
  debitOrderDay: string;
};

type PersonDetails = {
  firstName: string;
  secondName: string;
  surname: string;
  fullName: string;
  idNumber: string;
  dateOfBirth: string;
  gender: string;
  maritalStatus: string;
  phone: string;
  alternativePhone: string;
  whatsapp: string;
  email: string;
  physicalAddress: string;
  suburb: string;
  city: string;
  province: string;
  postalCode: string;
  employer: string;
  occupation: string;
  dateEmployed: string;
  salaryFrequency: string;
  grossSalary: number;
  nettSalary: number;
  monthlyLivingExpenses: number;
  bank: BankDetails;
};

type DebtAccount = {
  id: string;
  creditorName: string;
  accountNumber: string;
  accountType: string;
  openingBalance: number;
  currentBalance: number;
  arrears: number;
  monthlyInstallment: number;
  reducedAmount: number;
  lastPaidDate: string;
  monthsInArrears: number;
  openDate: string;
  status: string;
  included: boolean;
  isFurniture: boolean;
  isAsset: boolean;
  parserSource: string;
};

type PaymentPlan = {
  months: number;
  label: string;
  monthlyAmount: number;
};

type Coach = {
  service: string;
  urgency: string;
  headline: string;
  reasons: string[];
  openingScript: string;
  qualifyingQuestions: string[];
  nextSteps: string[];
  objectionHandlers: string[];
  pricing: null | {
    currency: string;
    onceOff: number;
    description: string;
    paymentPlans: PaymentPlan[];
  };
  totals: {
    outstanding: number;
    arrears: number;
    originalInstalment: number;
    reducedInstalment: number;
    estimatedRelief: number;
  };
  flags: {
    debtReviewListed: boolean;
    hasAsset: boolean;
    hasFurniture: boolean;
    scoreZeroRule: boolean;
    doubleSaleCandidate: boolean;
    creditProfileInvestigationCandidate: boolean;
  };
};

type Client = PersonDetails & {
  id: string;
  applicationType: 'Single' | 'Joint';
  spouse: PersonDetails;
  creditScore: number | null;
  scoreFound: boolean;
  riskCategory: string;
  debtReviewListed: boolean;
  debtReviewDetail: string;
  serviceType: string;
  status: string;
  detailsCompletion: number;
  detailsComplete: boolean;
  accounts: DebtAccount[];
  coach: Coach;
  report: {
    bureau: string;
    filename: string;
    reportReference: string;
    clientReference: string;
    searchDate: string;
    summary: Record<string, number>;
  };
};

type ParseResponse = {
  success: boolean;
  clientId: string;
  client: Client;
  warnings: string[];
  confidence: number;
  pdf: { encrypted: boolean; usedDefaultPassword: boolean; usedOcr: boolean; pageCount: number };
};

type View = 'dashboard' | 'upload' | 'capture' | 'clients';

const EMPTY_BANK: BankDetails = {
  accountHolder: '',
  bankName: '',
  accountType: '',
  branchCode: '',
  accountNumber: '',
  debitOrderDay: ''
};

const EMPTY_PERSON: PersonDetails = {
  firstName: '',
  secondName: '',
  surname: '',
  fullName: '',
  idNumber: '',
  dateOfBirth: '',
  gender: '',
  maritalStatus: '',
  phone: '',
  alternativePhone: '',
  whatsapp: '',
  email: '',
  physicalAddress: '',
  suburb: '',
  city: '',
  province: '',
  postalCode: '',
  employer: '',
  occupation: '',
  dateEmployed: '',
  salaryFrequency: 'Monthly',
  grossSalary: 0,
  nettSalary: 0,
  monthlyLivingExpenses: 0,
  bank: { ...EMPTY_BANK }
};

const EMPTY_COACH: Coach = {
  service: 'Needs Manual Review',
  urgency: 'Low',
  headline: 'Manual review required',
  reasons: ['Upload a credit report to activate the Sales Opportunity Engine.'],
  openingScript: 'Capture the client objective and supporting information before selecting a service.',
  qualifyingQuestions: ['What result is the client trying to achieve?'],
  nextSteps: ['Capture the client details and upload the credit report.'],
  objectionHandlers: ['Do not promise an outcome before the report and documents are verified.'],
  pricing: null,
  totals: { outstanding: 0, arrears: 0, originalInstalment: 0, reducedInstalment: 0, estimatedRelief: 0 },
  flags: {
    debtReviewListed: false,
    hasAsset: false,
    hasFurniture: false,
    scoreZeroRule: false,
    doubleSaleCandidate: false,
    creditProfileInvestigationCandidate: false
  }
};

const money = (value: number | undefined) => new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR' }).format(value || 0);

function normalizePerson(value?: Partial<PersonDetails>): PersonDetails {
  return {
    ...EMPTY_PERSON,
    ...(value || {}),
    grossSalary: Number(value?.grossSalary || 0),
    nettSalary: Number(value?.nettSalary || 0),
    monthlyLivingExpenses: Number(value?.monthlyLivingExpenses || 0),
    bank: { ...EMPTY_BANK, ...(value?.bank || {}) }
  };
}

function normalizeClient(value: Partial<Client>): Client {
  const primary = normalizePerson(value);
  return {
    ...primary,
    id: value.id || '',
    applicationType: value.applicationType === 'Joint' ? 'Joint' : 'Single',
    spouse: normalizePerson(value.spouse),
    creditScore: value.creditScore ?? null,
    scoreFound: Boolean(value.scoreFound),
    riskCategory: value.riskCategory || '',
    debtReviewListed: Boolean(value.debtReviewListed),
    debtReviewDetail: value.debtReviewDetail || '',
    serviceType: value.serviceType || value.coach?.service || 'Needs Manual Review',
    status: value.status || 'Client Details Captured',
    detailsCompletion: Number(value.detailsCompletion || 0),
    detailsComplete: Boolean(value.detailsComplete),
    accounts: Array.isArray(value.accounts) ? value.accounts : [],
    coach: {
      ...EMPTY_COACH,
      ...(value.coach || {}),
      reasons: value.coach?.reasons || EMPTY_COACH.reasons,
      openingScript: value.coach?.openingScript || EMPTY_COACH.openingScript,
      qualifyingQuestions: value.coach?.qualifyingQuestions || EMPTY_COACH.qualifyingQuestions,
      nextSteps: value.coach?.nextSteps || EMPTY_COACH.nextSteps,
      objectionHandlers: value.coach?.objectionHandlers || EMPTY_COACH.objectionHandlers,
      totals: { ...EMPTY_COACH.totals, ...(value.coach?.totals || {}) },
      flags: { ...EMPTY_COACH.flags, ...(value.coach?.flags || {}) },
      pricing: value.coach?.pricing || null
    },
    report: {
      bureau: value.report?.bureau || '',
      filename: value.report?.filename || '',
      reportReference: value.report?.reportReference || '',
      clientReference: value.report?.clientReference || '',
      searchDate: value.report?.searchDate || '',
      summary: value.report?.summary || {}
    }
  };
}

function calculateCompletion(client: Client): number {
  const primary = [
    client.firstName, client.surname, client.idNumber, client.phone, client.email,
    client.physicalAddress, client.employer, client.nettSalary,
    client.bank.accountHolder, client.bank.bankName, client.bank.accountType, client.bank.accountNumber
  ];
  const values: Array<string | number> = [...primary];
  if (client.applicationType === 'Joint') {
    values.push(
      client.spouse.firstName, client.spouse.surname, client.spouse.idNumber,
      client.spouse.phone, client.spouse.email, client.spouse.employer,
      client.spouse.nettSalary, client.spouse.bank.accountHolder,
      client.spouse.bank.bankName, client.spouse.bank.accountNumber
    );
  }
  const completed = values.filter((value) => value !== '' && value !== 0).length;
  return values.length ? Math.round((completed / values.length) * 100) : 0;
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(init.headers || {})
    }
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.error || `Request failed (${response.status})`) as Error & { payload?: unknown; status?: number };
    error.payload = body;
    error.status = response.status;
    throw error;
  }
  return body as T;
}

function Field(props: {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  inputMode?: 'text' | 'numeric' | 'decimal' | 'tel' | 'email' | 'search' | 'url' | 'none';
}) {
  return (
    <label>
      {props.label}
      <input
        type={props.type || 'text'}
        value={props.value}
        placeholder={props.placeholder}
        inputMode={props.inputMode}
        onChange={(event) => props.onChange(event.target.value)}
      />
    </label>
  );
}

function SelectField(props: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label>
      {props.label}
      <select value={props.value} onChange={(event) => props.onChange(event.target.value)}>
        <option value="">Select</option>
        {props.options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function PasswordDialog(props: {
  open: boolean;
  invalid: boolean;
  companyDefaultAvailable: boolean;
  busy: boolean;
  onCancel: () => void;
  onSubmit: (password: string, useDefault: boolean) => void;
}) {
  const [password, setPassword] = useState('');
  useEffect(() => { if (props.open) setPassword(''); }, [props.open]);
  if (!props.open) return null;
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <section className="modal-card">
        <div className="icon-bubble">🔒</div>
        <h2>Password-protected credit report</h2>
        <p>The PDF is encrypted. Enter the report password, or use the company default kept securely on the server.</p>
        {props.invalid && <div className="alert danger">That password did not unlock the PDF. Check it and try again.</div>}
        <label>PDF password<input autoFocus type="password" value={password} onChange={(event) => setPassword(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && password) props.onSubmit(password, false); }} /></label>
        <div className="button-row">
          <button className="ghost" onClick={props.onCancel} disabled={props.busy}>Cancel</button>
          {props.companyDefaultAvailable && <button className="secondary" onClick={() => props.onSubmit('', true)} disabled={props.busy}>Use company default</button>}
          <button className="primary" onClick={() => props.onSubmit(password, false)} disabled={props.busy || !password}>Unlock & parse</button>
        </div>
      </section>
    </div>
  );
}

function UploadView({ onParsed }: { onParsed: (result: ParseResponse) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [passwordPrompt, setPasswordPrompt] = useState({ open: false, invalid: false, companyDefaultAvailable: false });

  const submit = async (password = '', useDefault = false) => {
    if (!file) return;
    setBusy(true);
    setError('');
    const form = new FormData();
    form.append('file', file);
    if (password) form.append('pdfPassword', password);
    if (useDefault) form.append('useDefaultPassword', 'true');
    try {
      const result = await api<ParseResponse>('/api/upload/credit-report', { method: 'POST', body: form });
      setPasswordPrompt({ open: false, invalid: false, companyDefaultAvailable: false });
      onParsed(result);
    } catch (caught) {
      const typed = caught as Error & { payload?: { code?: string; invalidPassword?: boolean; companyDefaultAvailable?: boolean } };
      if (typed.payload?.code === 'PDF_PASSWORD_REQUIRED') {
        setPasswordPrompt({ open: true, invalid: Boolean(typed.payload.invalidPassword), companyDefaultAvailable: Boolean(typed.payload.companyDefaultAvailable) });
      } else {
        setError(typed.message);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <section className="panel upload-panel">
        <div className="section-heading"><div><p className="eyebrow">Credit report</p><h2>Upload and analyse</h2></div><span className="pill">Protected PDF flow enabled</span></div>
        <div className="drop-zone" onClick={() => inputRef.current?.click()}>
          <input ref={inputRef} hidden type="file" accept="application/pdf,.pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} />
          <div className="upload-icon">PDF</div>
          <strong>{file?.name || 'Choose a PDF report'}</strong>
          <span>{file ? `${(file.size / 1024).toFixed(0)} KB ready to parse` : 'Click here to select a Datanamix credit report'}</span>
        </div>
        <div className="info-grid">
          <article><b>Protected PDFs</b><span>A password box opens only when the file is encrypted.</span></article>
          <article><b>Client capture</b><span>After parsing, complete personal, employment, affordability and banking information.</span></article>
          <article><b>Sales Coach</b><span>Debt Review, Removal, Mediation and Credit Profile Investigation routing.</span></article>
        </div>
        {error && <div className="alert danger">{error}</div>}
        <button className="primary large" disabled={!file || busy} onClick={() => submit()}>{busy ? 'Analysing report…' : 'Analyse credit report'}</button>
      </section>
      <PasswordDialog
        open={passwordPrompt.open}
        invalid={passwordPrompt.invalid}
        companyDefaultAvailable={passwordPrompt.companyDefaultAvailable}
        busy={busy}
        onCancel={() => setPasswordPrompt({ open: false, invalid: false, companyDefaultAvailable: false })}
        onSubmit={submit}
      />
    </>
  );
}

function PersonForm(props: {
  title: string;
  subtitle: string;
  person: PersonDetails;
  setPersonField: <K extends keyof PersonDetails>(field: K, value: PersonDetails[K]) => void;
  setBankField: <K extends keyof BankDetails>(field: K, value: BankDetails[K]) => void;
}) {
  const person = props.person;
  return (
    <div className="form-section-stack">
      <section className="panel form-panel">
        <div className="section-heading"><div><p className="eyebrow">{props.subtitle}</p><h2>{props.title}</h2></div></div>
        <div className="form-grid three">
          <Field label="First name" value={person.firstName} onChange={(value) => props.setPersonField('firstName', value)} />
          <Field label="Second name" value={person.secondName} onChange={(value) => props.setPersonField('secondName', value)} />
          <Field label="Surname" value={person.surname} onChange={(value) => props.setPersonField('surname', value)} />
          <Field label="ID number" value={person.idNumber} inputMode="numeric" onChange={(value) => props.setPersonField('idNumber', value)} />
          <Field label="Date of birth" type="date" value={person.dateOfBirth} onChange={(value) => props.setPersonField('dateOfBirth', value)} />
          <SelectField label="Gender" value={person.gender} options={['Female', 'Male', 'Non-binary', 'Prefer not to say']} onChange={(value) => props.setPersonField('gender', value)} />
          <SelectField label="Marital status" value={person.maritalStatus} options={['Single', 'Married in community of property', 'Married out of community of property', 'Divorced', 'Widowed', 'Life partner']} onChange={(value) => props.setPersonField('maritalStatus', value)} />
          <Field label="Cellphone" value={person.phone} inputMode="tel" onChange={(value) => props.setPersonField('phone', value)} />
          <Field label="Alternative number" value={person.alternativePhone} inputMode="tel" onChange={(value) => props.setPersonField('alternativePhone', value)} />
          <Field label="WhatsApp" value={person.whatsapp} inputMode="tel" onChange={(value) => props.setPersonField('whatsapp', value)} />
          <Field label="Email" type="email" value={person.email} inputMode="email" onChange={(value) => props.setPersonField('email', value)} />
        </div>
        <div className="form-grid two address-grid">
          <label className="span-two">Physical address<textarea rows={3} value={person.physicalAddress} onChange={(event) => props.setPersonField('physicalAddress', event.target.value)} /></label>
          <Field label="Suburb" value={person.suburb} onChange={(value) => props.setPersonField('suburb', value)} />
          <Field label="City / Town" value={person.city} onChange={(value) => props.setPersonField('city', value)} />
          <Field label="Province" value={person.province} onChange={(value) => props.setPersonField('province', value)} />
          <Field label="Postal code" value={person.postalCode} inputMode="numeric" onChange={(value) => props.setPersonField('postalCode', value)} />
        </div>
      </section>

      <section className="panel form-panel">
        <div className="section-heading"><div><p className="eyebrow">Affordability</p><h2>Employment and income</h2></div></div>
        <div className="form-grid three">
          <Field label="Employer" value={person.employer} onChange={(value) => props.setPersonField('employer', value)} />
          <Field label="Occupation" value={person.occupation} onChange={(value) => props.setPersonField('occupation', value)} />
          <Field label="Date employed" type="date" value={person.dateEmployed} onChange={(value) => props.setPersonField('dateEmployed', value)} />
          <SelectField label="Salary frequency" value={person.salaryFrequency} options={['Weekly', 'Fortnightly', 'Monthly']} onChange={(value) => props.setPersonField('salaryFrequency', value)} />
          <Field label="Gross salary" type="number" value={person.grossSalary} inputMode="decimal" onChange={(value) => props.setPersonField('grossSalary', Number(value || 0))} />
          <Field label="Nett salary" type="number" value={person.nettSalary} inputMode="decimal" onChange={(value) => props.setPersonField('nettSalary', Number(value || 0))} />
          <Field label="Monthly household budget / living expenses" type="number" value={person.monthlyLivingExpenses} inputMode="decimal" onChange={(value) => props.setPersonField('monthlyLivingExpenses', Number(value || 0))} />
        </div>
      </section>

      <section className="panel form-panel banking-panel">
        <div className="section-heading"><div><p className="eyebrow">Debit-order readiness</p><h2>Banking information</h2></div><span className="pill">Verify against bank statement</span></div>
        <div className="form-grid three">
          <Field label="Account holder" value={person.bank.accountHolder} onChange={(value) => props.setBankField('accountHolder', value)} />
          <SelectField label="Bank name" value={person.bank.bankName} options={['Absa', 'African Bank', 'Capitec', 'Discovery Bank', 'FNB', 'Investec', 'Nedbank', 'Standard Bank', 'TymeBank', 'Other']} onChange={(value) => props.setBankField('bankName', value)} />
          <SelectField label="Account type" value={person.bank.accountType} options={['Cheque / Current', 'Savings', 'Transmission']} onChange={(value) => props.setBankField('accountType', value)} />
          <Field label="Branch code" value={person.bank.branchCode} inputMode="numeric" onChange={(value) => props.setBankField('branchCode', value)} />
          <Field label="Account number" value={person.bank.accountNumber} inputMode="numeric" onChange={(value) => props.setBankField('accountNumber', value)} />
          <SelectField label="Preferred debit-order day" value={person.bank.debitOrderDay} options={Array.from({ length: 31 }, (_, index) => String(index + 1))} onChange={(value) => props.setBankField('debitOrderDay', value)} />
        </div>
      </section>
    </div>
  );
}

function ClientCapture(props: { client: Client; onSaved: (client: Client) => void; onOpenCoach: () => void }) {
  const [draft, setDraft] = useState<Client>(() => normalizeClient(props.client));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const liveCompletion = useMemo(() => calculateCompletion(draft), [draft]);

  useEffect(() => {
    setDraft(normalizeClient(props.client));
    setError('');
    setMessage('');
  }, [props.client]);

  const setPrimary = <K extends keyof PersonDetails>(field: K, value: PersonDetails[K]) => {
    setDraft((current) => ({ ...current, [field]: value }));
  };
  const setPrimaryBank = <K extends keyof BankDetails>(field: K, value: BankDetails[K]) => {
    setDraft((current) => ({ ...current, bank: { ...current.bank, [field]: value } }));
  };
  const setSpouse = <K extends keyof PersonDetails>(field: K, value: PersonDetails[K]) => {
    setDraft((current) => ({ ...current, spouse: { ...current.spouse, [field]: value } }));
  };
  const setSpouseBank = <K extends keyof BankDetails>(field: K, value: BankDetails[K]) => {
    setDraft((current) => ({ ...current, spouse: { ...current.spouse, bank: { ...current.spouse.bank, [field]: value } } }));
  };

  const save = async () => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await api<{ success: boolean; client: Client }>(`/api/clients/${draft.id}`, {
        method: 'PATCH',
        body: JSON.stringify(draft)
      });
      const saved = normalizeClient(result.client);
      setDraft(saved);
      props.onSaved(saved);
      setMessage('Client details, application type and banking information were saved.');
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="view-stack capture-view">
      <section className="hero-card capture-hero">
        <div>
          <p className="eyebrow">Client capture</p>
          <h2>{draft.fullName || [draft.firstName, draft.surname].filter(Boolean).join(' ') || 'New client'}</h2>
          <p>{draft.report.bureau ? `${draft.report.bureau} report attached` : 'Credit report not uploaded yet'} · {draft.serviceType}</p>
        </div>
        <div className="completion-box"><span>Capture completion</span><strong>{liveCompletion}%</strong><div><i style={{ width: `${liveCompletion}%` }} /></div></div>
      </section>

      <section className="panel application-selector">
        <div><p className="eyebrow">Application structure</p><h2>Single or joint application</h2><p>Select Joint to open a complete spouse/co-applicant capture section.</p></div>
        <div className="segment-control">
          <button className={draft.applicationType === 'Single' ? 'active' : ''} onClick={() => setDraft((current) => ({ ...current, applicationType: 'Single' }))}>Single application</button>
          <button className={draft.applicationType === 'Joint' ? 'active' : ''} onClick={() => setDraft((current) => ({ ...current, applicationType: 'Joint' }))}>Joint application</button>
        </div>
      </section>

      <PersonForm title="Primary applicant personal information" subtitle="Primary applicant" person={draft} setPersonField={setPrimary} setBankField={setPrimaryBank} />

      {draft.applicationType === 'Joint' && (
        <div className="joint-divider">
          <div><span>Joint application</span><h2>Spouse / co-applicant</h2></div>
          <PersonForm title="Spouse / co-applicant personal information" subtitle="Joint applicant" person={draft.spouse} setPersonField={setSpouse} setBankField={setSpouseBank} />
        </div>
      )}

      {error && <div className="alert danger">{error}</div>}
      {message && <div className="alert success">{message}</div>}
      <section className="save-bar">
        <div><strong>{draft.applicationType} application</strong><span>Save before sending mandates, signature links or handing over to admin.</span></div>
        <div className="button-row">
          <button className="ghost" onClick={props.onOpenCoach}>View Sales Coach</button>
          <button className="primary large" disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save client details'}</button>
        </div>
      </section>
    </div>
  );
}

function SalesCoachPanel({ coach }: { coach: Coach }) {
  return (
    <section className={`panel coach-panel ${coach.flags.creditProfileInvestigationCandidate ? 'cpi' : ''}`}>
      <div className="section-heading"><div><p className="eyebrow">Sales Opportunity Engine</p><h2>{coach.headline}</h2></div><div className="coach-badges"><span className={`urgency ${coach.urgency.toLowerCase()}`}>{coach.urgency}</span><span className="service-badge">{coach.service}</span></div></div>

      {coach.flags.creditProfileInvestigationCandidate && (
        <div className="opportunity-callout">
          <div><span>New opportunity rule</span><strong>Not under debt review + total instalments below R1,000 pm</strong></div>
          <b>Potential Credit Profile Investigation sale</b>
        </div>
      )}

      <div className="coach-grid">
        <article className="script-card"><span>Suggested call opening</span><blockquote>{coach.openingScript}</blockquote></article>
        <article><h3>Why this route</h3><ul>{coach.reasons.map((reason, index) => <li key={`${reason}-${index}`}>{reason}</li>)}</ul></article>
        <article><h3>Qualifying questions</h3><ol>{coach.qualifyingQuestions.map((question, index) => <li key={`${question}-${index}`}>{question}</li>)}</ol></article>
        <article><h3>Consultant next steps</h3><ol>{coach.nextSteps.map((step, index) => <li key={`${step}-${index}`}>{step}</li>)}</ol></article>
      </div>

      {coach.pricing && (
        <div className="pricing-section">
          <div><p className="eyebrow">Service fee</p><h3>{money(coach.pricing.onceOff)} total</h3><p>{coach.pricing.description}</p></div>
          <div className="payment-plans">{coach.pricing.paymentPlans.map((plan) => (
            <article key={plan.months}><span>{plan.label}</span><strong>{money(plan.monthlyAmount)}</strong><small>{plan.months === 1 ? 'single payment' : 'per month'}</small></article>
          ))}</div>
        </div>
      )}

      <details className="objection-box"><summary>Responsible objection handling</summary><ul>{coach.objectionHandlers.map((handler, index) => <li key={`${handler}-${index}`}>{handler}</li>)}</ul></details>
    </section>
  );
}

function ClientDetail(props: { client: Client; warnings?: string[]; confidence?: number; onEdit: () => void; onUpload: () => void }) {
  const client = normalizeClient(props.client);
  const included = client.accounts.filter((account) => account.included);
  return (
    <div className="view-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">{client.report.bureau || 'Client record'} {client.report.reportReference ? `· ${client.report.reportReference}` : ''}</p>
          <h2>{client.fullName || 'Unnamed client'}</h2>
          <p>{client.idNumber || 'ID not captured'} · {client.applicationType} · Score {client.scoreFound ? client.creditScore : 'Not found'} · {client.status}</p>
        </div>
        <div className="hero-actions"><span className={`urgency ${client.coach.urgency.toLowerCase()}`}>{client.coach.urgency}</span><strong>{client.serviceType}</strong><div className="button-row"><button className="ghost light" onClick={props.onEdit}>Edit client details</button><button className="ghost light" onClick={props.onUpload}>Upload report</button></div></div>
      </section>

      {(Boolean(props.warnings?.length) || props.confidence !== undefined) && (
        <section className="panel compact-panel">
          <div className="section-heading"><h3>Parser quality</h3>{props.confidence !== undefined && <span className="pill">Confidence {props.confidence}%</span>}</div>
          {(props.warnings || []).map((warning) => <div className="alert warn" key={warning}>{warning}</div>)}
          {!props.warnings?.length && <div className="alert success">The report passed the current parser checks.</div>}
        </section>
      )}

      <section className="metric-grid">
        <article><span>Outstanding debt</span><strong>{money(client.coach.totals.outstanding)}</strong></article>
        <article><span>Total arrears</span><strong>{money(client.coach.totals.arrears)}</strong></article>
        <article><span>Current instalments</span><strong>{money(client.coach.totals.originalInstalment)}</strong></article>
        <article><span>Capture complete</span><strong>{client.detailsCompletion}%</strong></article>
      </section>

      <section className="panel client-summary">
        <div className="section-heading"><div><p className="eyebrow">Captured information</p><h2>Personal and banking summary</h2></div><span className="pill">{client.applicationType}</span></div>
        <div className="summary-grid">
          <article><span>Primary contact</span><strong>{client.phone || 'Not captured'}</strong><small>{client.email || 'Email not captured'}</small></article>
          <article><span>Employment</span><strong>{client.employer || 'Not captured'}</strong><small>{client.occupation || 'Occupation not captured'}</small></article>
          <article><span>Nett income</span><strong>{money(client.nettSalary)}</strong><small>Budget {money(client.monthlyLivingExpenses)}</small></article>
          <article><span>Bank account</span><strong>{client.bank.bankName || 'Not captured'}</strong><small>{client.bank.accountType || 'Account type not captured'} · •••{client.bank.accountNumber.slice(-4) || '----'}</small></article>
          {client.applicationType === 'Joint' && <article><span>Joint applicant</span><strong>{client.spouse.fullName || [client.spouse.firstName, client.spouse.surname].filter(Boolean).join(' ') || 'Not captured'}</strong><small>{client.spouse.idNumber || 'ID not captured'}</small></article>}
        </div>
      </section>

      <SalesCoachPanel coach={client.coach} />

      <section className="panel">
        <div className="section-heading"><div><p className="eyebrow">Parsed debt accounts</p><h2>{client.accounts.length} accounts · {included.length} included</h2></div><span className="pill">CPA + NLR</span></div>
        {client.accounts.length ? (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Source</th><th>Creditor</th><th>Account</th><th>Status</th><th>Opening</th><th>Balance</th><th>Arrears</th><th>Instalment</th><th>Reduced</th><th>Last paid</th></tr></thead>
              <tbody>{client.accounts.map((account) => (
                <tr key={account.id} className={!account.included ? 'excluded' : ''}>
                  <td><span className="tiny-pill">{account.parserSource}</span></td>
                  <td><strong>{account.creditorName}</strong><small>{account.accountType}</small>{account.isFurniture && <em>Furniture</em>}{account.isAsset && <em>Asset</em>}</td>
                  <td>{account.accountNumber}</td><td>{account.status}</td><td>{money(account.openingBalance)}</td><td>{money(account.currentBalance)}</td><td>{money(account.arrears)}</td><td>{money(account.monthlyInstallment)}</td><td>{money(account.reducedAmount)}</td><td>{account.lastPaidDate || '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <div className="alert info">No credit report accounts are attached to this manually created client yet.</div>}
      </section>
    </div>
  );
}

function ClientsView(props: { clients: Client[]; select: (client: Client) => void; createNew: () => void; busy: boolean }) {
  return (
    <section className="panel">
      <div className="section-heading"><div><p className="eyebrow">Tenant database</p><h2>Clients</h2></div><div className="button-row"><span className="pill">{props.clients.length} records</span><button className="primary" onClick={props.createNew} disabled={props.busy}>{props.busy ? 'Creating…' : 'New client'}</button></div></div>
      {!props.clients.length ? <div className="empty-state"><h2>No clients yet</h2><p>Create a manual client record or upload the first report.</p><button className="primary" onClick={props.createNew}>Create client</button></div> : (
        <div className="client-list">{props.clients.map((rawClient) => {
          const client = normalizeClient(rawClient);
          return (
            <button key={client.id} onClick={() => props.select(client)}>
              <div><strong>{client.fullName || 'Unnamed client'}</strong><span>{client.idNumber || 'ID not captured'} · {client.applicationType} · {client.report.bureau || 'No report'}</span></div>
              <div><b>{client.serviceType}</b><span>{client.detailsCompletion}% captured · {money(client.coach.totals.outstanding)}</span></div>
            </button>
          );
        })}</div>
      )}
    </section>
  );
}

export default function App() {
  const [view, setView] = useState<View>('dashboard');
  const [clients, setClients] = useState<Client[]>([]);
  const [selected, setSelected] = useState<Client | null>(null);
  const [parseMeta, setParseMeta] = useState<{ warnings: string[]; confidence?: number }>({ warnings: [] });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [creating, setCreating] = useState(false);

  const loadClients = async () => {
    const result = await api<{ clients: Client[] }>('/api/clients');
    const normalized = (result.clients || []).map(normalizeClient);
    setClients(normalized);
    setSelected((current) => current || normalized[0] || null);
  };

  useEffect(() => {
    loadClients()
      .catch((error) => setLoadError((error as Error).message))
      .finally(() => setLoading(false));
  }, []);

  const dashboard = useMemo(() => {
    const totalDebt = clients.reduce((sum, client) => sum + client.coach.totals.outstanding, 0);
    const totalArrears = clients.reduce((sum, client) => sum + client.coach.totals.arrears, 0);
    return {
      totalDebt,
      totalArrears,
      removals: clients.filter((client) => client.serviceType === 'Debt Review Removal').length,
      mediation: clients.filter((client) => client.serviceType === 'Debt Mediation').length,
      cpi: clients.filter((client) => client.serviceType === 'Credit Profile Investigation').length
    };
  }, [clients]);

  const updateClientState = (client: Client) => {
    const normalized = normalizeClient(client);
    setSelected(normalized);
    setClients((previous) => [normalized, ...previous.filter((item) => item.id !== normalized.id)]);
  };

  const parsed = (result: ParseResponse) => {
    const client = normalizeClient({ ...result.client, id: result.clientId });
    updateClientState(client);
    setParseMeta({ warnings: result.warnings || [], confidence: result.confidence });
    setView('capture');
  };

  const createClient = async () => {
    setCreating(true);
    setLoadError('');
    try {
      const result = await api<{ success: boolean; client: Client }>('/api/clients', { method: 'POST', body: JSON.stringify({ applicationType: 'Single' }) });
      const client = normalizeClient(result.client);
      updateClientState(client);
      setParseMeta({ warnings: [] });
      setView('capture');
    } catch (error) {
      setLoadError((error as Error).message);
    } finally {
      setCreating(false);
    }
  };

  const nav: { key: View; label: string; note: string }[] = [
    { key: 'dashboard', label: 'Dashboard', note: 'Sales Coach and opportunity' },
    { key: 'upload', label: 'Upload report', note: 'Protected PDF parser' },
    { key: 'capture', label: 'Client capture', note: 'Personal, joint and banking' },
    { key: 'clients', label: 'Clients', note: 'Khusela client database' }
  ];

  if (loading) return <main className="loading-page"><div className="spinner" /><p>Loading Fin-Tastic…</p></main>;

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand-lockup"><div className="brand-mark">F</div><div><strong>Fin-Tastic</strong><span>Sales Coach</span></div></div>
        <div className="tenant-card"><span>Active tenant</span><strong>Khusela Debt Management</strong><small>Open access — logins temporarily disabled</small></div>
        <nav>{nav.map((item) => <button key={item.key} className={view === item.key ? 'active' : ''} onClick={() => { setView(item.key); setSidebarOpen(false); }}><strong>{item.label}</strong><span>{item.note}</span></button>)}</nav>
        <button className="primary sidebar-new" onClick={createClient} disabled={creating}>{creating ? 'Creating…' : '+ New client'}</button>
        <div className="sidebar-footer"><strong>Opportunity rules active</strong><span>DR · DRR · Mediation · Credit Profile Investigation</span></div>
      </aside>
      <main className="main-panel">
        <header className="topbar">
          <button className="menu-button" onClick={() => setSidebarOpen((open) => !open)}>☰</button>
          <div><p className="eyebrow">Render deployment</p><h1>{nav.find((item) => item.key === view)?.label}</h1></div>
          <div className="topbar-status"><span className="status-dot" />Open access</div>
        </header>

        {loadError && <div className="alert danger">{loadError}</div>}
        {view === 'upload' && <UploadView onParsed={parsed} />}
        {view === 'clients' && <ClientsView clients={clients} select={(client) => { setSelected(client); setParseMeta({ warnings: [] }); setView('dashboard'); }} createNew={createClient} busy={creating} />}
        {view === 'capture' && (selected ? <ClientCapture client={selected} onSaved={updateClientState} onOpenCoach={() => setView('dashboard')} /> : <section className="panel empty-state"><h2>Select or create a client</h2><p>The capture screen stores personal, joint application, employment and banking information.</p><button className="primary" onClick={createClient}>Create client</button></section>)}
        {view === 'dashboard' && (
          <div className="view-stack">
            <section className="metric-grid dashboard-metrics">
              <article><span>Clients</span><strong>{clients.length}</strong></article>
              <article><span>Total debt found</span><strong>{money(dashboard.totalDebt)}</strong></article>
              <article><span>Total arrears</span><strong>{money(dashboard.totalArrears)}</strong></article>
              <article><span>CPI opportunities</span><strong>{dashboard.cpi}</strong></article>
            </section>
            <div className="route-strip"><span>Removal {dashboard.removals}</span><span>Mediation {dashboard.mediation}</span><span>Credit Profile Investigation {dashboard.cpi}</span></div>
            {selected ? <ClientDetail client={selected} warnings={parseMeta.warnings} confidence={parseMeta.confidence} onEdit={() => setView('capture')} onUpload={() => setView('upload')} /> : <section className="panel empty-state"><h2>Ready for the first client</h2><p>Create a client to capture personal and banking information, or upload a Datanamix report to activate the Sales Opportunity Engine.</p><div className="button-row"><button className="secondary" onClick={createClient}>Create client</button><button className="primary" onClick={() => setView('upload')}>Upload credit report</button></div></section>}
          </div>
        )}
      </main>
    </div>
  );
}
