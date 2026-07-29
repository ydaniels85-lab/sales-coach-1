import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useState } from 'react';

type ViewKey = 'dashboard' | 'clients' | 'upload' | 'profile' | 'coach' | 'accounts' | 'mandate' | 'documents' | 'workflow' | 'admin' | 'settings';
type ServiceType = 'Debt Review Sales Coach' | 'Debt Review Removal' | 'Debt Mediation' | 'Needs Manual Review';
type Urgency = 'Low' | 'Medium' | 'High';

type Tenant = { id: string; name: string; ncr: string; userCount: number; clientCount: number };
type TenantUser = { id: string; name: string; role: string; email: string; isActive?: boolean; isPlatformOwner?: boolean };

type Applicant = {
  firstName: string;
  secondName: string;
  surname: string;
  dateOfBirth: string;
  gender: string;
  maritalStatus: string;
  fullName: string;
  idNumber: string;
  email: string;
  phone: string;
  whatsapp: string;
  physicalAddress: string;
  employer: string;
  occupation: string;
  dateEmployed: string;
  salaryFrequency: 'Weekly' | 'Fortnightly' | 'Monthly';
  grossSalary: number;
  nettSalary: number;
};

type BankDetails = {
  accountHolder: string;
  bankName: string;
  accountType: 'Cheque' | 'Savings' | 'Transmission' | 'Current' | '';
  branchCode: string;
  accountNumber: string;
  debitDay: string;
  mandateAccepted: boolean;
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
  parserSource?: string;
  rawLine?: string;
};

type CoachConversationStep = { stage: string; objective: string; script: string };
type CoachObjection = { objection: string; response: string; followUp: string };

type CoachResult = {
  service: ServiceType;
  urgency: Urgency;
  headline: string;
  reasons: string[];
  nextSteps: string[];
  objectionHandlers: string[];
  callOpening: string;
  permissionQuestion: string;
  discoveryQuestions: string[];
  conversationGuide: CoachConversationStep[];
  valuePoints: string[];
  objections: CoachObjection[];
  closingScript: string;
  complianceReminders: string[];
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
  };
};

type DocumentItem = { name: string; status: string; filename?: string; uploadedAt?: string; source?: string; notes?: string };
type ClientDocuments = { required: string[]; items: DocumentItem[]; requestStatus: string; sentAt?: string; uploadLink?: string };
type ClientSignature = { status: string; link?: string; sentAt?: string; signedAt?: string };
type NuPayMandate = { status: string; mandateId?: string; link?: string; amount: number; debitDay: string; sentAt?: string; cancelledAt?: string; history: { at: string; action: string; amount?: number; debitDay?: string; reason?: string }[] };
type AdminHandover = { status: string; submittedAt?: string; submittedBy?: string; notes?: string; snapshot?: Record<string, unknown> };
type PdaInfo = { pdaName: string; pdaReference: string; proposalAmount: number; paymentStartDate: string; status: string; notes: string };

type Client = Applicant & {
  id: string;
  tenantId: string;
  assignedUserId: string;
  applicationType: 'Single' | 'Joint';
  spouse: Applicant;
  bank: BankDetails;
  creditScore: number | null;
  scoreFound?: boolean;
  debtReviewListed: boolean;
  notes: string;
  status: string;
  serviceType: ServiceType;
  accounts: DebtAccount[];
  coach?: CoachResult;
  portalLinks?: { signatureLink?: string; uploadLink?: string; createdAt?: string };
  documents?: ClientDocuments;
  signature?: ClientSignature;
  nupayMandate?: NuPayMandate;
  adminHandover?: AdminHandover;
  pdaInfo?: PdaInfo;
  createdAt?: string;
  updatedAt?: string;
};

type ParseResult = {
  success: boolean;
  bureau?: string;
  confidence?: number;
  filename?: string;
  warnings?: string[];
  tenantId?: string;
  clientId?: string;
  client?: Client;
  accounts?: DebtAccount[];
  coach?: CoachResult;
  clients?: Client[];
  error?: string;
  parserDebug?: { bureau?: string; textLength?: number; ocrAvailable?: boolean; ocrUsed?: boolean; datanamixSubscriberBlocks?: number; accountCount?: number };
};

const drrFee = 7000;

const emptyApplicant = (): Applicant => ({
  firstName: '',
  secondName: '',
  surname: '',
  dateOfBirth: '',
  gender: '',
  maritalStatus: '',
  fullName: '',
  idNumber: '',
  email: '',
  phone: '',
  whatsapp: '',
  physicalAddress: '',
  employer: '',
  occupation: '',
  dateEmployed: '',
  salaryFrequency: 'Monthly',
  grossSalary: 0,
  nettSalary: 0
});

const emptyCoach = (): CoachResult => ({
  service: 'Needs Manual Review',
  urgency: 'Low',
  headline: 'Create or select a client',
  reasons: ['Add a client or upload a credit report to generate the sales route.'],
  nextSteps: ['Verify the report and affordability information before recommending a product.'],
  objectionHandlers: [],
  callOpening: 'Good day. My name is [consultant name] from [company]. I would like to verify a few details before recommending any service. Is this a good time?',
  permissionQuestion: 'May I confirm your current debts, affordability and debt-review status?',
  discoveryQuestions: ['Have you ever been under debt review?', 'Which payments are currently placing you under pressure?', 'What is your verified nett income and essential expenditure?'],
  conversationGuide: [{ stage: 'Verify first', objective: 'Collect reliable facts.', script: 'Do not recommend a product until the report and affordability details are confirmed.' }],
  valuePoints: ['A fact-based recommendation instead of a generic sale.'],
  objections: [],
  closingScript: 'Let us complete the missing information first, and then I can give you a clear recommendation.',
  complianceReminders: ['Do not guarantee an outcome or present unverified parser figures as final.'],
  totals: { outstanding: 0, arrears: 0, originalInstalment: 0, reducedInstalment: 0, estimatedRelief: 0 },
  flags: { debtReviewListed: false, hasAsset: false, hasFurniture: false, scoreZeroRule: false, doubleSaleCandidate: false }
});


const requiredDocumentsFor = (service: ServiceType): string[] => {
  const common = ['POPIA consent', 'ID copy', 'Proof of address', 'Latest payslip', '3 months bank statements', 'Credit report'];
  if (service === 'Debt Review Removal') return [...common, 'DR removal mandate', 'NCT/court order if available', 'Paid-up letters where applicable', 'Clearance or termination evidence', 'NuPay mandate'];
  if (service === 'Debt Review Sales Coach') return [...common, 'Form 16', '17.1 notice', 'COB request authority', 'Budget and affordability sheet', 'NuPay mandate'];
  if (service === 'Debt Mediation') return [...common, 'Mediation mandate', 'Creditor proposal authority', 'Settlement/arrangement mandate', 'NuPay mandate'];
  return [...common, 'Service mandate', 'NuPay mandate'];
};

const defaultDocuments = (service: ServiceType): ClientDocuments => ({
  required: requiredDocumentsFor(service),
  items: requiredDocumentsFor(service).map((name) => ({ name, status: 'Missing' })),
  requestStatus: 'Not Sent',
  sentAt: '',
  uploadLink: ''
});

const defaultSignature = (): ClientSignature => ({ status: 'Not Sent', link: '', sentAt: '', signedAt: '' });
const defaultNuPay = (): NuPayMandate => ({ status: 'Not Sent', mandateId: '', link: '', amount: 0, debitDay: '25', sentAt: '', cancelledAt: '', history: [] });
const defaultAdminHandover = (): AdminHandover => ({ status: 'Not Submitted', submittedAt: '', submittedBy: '', notes: '', snapshot: {} });
const defaultPda = (): PdaInfo => ({ pdaName: '', pdaReference: '', proposalAmount: 0, paymentStartDate: '', status: 'Not Submitted', notes: '' });

const withWorkflowDefaults = (client: Client): Client => {
  const service = (client.serviceType || client.coach?.service || 'Needs Manual Review') as ServiceType;
  const required = requiredDocumentsFor(service);
  const previousItems = client.documents?.items || [];
  const existingItems = new Map(previousItems.map((item) => [item.name, item]));
  const extraItems = previousItems.filter((item) => !required.includes(item.name));
  const documents: ClientDocuments = {
    required,
    items: [...required.map((name) => existingItems.get(name) || { name, status: 'Missing' }), ...extraItems],
    requestStatus: client.documents?.requestStatus || 'Not Sent',
    sentAt: client.documents?.sentAt || '',
    uploadLink: client.documents?.uploadLink || client.portalLinks?.uploadLink || ''
  };
  return {
    ...client,
    bank: client.bank || { accountHolder: '', bankName: '', accountType: '', branchCode: '', accountNumber: '', debitDay: '25', mandateAccepted: false },
    spouse: client.spouse || emptyApplicant(),
    accounts: client.accounts || [],
    documents,
    signature: { ...defaultSignature(), ...(client.signature || {}), link: client.signature?.link || client.portalLinks?.signatureLink || '' },
    nupayMandate: { ...defaultNuPay(), ...(client.nupayMandate || {}), amount: toNumber(client.nupayMandate?.amount || client.coach?.totals.reducedInstalment || 0), debitDay: client.nupayMandate?.debitDay || client.bank?.debitDay || '25', history: client.nupayMandate?.history || [] },
    adminHandover: { ...defaultAdminHandover(), ...(client.adminHandover || {}) },
    pdaInfo: { ...defaultPda(), ...(client.pdaInfo || {}), proposalAmount: toNumber(client.pdaInfo?.proposalAmount || client.coach?.totals.reducedInstalment || 0) }
  };
};

const newLocalClient = (tenantId: string, userId: string): Client => ({
  id: `local-${Date.now()}`,
  tenantId,
  assignedUserId: userId,
  applicationType: 'Single',
  ...emptyApplicant(),
  fullName: 'New Client',
  spouse: emptyApplicant(),
  bank: { accountHolder: '', bankName: '', accountType: '', branchCode: '', accountNumber: '', debitDay: '25', mandateAccepted: false },
  creditScore: null,
  scoreFound: false,
  debtReviewListed: false,
  notes: '',
  status: 'Lead Received',
  serviceType: 'Needs Manual Review',
  accounts: [],
  coach: emptyCoach(),
  documents: defaultDocuments('Needs Manual Review'),
  signature: defaultSignature(),
  nupayMandate: defaultNuPay(),
  adminHandover: defaultAdminHandover(),
  pdaInfo: defaultPda()
});

function currency(value: number | string | undefined): string {
  const numberValue = typeof value === 'string' ? Number(value || 0) : Number(value || 0);
  return new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR' }).format(Number.isFinite(numberValue) ? numberValue : 0);
}

function toNumber(value: string | number | boolean | undefined): number {
  if (typeof value === 'number') return Number.isFinite(value) ? value : 0;
  const parsed = Number(String(value ?? '').replace(/[^0-9.-]/g, ''));
  return Number.isFinite(parsed) ? parsed : 0;
}

function suggestReducedAmount(balance: number, installment: number): number {
  if (balance <= 0 && installment <= 0) return 0;
  const balanceBased = balance * 0.015;
  const installmentBased = installment > 0 ? installment * 0.65 : 0;
  let suggested = Math.max(100, balanceBased, installmentBased);
  if (installment > 0) suggested = Math.min(suggested, installment);
  return Math.round(suggested / 10) * 10;
}

function isBadParsedAccount(account: DebtAccount): boolean {
  const creditor = String(account.creditorName || '').trim().toLowerCase();
  const accountNumber = String(account.accountNumber || '').trim();
  const badWords = ['total no', 'total number', 'counts', 'payment profile', 'account summary', 'enquiry', 'friday', 'monday', 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday', 'months in arrears'];
  if (!creditor || creditor === 'unknown creditor') return true;
  if (badWords.some((word) => creditor.includes(word))) return true;
  const weakOnly = creditor.split(/\W+/).filter(Boolean).every((word) => ['total', 'no', 'of', 'account', 'accounts', 'credit', 'current', 'status', 'balance'].includes(word));
  if (weakOnly) return true;
  const largestValue = Math.max(toNumber(account.openingBalance), toNumber(account.currentBalance), toNumber(account.arrears), toNumber(account.monthlyInstallment), toNumber(account.reducedAmount));
  if (!accountNumber && largestValue < 100) return true;
  return false;
}

function evaluateCoach(client: Client, accounts: DebtAccount[]): CoachResult {
  const included = accounts.filter((account) => account.included);
  const outstanding = included.reduce((sum, account) => sum + toNumber(account.currentBalance), 0);
  const arrears = included.reduce((sum, account) => sum + toNumber(account.arrears), 0);
  const originalInstalment = included.reduce((sum, account) => sum + toNumber(account.monthlyInstallment), 0);
  const reducedInstalment = included.reduce((sum, account) => sum + toNumber(account.reducedAmount), 0);
  const estimatedRelief = Math.max(0, originalInstalment - reducedInstalment);
  const hasAsset = included.some((account) => account.isAsset || /vehicle|home loan|bond|mortgage|wesbank|mfc/i.test(account.creditorName));
  const hasFurniture = included.some((account) => account.isFurniture || /russells|bradlows|lewis|furniture|beares|jd/i.test(account.creditorName));
  const scoreIsKnown = Boolean(client.scoreFound) && client.creditScore !== null && client.creditScore !== undefined && String(client.creditScore) !== '';
  const numericScore = scoreIsKnown ? Number(client.creditScore) : null;
  const scoreZeroRule = scoreIsKnown && numericScore === 0;
  const debtReviewListed = Boolean(client.debtReviewListed || scoreZeroRule);
  const firstName = (client.firstName || client.fullName || 'the client').trim().split(/\s+/)[0];

  let service: ServiceType = 'Debt Mediation';
  let urgency: Urgency = 'Medium';
  let headline = 'Debt mediation opportunity detected';
  const reasons: string[] = [];
  let nextSteps: string[] = [];
  let callOpening = '';
  let permissionQuestion = '';
  let discoveryQuestions: string[] = [];
  let conversationGuide: CoachConversationStep[] = [];
  let valuePoints: string[] = [];
  let objections: CoachObjection[] = [];
  let closingScript = '';

  if (debtReviewListed) {
    service = 'Debt Review Removal';
    urgency = 'High';
    headline = 'Debt Review Removal lead';
    reasons.push('The report indicates a confirmed debt-review flag or a genuinely detected score of zero, so removal must be assessed first.');
    if (outstanding > 0) reasons.push('Balances still show, creating a possible second sale for mediation after the removal assessment.');
  } else if (hasAsset) {
    service = 'Debt Review Sales Coach';
    urgency = 'High';
    headline = 'Asset-protection opportunity';
    reasons.push('A home-loan or vehicle-finance type account was detected. Lead with affordability and protecting the asset, subject to eligibility.');
  } else if (scoreIsKnown && numericScore !== null && numericScore >= 400 && numericScore <= 650 && arrears > 0) {
    service = 'Debt Mediation';
    urgency = 'High';
    headline = 'Debt mediation lead with arrears pressure';
    reasons.push('The score and arrears pattern indicate immediate affordability pressure that may benefit from negotiated relief.');
  } else if (outstanding > 0) {
    service = 'Debt Mediation';
    reasons.push('Outstanding balances are present and can be assessed for a coordinated, affordable repayment proposal.');
  } else {
    service = 'Needs Manual Review';
    urgency = 'Low';
    headline = 'Manual assessment needed';
    reasons.push('The available report data is not sufficient to recommend a product safely.');
  }

  if (hasFurniture) reasons.push('Furniture accounts were detected. Confirm the status of the goods and explain the account clearly.');
  if (originalInstalment > 0) reasons.push(`The working proposal shows estimated monthly relief of ${currency(estimatedRelief)}, subject to affordability checks and creditor acceptance.`);

  if (service === 'Debt Review Removal') {
    nextSteps = ['Confirm whether the client is actively under debt review or only remains bureau-listed.', 'Request Form 17 documents, court/NCT order, PDA statement and paid-up evidence.', 'Explain the R7,000 fee and 1-3 month options without promising an outcome.', 'Assess mediation separately if active balances remain.'];
    callOpening = `Good day ${firstName}. My name is [consultant name] from [company]. I have reviewed the credit report information available to us, and it appears that a debt-review indicator may still be affecting the profile. I would like to ask a few questions to establish whether the listing is still active and what the correct removal process would be. Is this a good time to continue?`;
    permissionQuestion = 'Before I explain the process, may I confirm what happened with the previous debt-review matter and what result you are hoping to achieve now?';
    discoveryQuestions = ['Are you still paying through a debt counsellor or PDA?', 'Did you receive a court order, NCT order, Form 17.2 or clearance certificate?', 'Are all accounts paid up, or do balances remain?', 'When did you last speak to the debt counsellor?', 'Have you tried to remove the listing before?', 'Why do you need the listing addressed now?'];
    conversationGuide = [
      { stage: '1. Confirm the problem', objective: 'Separate an active process from a lingering bureau listing.', script: 'I want to separate the bureau listing from any active balances, because each issue may require a different solution.' },
      { stage: '2. Explain the route', objective: 'Explain the assessment and document process honestly.', script: 'We first verify the status and documents, then determine the appropriate removal route. No outcome can be guaranteed before assessment.' },
      { stage: '3. Present the service', objective: 'Connect the service to the client’s stated goal.', script: 'Based on what you have told me, the next practical step is a formal removal assessment and document collection.' },
      { stage: '4. Confirm affordability', objective: 'Discuss the fee and payment options.', script: 'The service fee is R7,000, payable once off or over up to three months. Which structure is realistic for you?' },
      { stage: '5. Secure the next action', objective: 'Obtain consent, documents and mandate.', script: 'I can send one secure link for the required documents and signature so we can begin the assessment.' }
    ];
    valuePoints = ['Structured assessment of the current debt-review status.', 'Guidance for bureau, debt counsellor, PDA, NCT or court documents.', 'Clear separation between removal and remaining debt.', 'Progress tracking through the admin workflow.'];
    objections = [
      { objection: 'I already paid my debt counsellor.', response: 'Payment may support the matter, but it does not confirm that the bureau indicator was removed. We still need to verify the status and evidence.', followUp: 'Do you have a clearance certificate, paid-up letters or final PDA statement?' },
      { objection: 'I only want my name cleared.', response: 'That is the objective of the assessment. Active balances must still be explained because removing an indicator does not erase valid debt.', followUp: 'May I show you which accounts still have balances?' },
      { objection: 'Why does it cost R7,000?', response: 'The fee covers investigation, document preparation, communication and the applicable workflow. It is not a payment to guarantee a result.', followUp: 'Would once off, two months or three months suit you better?' },
      { objection: 'Another company can do it immediately.', response: 'A responsible provider must first verify the legal and bureau status. Immediate removal cannot be promised without the facts and documents.', followUp: 'Would you like me to explain exactly what must be verified?' },
      { objection: 'I need to think about it.', response: 'That is understandable. Let us make sure the status, documents, fee and route are clear so your decision is informed.', followUp: 'Which part do you need more clarity on?' },
      { objection: 'I cannot afford the fee now.', response: 'A payment arrangement of up to three months can be considered if it is genuinely affordable.', followUp: 'What monthly amount would be realistic without adding pressure?' }
    ];
    closingScript = 'From what we have confirmed, the appropriate next step is the removal assessment. I will send the secure signature and document link, and we will only proceed once you understand the service, fee and required evidence. Shall we complete that now?';
  } else if (service === 'Debt Review Sales Coach') {
    nextSteps = ['Confirm income, living expenses, arrears and the status of the home or vehicle account.', 'Explain debt review as an affordability and asset-protection process, subject to eligibility.', 'Complete the budget and consent before Form 16, notices and COB requests.'];
    callOpening = `Good day ${firstName}. My name is [consultant name] from [company]. The report shows a home-loan or vehicle-finance type account, so I would like to understand whether the current repayments are placing the asset under pressure. My role is to assess the affordability problem and explain the available regulated options. Is this a good time to ask a few questions?`;
    permissionQuestion = 'May I first understand what changed in your finances and which payment is causing the most pressure?';
    discoveryQuestions = ['Are the home or vehicle payments up to date?', 'Have you received a demand, summons, cancellation or repossession warning?', 'What is the current nett household income?', 'What essential living expenses must be protected?', 'Which creditor payment is most difficult?', 'Have you previously applied for debt review?'];
    conversationGuide = [
      { stage: '1. Identify the pressure', objective: 'Understand the trigger and urgency.', script: 'Let us identify the payment that is no longer sustainable and whether the asset is already at risk.' },
      { stage: '2. Complete affordability', objective: 'Use verified income and expenses.', script: 'I need the full household budget so any recommendation is based on what you can genuinely afford.' },
      { stage: '3. Explain debt review', objective: 'Explain the regulated process without fear-based selling.', script: 'Debt review can restructure qualifying obligations and may assist with asset protection while the consumer complies, but eligibility and timelines must be assessed.' },
      { stage: '4. Show working relief', objective: 'Compare current and proposed amounts.', script: `The included instalments total about ${currency(originalInstalment)}; the working proposal is about ${currency(reducedInstalment)}, subject to the formal process.` },
      { stage: '5. Obtain informed consent', objective: 'Secure the next action.', script: 'If the option is suitable, the next step is consent, documents and the full affordability application.' }
    ];
    valuePoints = ['One affordability assessment across included credit agreements.', 'A regulated process with notices, balances and a formal proposal.', 'Focus on sustainable living expenses and qualifying asset protection.', 'Documented admin and PDA handover.'];
    objections = [
      { objection: 'I do not want debt review.', response: 'I understand. My role is to assess whether the current payments are sustainable and explain the consequences and alternatives accurately, not to force the option.', followUp: 'What concerns you most about debt review?' },
      { objection: 'I can catch up next month.', response: 'That may be possible, but we should compare the arrears and instalments with actual disposable income before relying on that plan.', followUp: 'After essential expenses, how much is genuinely available next month?' },
      { objection: 'Will I lose my car or house?', response: 'No honest adviser can give a blanket guarantee. Risk depends on account status, legal action and compliance. Early assessment is important.', followUp: 'Have you received any formal enforcement notice?' },
      { objection: 'Will I be blacklisted?', response: 'Debt review is reflected while active and access to new credit is restricted. The aim is rehabilitation through an affordable plan.', followUp: 'Is the priority new credit, or stabilising existing obligations?' },
      { objection: 'I need another loan instead.', response: 'More borrowing may increase pressure. We should first establish whether the current debt is already unaffordable.', followUp: 'Can we review the budget before adding another repayment?' },
      { objection: 'I need to speak to my spouse.', response: 'That is appropriate, especially for a joint household or marriage in community of property. We can explain it to both applicants.', followUp: 'When can we arrange a call with both of you?' }
    ];
    closingScript = 'The information suggests that a full affordability assessment is the responsible next step. I will send the consent and document link so the figures can be verified before any formal recommendation. Shall we start with that assessment?';
  } else if (service === 'Debt Mediation') {
    nextSteps = ['Confirm all income, living expenses, debit orders and creditor payments.', 'Agree included accounts and realistic reduced amounts.', 'Explain creditor acceptance and send the mediation mandate and document link.'];
    callOpening = `Good day ${firstName}. My name is [consultant name] from [company]. The report shows active balances that may be placing the monthly budget under pressure. I would like to understand the affordability gap and explain how a coordinated creditor proposal could work. Is this a good time to continue?`;
    permissionQuestion = 'May I ask what you are currently paying, what you can realistically afford, and what caused the pressure?';
    discoveryQuestions = ['Which accounts are in arrears or likely to fall behind?', 'What is your verified nett income and salary date?', 'What are the essential living expenses?', 'Are there deductions not shown on the report?', 'Have creditors offered arrangements?', 'What total debt payment can you maintain?'];
    conversationGuide = [
      { stage: '1. Understand the shortfall', objective: 'Identify why payments are not sustainable.', script: 'Let us compare the full creditor commitment with what remains after essential expenses.' },
      { stage: '2. Prioritise accounts', objective: 'Confirm negotiation and legal urgency.', script: 'We will review every included creditor, arrears status and enforcement communication.' },
      { stage: '3. Build the proposal', objective: 'Create a realistic working amount.', script: `Current instalments total about ${currency(originalInstalment)}; the working reduced total is ${currency(reducedInstalment)}, subject to confirmation and acceptance.` },
      { stage: '4. Explain expectations', objective: 'Avoid implying guaranteed acceptance.', script: 'Creditors may accept, counter or decline. The client must maintain agreed payments and keep information current.' },
      { stage: '5. Secure the mandate', objective: 'Obtain authority and documents.', script: 'Once the mandate and documents are complete, the admin team can begin the creditor process.' }
    ];
    valuePoints = ['One coordinated view of included creditor payments.', 'A proposal based on verified affordability.', 'Centralised communication and progress tracking.', 'Clear payment and mandate records.'];
    objections = [
      { objection: 'I can pay creditors myself.', response: 'You may. Mediation is useful when separate arrangements are difficult to coordinate or the total remains unaffordable.', followUp: 'Have the arrangements reduced the total to a sustainable amount?' },
      { objection: 'I am not in arrears yet.', response: 'Acting early can prevent missed promises if the budget already shows a shortfall.', followUp: 'After essential expenses, can every contractual instalment be paid this month?' },
      { objection: 'Can you guarantee lower payments?', response: 'No. We can prepare and motivate a proposal, but creditors must consider it.', followUp: 'Would you like to review the working amount and assumptions?' },
      { objection: 'Do not contact my creditors.', response: 'No contact should occur without informed authority. We explain the mandate before it is signed.', followUp: 'Which part of creditor communication concerns you?' },
      { objection: 'I need more time.', response: 'That is fair, but arrears, fees or legal action may continue, so set a specific follow-up date.', followUp: 'What information do you need, and when should we speak again?' },
      { objection: 'The payment is still too high.', response: 'Then we should not proceed with an unrealistic figure. Recheck the budget and included accounts.', followUp: 'Which verified expense or income item is missing?' }
    ];
    closingScript = 'The next step is to confirm the budget and obtain your mandate so the proposal can be prepared accurately. This does not guarantee creditor acceptance, but it gives authority to begin the structured process. Shall I send the secure link now?';
  } else {
    nextSteps = ['Verify the report and capture missing client, income and account details.', 'Do not recommend a service until debt-review status, balances and affordability are confirmed.'];
    callOpening = `Good day ${firstName}. My name is [consultant name] from [company]. I do not yet have enough reliable information to recommend a service, so I would like to verify a few details first. Is this a good time?`;
    permissionQuestion = 'May I confirm your current debts, income, arrears and whether you have ever been under debt review?';
    discoveryQuestions = ['Have you ever applied for debt review?', 'Which accounts are active?', 'Are any accounts in arrears or legal collections?', 'What is your nett income and essential expenditure?', 'Do you have a financed home or vehicle?'];
    conversationGuide = [{ stage: '1. Verify', objective: 'Correct missing or unreliable data.', script: 'I first need to verify the report and affordability information.' }, { stage: '2. Classify', objective: 'Identify DR status, assets, balances and arrears.', script: 'Once the facts are confirmed, I can explain which service, if any, is appropriate.' }];
    valuePoints = ['A fact-based recommendation instead of a generic sale.', 'Protection against selecting the wrong service.'];
    objections = [{ objection: 'Just tell me what I qualify for.', response: 'Reliable status, balance and affordability information is needed to avoid recommending the wrong process.', followUp: 'Can we complete the missing questions first?' }];
    closingScript = 'Let us complete the missing information first. Once verified, I can give you a clear and responsible recommendation.';
  }

  const objectionHandlers = objections.map((item) => `${item.objection}: ${item.response}`);
  const complianceReminders = ['Do not guarantee removal, creditor acceptance, asset protection, clearance or a score outcome.', 'Correct parser errors before presenting figures.', 'Obtain informed consent before documents, mandates or creditor contact.', 'Explain fees, exclusions, timelines and separate services clearly.'];
  return {
    service, urgency, headline, reasons, nextSteps, objectionHandlers,
    callOpening, permissionQuestion, discoveryQuestions, conversationGuide, valuePoints, objections, closingScript, complianceReminders,
    totals: { outstanding, arrears, originalInstalment, reducedInstalment, estimatedRelief },
    flags: { debtReviewListed, hasAsset, hasFurniture, scoreZeroRule, doubleSaleCandidate: debtReviewListed && outstanding > 0 }
  };
}

function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'good' | 'warn' | 'danger' | 'blue' | 'neutral' }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function StatCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{sub}</small>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}


const apiRequest = (input: RequestInfo | URL, init: RequestInit = {}) =>
  window.fetch(input, { ...init, credentials: 'include' });

export default function App() {
  const defaultApiBase = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://localhost:5000' : window.location.origin;
  const [apiBase, setApiBase] = useState(() => localStorage.getItem('fintastic_sales_api') || defaultApiBase);
  const [loggedIn, setLoggedIn] = useState(false);
  const [sessionChecking, setSessionChecking] = useState(true);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [sessionUser, setSessionUser] = useState<TenantUser | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState(() => localStorage.getItem('fintastic_tenant_id') || 'liberty-credit-specialists');
  const [users, setUsers] = useState<TenantUser[]>([]);
  const [userId, setUserId] = useState('');
  const [clients, setClients] = useState<Client[]>([]);
  const [client, setClient] = useState<Client>(() => newLocalClient(tenantId, userId));
  const [searchText, setSearchText] = useState('');
  const [serviceFilter, setServiceFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadMode, setUploadMode] = useState<'new' | 'existing'>('new');
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('Not saved in this session');
  const [uploadError, setUploadError] = useState('');
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [activeView, setActiveView] = useState<ViewKey>('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [drrMonths, setDrrMonths] = useState(3);
  const [adminClients, setAdminClients] = useState<Client[]>([]);
  const [handoverNotes, setHandoverNotes] = useState('');
  const [docUploadName, setDocUploadName] = useState('ID copy');
  const [tenantForm, setTenantForm] = useState({ name: '', ncr: '', adminName: '', adminEmail: '', adminPassword: '' });
  const [tenantCreateMessage, setTenantCreateMessage] = useState('');
  const [creatingTenant, setCreatingTenant] = useState(false);
  const [userForm, setUserForm] = useState({ tenantId, name: '', email: '', password: '', role: 'Consultant' });
  const [userCreateMessage, setUserCreateMessage] = useState('');
  const [creatingUser, setCreatingUser] = useState(false);

  const accounts = client.accounts || [];
  const coach = useMemo(() => evaluateCoach(client, accounts), [client, accounts]);
  const currentTenant = tenants.find((tenant) => tenant.id === tenantId);
  const currentUser = sessionUser;
  const isPlatformOwner = Boolean(currentUser?.isPlatformOwner);
  const isAdminRole = isPlatformOwner || ['Admin', 'Manager'].includes(currentUser?.role || '');

  const quickTabs: { key: ViewKey; label: string; helper: string }[] = [
    { key: 'profile', label: 'Client Info', helper: 'Details + joint' },
    { key: 'upload', label: 'Credit Report', helper: 'Upload + parse' },
    { key: 'coach', label: 'Sales Coach', helper: 'Route + script' },
    { key: 'accounts', label: 'Accounts / Fees', helper: 'Reduced amounts' },
    { key: 'documents', label: 'Docs + Signature', helper: 'Links + status' },
    { key: 'mandate', label: 'NuPay Mandate', helper: 'Send/cancel/resend' },
    { key: 'workflow', label: 'Admin / PDA', helper: 'Submit handover' }
  ];

  const apiHeaders = { 'Content-Type': 'application/json', 'X-Tenant-ID': tenantId };

  const loadTenants = async () => {
    try {
      const response = await apiRequest(`${apiBase}/api/tenants`);
      const data = await response.json();
      if (data.success) setTenants(data.tenants || []);
    } catch (error) {
      console.warn(error);
      setTenants([]);
    }
  };

  const createTenant = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreatingTenant(true);
    setTenantCreateMessage('');
    try {
      const response = await apiRequest(`${apiBase}/api/tenants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': tenantId },
        body: JSON.stringify(tenantForm)
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not create tenant');
      setTenants(data.tenants || []);
      setTenantForm({ name: '', ncr: '', adminName: '', adminEmail: '', adminPassword: '' });
      setTenantCreateMessage(`${data.tenant.name} created successfully. You remain signed in as platform owner.`);
    } catch (error) {
      setTenantCreateMessage(error instanceof Error ? error.message : 'Could not create tenant');
    } finally {
      setCreatingTenant(false);
    }
  };

  const createUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreatingUser(true);
    setUserCreateMessage('');
    try {
      const response = await apiRequest(`${apiBase}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': userForm.tenantId },
        body: JSON.stringify({ name: userForm.name, email: userForm.email, password: userForm.password, role: userForm.role })
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not create user');
      setUserForm((current) => ({ ...current, name: '', email: '', password: '', role: 'Consultant' }));
      setUserCreateMessage(`${data.user.name} ${data.activatedLegacyUser ? 'was activated' : 'was created'} in ${tenants.find((item) => item.id === userForm.tenantId)?.name || userForm.tenantId}.`);
      await loadTenants();
      if (userForm.tenantId === tenantId) await loadUsers(tenantId);
    } catch (error) {
      setUserCreateMessage(error instanceof Error ? error.message : 'Could not create user');
    } finally {
      setCreatingUser(false);
    }
  };

  const loadUsers = async (nextTenantId = tenantId) => {
    try {
      const response = await apiRequest(`${apiBase}/api/users`, { headers: { 'X-Tenant-ID': nextTenantId } });
      const data = await response.json();
      if (data.success) {
        setUsers(data.users || []);
      }
    } catch {
      setUsers([]);
    }
  };

  const loadClients = async (query = searchText, nextTenantId = tenantId) => {
    const params = new URLSearchParams();
    if (query) params.set('search', query);
    if (serviceFilter) params.set('service', serviceFilter);
    if (statusFilter) params.set('status', statusFilter);
    try {
      const response = await apiRequest(`${apiBase}/api/clients?${params.toString()}`, { headers: { 'X-Tenant-ID': nextTenantId } });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not load clients');
      const loadedClients = (data.clients || []).map((item: Client) => withWorkflowDefaults(item));
      setClients(loadedClients);
      // Important: refreshing/searching the client list must never replace the active draft/client.
      // The active client changes only when the user clicks a client, creates a new client, or uploads a report.
      const activeStillExists = loadedClients.some((item: Client) => item.id === client.id);
      if (!activeStillExists && !client.id.startsWith('local-') && client.tenantId === nextTenantId) {
        setSaveMessage('Selected client is not visible in the current search/filter, but it was not overwritten.');
      }
    } catch (error) {
      console.warn(error);
    }
  };

  useEffect(() => {
    const restoreSession = async () => {
      try {
        const response = await apiRequest(`${apiBase}/api/me`);
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.error || 'Session expired');
        setSessionUser(data.user);
        setUserId(data.user.id);
        setTenantId(data.tenant.id);
        setLoggedIn(true);
        await Promise.all([loadTenants(), loadUsers(data.tenant.id), loadClients('', data.tenant.id)]);
      } catch {
        setLoggedIn(false);
        setSessionUser(null);
      } finally {
        setSessionChecking(false);
      }
    };
    restoreSession();
  }, []);

  useEffect(() => {
    if (!loggedIn) return;
    localStorage.setItem('fintastic_tenant_id', tenantId);
    loadUsers(tenantId);
    loadClients('', tenantId);
  }, [tenantId, loggedIn]);

  useEffect(() => {
    if (!loggedIn) return;
    const timer = window.setTimeout(() => loadClients(searchText), 250);
    return () => window.clearTimeout(timer);
  }, [searchText, serviceFilter, statusFilter]);

  const setCurrentTenant = (nextTenantId: string) => {
    setTenantId(nextTenantId);
    setSearchText('');
    setServiceFilter('');
    setStatusFilter('');
    setClient(newLocalClient(nextTenantId, userId));
    setActiveView('clients');
  };

  const updateClient = <K extends keyof Client>(field: K, value: Client[K]) => {
    setClient((current) => ({ ...current, [field]: value }));
  };

  const updateClientNamePart = (field: 'firstName' | 'secondName' | 'surname', value: string) => {
    setClient((current) => {
      const next = { ...current, [field]: value };
      const joined = [next.firstName, next.secondName, next.surname].filter(Boolean).join(' ').trim();
      return { ...next, fullName: joined || next.fullName };
    });
  };

  const updateSpouse = <K extends keyof Applicant>(field: K, value: Applicant[K]) => {
    setClient((current) => ({ ...current, spouse: { ...current.spouse, [field]: value } }));
  };

  const updateBank = <K extends keyof BankDetails>(field: K, value: BankDetails[K]) => {
    setClient((current) => ({ ...current, bank: { ...current.bank, [field]: value } }));
  };

  const updateAccount = (id: string, field: keyof DebtAccount, value: string | number | boolean) => {
    setClient((current) => {
      const nextAccounts = current.accounts.map((account) => {
        if (account.id !== id) return account;
        const next = { ...account, [field]: typeof value === 'string' && ['openingBalance', 'currentBalance', 'arrears', 'monthlyInstallment', 'reducedAmount', 'monthsInArrears'].includes(field) ? toNumber(value) : value } as DebtAccount;
        if (field === 'currentBalance' || field === 'monthlyInstallment') {
          next.reducedAmount = suggestReducedAmount(toNumber(next.currentBalance), toNumber(next.monthlyInstallment));
        }
        return next;
      });
      return { ...current, accounts: nextAccounts };
    });
  };

  const addAccount = () => {
    setClient((current) => ({
      ...current,
      accounts: [
        ...current.accounts,
        {
          id: `manual-${Date.now()}`,
          creditorName: 'New Creditor',
          accountNumber: '',
          accountType: 'Credit Account',
          openingBalance: 0,
          currentBalance: 0,
          arrears: 0,
          monthlyInstallment: 0,
          reducedAmount: 0,
          lastPaidDate: '',
          monthsInArrears: 0,
          openDate: '',
          status: 'Active',
          included: true,
          isFurniture: false,
          isAsset: false
        }
      ]
    }));
  };

  const cleanParsedAccounts = () => {
    setClient((current) => {
      const cleaned = current.accounts.filter((account) => !isBadParsedAccount(account));
      if (cleaned.length === current.accounts.length) {
        alert('No obvious bad parser rows were found.');
        return current;
      }
      return { ...current, accounts: cleaned };
    });
  };

  const startNewClient = () => {
    setUploadMode('new');
    setClient(newLocalClient(tenantId, userId));
    setParseResult(null);
    setSaveMessage('New unsaved client');
    setActiveView('profile');
  };

  const saveClient = async (): Promise<Client | null> => {
    setSaving(true);
    setSaveMessage('Saving...');
    const fullNameFromParts = [client.firstName, client.secondName, client.surname].filter(Boolean).join(' ').trim();
    const body = {
      ...client,
      fullName: (client.fullName || fullNameFromParts || 'New Client').trim(),
      coach,
      serviceType: coach.service,
      scoreFound: Boolean(client.scoreFound) || (client.creditScore !== null && client.creditScore !== undefined && String(client.creditScore) !== ''),
      tenantId,
      assignedUserId: client.assignedUserId || userId
    };
    const isLocal = client.id.startsWith('local-');
    try {
      const response = await apiRequest(`${apiBase}/api/clients${isLocal ? '' : `/${client.id}`}`, {
        method: isLocal ? 'POST' : 'PUT',
        headers: apiHeaders,
        body: JSON.stringify(body)
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Save failed');
      const saved = withWorkflowDefaults(data.client);
      setClient(saved);
      setClients((current) => {
        const source = Array.isArray(data.clients) ? data.clients.map((item: Client) => withWorkflowDefaults(item)) : current;
        const exists = source.some((item: Client) => item.id === saved.id);
        return exists ? source.map((item: Client) => item.id === saved.id ? saved : item) : [saved, ...source];
      });
      setParseResult(null);
      setSaveMessage(`Saved ${saved.fullName || 'client'} at ${new Date().toLocaleTimeString()}`);
      return saved;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not save client';
      setSaveMessage(`Save failed: ${message}`);
      alert(message);
      return null;
    } finally {
      setSaving(false);
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSelectedFile(event.target.files?.[0] || null);
    setUploadError('');
  };

  const handleUpload = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedFile) {
      setUploadError('Please choose a credit report PDF first.');
      return;
    }
    setUploading(true);
    setUploadError('');
    setParseResult(null);

    try {
      const updatingExisting = uploadMode === 'existing';
      if (updatingExisting && client.id.startsWith('local-')) {
        throw new Error('Select a saved client first, or choose Upload as NEW client.');
      }
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('tenantId', tenantId);
      formData.append('userId', userId);
      const endpoint = updatingExisting ? `${apiBase}/api/clients/${client.id}/credit-report/upload` : `${apiBase}/api/upload/credit-report`;
      const response = await apiRequest(endpoint, { method: 'POST', headers: { 'X-Tenant-ID': tenantId }, body: formData });
      const data: ParseResult = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Upload failed');
      setParseResult(data);
      if (data.client) setClient(withWorkflowDefaults(data.client));
      if (data.clients) setClients(data.clients.map((item: Client) => withWorkflowDefaults(item)));
      setSaveMessage(uploadMode === 'existing' ? 'Selected client report replaced and saved.' : 'New client created from uploaded report.');
      setSelectedFile(null);
      setActiveView('coach');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed';
      setUploadError(`${message}. Make sure the backend is running on ${apiBase}.`);
    } finally {
      setUploading(false);
    }
  };

  const createPortalLinks = async () => {
    const saved = client.id.startsWith('local-') ? await saveClient() : client;
    if (!saved) return;
    try {
      const response = await apiRequest(`${apiBase}/api/portal/links`, {
        method: 'POST',
        headers: apiHeaders,
        body: JSON.stringify({ clientId: saved.id, tenantId, baseUrl: `${window.location.origin}/portal` })
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not create links');
      setClient((current) => ({ ...current, id: saved.id, portalLinks: { signatureLink: data.signatureLink, uploadLink: data.uploadLink, createdAt: data.createdAt } }));
      setSaveMessage(`Portal links saved at ${new Date().toLocaleTimeString()}`);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not create portal links');
    }
  };


  const ensureSavedClient = async (): Promise<Client | null> => {
    if (!client.id.startsWith('local-')) return client;
    return saveClient();
  };

  const updateClientFromResponse = (data: { client?: Client }) => {
    if (data.client) {
      const next = withWorkflowDefaults(data.client);
      setClient(next);
      setClients((current) => current.map((item) => item.id === next.id ? next : item).concat(current.some((item) => item.id === next.id) ? [] : [next]));
    }
  };

  const postClientAction = async (path: string, body: Record<string, unknown> = {}, method = 'POST') => {
    const saved = await ensureSavedClient();
    if (!saved) return null;
    const response = await apiRequest(`${apiBase}/api/clients/${saved.id}${path}`, {
      method,
      headers: apiHeaders,
      body: JSON.stringify({ ...body, tenantId, baseUrl: `${window.location.origin}/portal` })
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Action failed');
    updateClientFromResponse(data);
    return data;
  };

  const requestDocuments = async () => {
    try {
      await postClientAction('/documents/request');
      alert('Document upload link created and relevant document request marked as sent.');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not request documents');
    }
  };

  const simulateDocumentUpload = async () => {
    try {
      const saved = await ensureSavedClient();
      if (!saved) return;
      const form = new FormData();
      form.append('docName', docUploadName);
      form.append('filename', `${docUploadName.replace(/\s+/g, '_')}.pdf`);
      const response = await apiRequest(`${apiBase}/api/clients/${saved.id}/documents/upload`, { method: 'POST', headers: { 'X-Tenant-ID': tenantId }, body: form });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not mark document uploaded');
      updateClientFromResponse(data);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not mark document uploaded');
    }
  };

  const sendSignatureLink = async () => {
    try {
      await postClientAction('/signature/send');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not send signature link');
    }
  };

  const markSignatureSigned = async () => {
    try {
      await postClientAction('/signature/mark-signed');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not mark signature signed');
    }
  };

  const sendNupayMandate = async () => {
    try {
      const amount = client.nupayMandate?.amount || coach.totals.reducedInstalment || (coach.service === 'Debt Review Removal' ? drrFee / drrMonths : 0);
      await postClientAction('/mandate/send', { amount, debitDay: client.bank.debitDay });
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not send NuPay mandate');
    }
  };

  const cancelNupayMandate = async () => {
    try {
      await postClientAction('/mandate/cancel');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not cancel NuPay mandate');
    }
  };

  const resendNupayMandate = async () => {
    try {
      await postClientAction('/mandate/resend', { reason: 'Cancelled or details changed' });
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not resend NuPay mandate');
    }
  };

  const updatePdaField = <K extends keyof PdaInfo>(field: K, value: PdaInfo[K]) => {
    setClient((current) => ({ ...current, pdaInfo: { ...defaultPda(), ...(current.pdaInfo || {}), [field]: value } }));
  };

  const savePdaInfo = async () => {
    try {
      await postClientAction('/pda', { ...(client.pdaInfo || defaultPda()) }, 'PUT');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not save PDA info');
    }
  };

  const submitToAdmin = async () => {
    try {
      await postClientAction('/admin-submit', { notes: handoverNotes });
      setActiveView('admin');
      loadAdminClients();
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not submit to admin');
    }
  };

  const loadAdminClients = async () => {
    if (!isAdminRole) {
      setAdminClients([]);
      return;
    }
    try {
      const response = await apiRequest(`${apiBase}/api/admin/clients`, { headers: { 'X-Tenant-ID': tenantId } });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not load admin queue');
      setAdminClients((data.clients || []).map((item: Client) => withWorkflowDefaults(item)));
    } catch (error) {
      console.warn(error);
      setAdminClients([]);
    }
  };

  const saveApiBase = () => {
    localStorage.setItem('fintastic_sales_api', apiBase);
    loadTenants();
    loadUsers();
    loadClients();
  };

  const documents = useMemo(() => {
    const common = ['POPIA consent', 'ID copy', 'Proof of address', 'Latest payslip', '3 months bank statements', 'Credit report'];
    if (coach.service === 'Debt Review Removal') return [...common, 'DR removal mandate', 'NCT/court order if available', 'Paid-up letters where applicable', 'Clearance or termination evidence'];
    if (coach.service === 'Debt Review Sales Coach') return [...common, 'Form 16', '17.1 notice', 'COB request letters', 'Debit order mandate', 'Budget and affordability sheet'];
    if (coach.service === 'Debt Mediation') return [...common, 'Mediation mandate', 'Creditor proposal sheet', 'Debit order mandate', 'Settlement/arrangement letters'];
    return common;
  }, [coach.service]);

  const handoverText = useMemo(() => {
    return [
      `Tenant: ${currentTenant?.name || tenantId}`,
      `Consultant/User: ${currentUser?.name || userId}`,
      `Client: ${client.fullName || 'Not captured'} (${client.applicationType})`,
      `Service Route: ${coach.service} / ${coach.urgency} priority`,
      `Status: ${client.status}`,
      `DR Flag: ${coach.flags.debtReviewListed ? 'Yes' : 'No'}`,
      `Outstanding: ${currency(coach.totals.outstanding)}`,
      `Original Instalments: ${currency(coach.totals.originalInstalment)}`,
      `Reduced Proposal: ${currency(coach.totals.reducedInstalment)}`,
      `DRR Fee: ${coach.service === 'Debt Review Removal' ? `${currency(drrFee)} over ${drrMonths} month(s) = ${currency(drrFee / drrMonths)} p/m` : 'Not applicable'}`,
      `Signature: ${client.signature?.status || 'Not Sent'}`,
      `NuPay Mandate: ${client.nupayMandate?.status || 'Not Sent'} ${client.nupayMandate?.mandateId ? `(${client.nupayMandate.mandateId})` : ''}`,
      `PDA: ${client.pdaInfo?.status || 'Not Submitted'} ${client.pdaInfo?.pdaReference ? `- ${client.pdaInfo.pdaReference}` : ''}`,
      `Uploaded Docs: ${(client.documents?.items || []).filter((item) => item.status === 'Uploaded').length}/${(client.documents?.items || []).length}`,
      '',
      'Coach reasons:',
      ...coach.reasons.map((reason) => `- ${reason}`),
      '',
      'Next steps:',
      ...coach.nextSteps.map((step) => `- ${step}`)
    ].join('\n');
  }, [client, coach, drrMonths, currentTenant, currentUser, tenantId, userId]);

  useEffect(() => {
    if (activeView === 'admin') loadAdminClients();
  }, [activeView, tenantId]);

  const allNavItems: { key: ViewKey; label: string; helper: string }[] = [
    { key: 'dashboard', label: 'Dashboard', helper: 'Tenant overview' },
    { key: 'clients', label: 'Clients', helper: 'List and search' },
    { key: 'upload', label: 'Upload Report', helper: 'Parse and route sale' },
    { key: 'profile', label: 'Client Profile', helper: 'Single or joint application' },
    { key: 'coach', label: 'Sales Coach', helper: 'Best next sale' },
    { key: 'accounts', label: 'Accounts', helper: 'Reduced amount table' },
    { key: 'mandate', label: 'Banking / NuPay', helper: 'Debit order ready' },
    { key: 'documents', label: 'Documents', helper: 'Links and uploaded docs' },
    { key: 'workflow', label: 'Submit Workflow', helper: 'Admin and PDA handover' },
    { key: 'admin', label: 'Admin Queue', helper: 'Docs, fees, PDA' },
    { key: 'settings', label: 'Settings', helper: 'API and session' }
  ];
  const navItems = allNavItems.filter((item) => isAdminRole || item.key !== 'admin');

  const login = async (event?: FormEvent) => {
    event?.preventDefault();
    setLoginError('');
    try {
      const response = await apiRequest(`${apiBase}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: loginEmail.trim().toLowerCase(), password: loginPassword })
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Sign-in failed');
      setSessionUser(data.user);
      setUserId(data.user.id);
      setTenantId(data.tenant.id);
      setLoggedIn(true);
      setLoginPassword('');
      setClient(newLocalClient(data.tenant.id, data.user.id));
      await Promise.all([loadTenants(), loadUsers(data.tenant.id), loadClients('', data.tenant.id)]);
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'Sign-in failed');
    }
  };

  const logout = async () => {
    try {
      await apiRequest(`${apiBase}/api/auth/logout`, { method: 'POST' });
    } finally {
      localStorage.removeItem('fintastic_logged_in');
      localStorage.removeItem('fintastic_user_id');
      setLoggedIn(false);
      setSessionUser(null);
      setUsers([]);
      setClients([]);
      setLoginPassword('');
    }
  };

  if (sessionChecking) {
    return <div className="login-shell"><div className="login-card"><h1>Fin-Tastic</h1><p>Checking secure session…</p></div></div>;
  }

  if (!loggedIn) {
    return (
      <div className="login-shell">
        <form className="login-card" onSubmit={login}>
          <div className="brand-block login-brand"><div className="brand-mark">FT</div><div><strong>Fin-Tastic</strong><span>Sales Coach</span></div></div>
          <h1>Secure sign in</h1>
          <p>Use the email address and password created for you by the Fin-Tastic platform owner.</p>
          <Field label="Email Address"><input required autoComplete="username" type="email" value={loginEmail} onChange={(event) => setLoginEmail(event.target.value)} /></Field>
          <Field label="Password"><input required autoComplete="current-password" type="password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} /></Field>
          <details><summary>Connection settings</summary><Field label="Backend API Base"><input value={apiBase} onChange={(event) => setApiBase(event.target.value)} /></Field></details>
          {loginError && <div className="notice error">{loginError}</div>}
          <div className="button-row"><button className="primary" type="submit">Sign In</button><button className="secondary" type="button" onClick={saveApiBase}>Save API Address</button></div>
          <div className="panel-card tenant-rules"><strong>Tenant security:</strong><p>Your login determines your tenant. Tenant headers cannot be used to enter another company’s workspace.</p></div>
        </form>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand-block">
          <div className="brand-mark">FT</div>
          <div>
            <strong>Fin-Tastic</strong>
            <span>Sales Coach</span>
          </div>
        </div>
        <div className="tenant-card dark">
          <small>Active tenant</small>
          <strong>{currentTenant?.name || tenantId}</strong>
          <span>{clients.length} visible client(s)</span>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <button key={item.key} className={activeView === item.key ? 'active' : ''} onClick={() => { setActiveView(item.key); setSidebarOpen(false); }}>
              <span>{item.label}</span>
              <small>{item.helper}</small>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <Badge tone={coach.urgency === 'High' ? 'danger' : coach.urgency === 'Medium' ? 'warn' : 'good'}>{coach.urgency} Priority</Badge>
          <p>{coach.service}</p>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <button className="menu-button" onClick={() => setSidebarOpen((open) => !open)}>☰</button>
          <div>
            <h1>{navItems.find((item) => item.key === activeView)?.label}</h1>
            <p>Every user sees only the clients inside their own tenant database.</p>
          </div>
          <div className="topbar-actions session-chip">
            <span><strong>{currentTenant?.name || tenantId}</strong></span>
            <span>{currentUser ? `${currentUser.name} · ${currentUser.role}` : userId}</span>
            <button className="secondary" onClick={logout}>Sign Out</button>
          </div>
        </header>

        <div className="case-tab-strip" aria-label="Client workflow tabs">
          <div className="case-tab-client">
            <span>Selected client</span>
            <strong>{client.fullName || 'No client selected'}</strong>
            <small>{client.id.startsWith('local-') ? 'Unsaved' : client.status}</small>
          </div>
          <div className="case-tabs">
            {quickTabs.map((tab, index) => (
              <button key={tab.key} className={activeView === tab.key ? 'active' : ''} onClick={() => setActiveView(tab.key)}>
                <b>{String.fromCharCode(65 + index)}</b>
                <span>{tab.label}</span>
                <small>{tab.helper}</small>
              </button>
            ))}
          </div>
          <div className="save-status">
            <button className="primary" onClick={saveClient} disabled={saving}>{saving ? 'Saving...' : 'Save Client'}</button>
            <small>{saveMessage}</small>
          </div>
        </div>

        {activeView === 'dashboard' && (
          <section className="view-stack">
            <div className="hero-card">
              <div>
                <Badge tone="blue">Tenant Isolated</Badge>
                <h2>{coach.headline}</h2>
                <p>{currentTenant?.name || tenantId} users share this tenant’s clients, but no other tenant can see this list or database records.</p>
                <div className="button-row">
                  <button className="primary" onClick={() => setActiveView('clients')}>Open Client List</button>
                  <button className="secondary" onClick={() => setActiveView('upload')}>Upload Credit Report</button>
                </div>
              </div>
              <div className="hero-summary">
                <span>Selected client</span>
                <strong>{client.fullName || 'No client selected'}</strong>
                <small>{coach.service}</small>
              </div>
            </div>

            <div className="stats-grid">
              <StatCard label="Tenant Clients" value={String(clients.length)} sub="Scoped by X-Tenant-ID" />
              <StatCard label="Outstanding Debt" value={currency(coach.totals.outstanding)} sub="Selected client" />
              <StatCard label="Reduced Proposal" value={currency(coach.totals.reducedInstalment)} sub="Included accounts" />
              <StatCard label="Estimated Relief" value={currency(coach.totals.estimatedRelief)} sub="Before final checks" />
            </div>

            <div className="two-column">
              <div className="panel-card">
                <h3>Tenant security rule</h3>
                <p>Frontend sends <code>X-Tenant-ID</code> and backend stores clients under that tenant only. Switching tenants changes the entire client list.</p>
                <div className="flag-grid">
                  <Badge tone="good">Tenant DB</Badge>
                  <Badge tone="good">Shared users</Badge>
                  <Badge tone="danger">No cross-tenant clients</Badge>
                </div>
              </div>
              <div className="panel-card">
                <h3>Selected client flags</h3>
                <div className="flag-grid">
                  <Badge tone={coach.flags.debtReviewListed ? 'danger' : 'good'}>{coach.flags.debtReviewListed ? 'Debt Review Listed' : 'No DR Listing'}</Badge>
                  <Badge tone={coach.flags.hasAsset ? 'warn' : 'neutral'}>{coach.flags.hasAsset ? 'Asset Detected' : 'No Asset Detected'}</Badge>
                  <Badge tone={coach.flags.hasFurniture ? 'blue' : 'neutral'}>{coach.flags.hasFurniture ? 'Furniture Tagged' : 'No Furniture Tag'}</Badge>
                </div>
              </div>
            </div>
          </section>
        )}

        {activeView === 'clients' && (
          <section className="view-stack">
            <div className="panel-card">
              <div className="section-heading">
                <div>
                  <h2>Client list and search</h2>
                  <p>This list is loaded only from <strong>{currentTenant?.name || tenantId}</strong>. Users in this tenant see the same records.</p>
                </div>
                <div className="button-row">
                  <button className="secondary" onClick={() => loadClients()}>Refresh</button>
                  <button className="primary" onClick={startNewClient}>New Client</button>
                </div>
              </div>
              <div className="search-panel">
                <Field label="Search name, ID, phone, email or route">
                  <input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder="Search this tenant’s clients..." />
                </Field>
                <Field label="Service filter">
                  <select value={serviceFilter} onChange={(event) => setServiceFilter(event.target.value)}>
                    <option value="">All services</option>
                    <option>Debt Review Sales Coach</option>
                    <option>Debt Review Removal</option>
                    <option>Debt Mediation</option>
                    <option>Needs Manual Review</option>
                  </select>
                </Field>
                <Field label="Status filter">
                  <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                    <option value="">All statuses</option>
                    <option>Lead Received</option>
                    <option>Credit Report Uploaded</option>
                    <option>Docs Requested</option>
                    <option>Docs Received</option>
                    <option>Handover Ready</option>
                  </select>
                </Field>
              </div>
            </div>

            <div className="client-grid">
              {clients.length ? clients.map((item) => (
                <button key={item.id} className={`client-card ${client.id === item.id ? 'selected' : ''}`} onClick={() => { setClient(withWorkflowDefaults(item)); setActiveView('profile'); }}>
                  <div className="client-card-top">
                    <strong>{item.fullName || 'Unnamed Client'}</strong>
                    <Badge tone={item.serviceType === 'Debt Review Removal' ? 'danger' : item.serviceType === 'Debt Review Sales Coach' ? 'warn' : item.serviceType === 'Debt Mediation' ? 'blue' : 'neutral'}>{item.serviceType || 'Manual'}</Badge>
                  </div>
                  <span>ID: {item.idNumber || 'Not captured'}</span>
                  <span>Phone: {item.phone || item.whatsapp || 'Not captured'}</span>
                  <span>Status: {item.status || 'Lead Received'}</span>
                  <small>Updated: {item.updatedAt ? new Date(item.updatedAt).toLocaleString() : 'Not saved yet'}</small>
                </button>
              )) : <div className="empty-state">No clients found for this tenant. Create a new client or upload a report.</div>}
            </div>
          </section>
        )}

        {activeView === 'upload' && (
          <section className="view-stack">
            <div className="panel-card">
              <div className="section-heading">
                <div>
                  <h2>Upload credit report</h2>
                  <p>Uploads are saved under the active tenant only. Selected client: <strong>{client.fullName}</strong>.</p>
                </div>
                <Badge tone="blue">PDF</Badge>
              </div>
              <div className="upload-mode-panel">
                <label className="checkline"><input type="radio" checked={uploadMode === 'new'} onChange={() => setUploadMode('new')} /> Upload as NEW client</label>
                <label className="checkline"><input type="radio" checked={uploadMode === 'existing'} onChange={() => setUploadMode('existing')} /> Replace credit report for selected saved client</label>
                <small>{uploadMode === 'new' ? 'Safe default: a new client record will be created. Previous selected client will not be overwritten.' : `This will update ${client.fullName || 'the selected client'} only.`}</small>
              </div>
              <form className="upload-box" onSubmit={handleUpload}>
                <input type="file" accept="application/pdf,.pdf" onChange={handleFileChange} />
                <button className="primary" disabled={uploading}>{uploading ? 'Parsing...' : uploadMode === 'new' ? 'Upload as New Client' : 'Replace Selected Report'}</button>
              </form>
              {selectedFile ? <p className="muted">Selected: {selectedFile.name}</p> : null}
              {uploadError ? <div className="alert danger">{uploadError}</div> : null}
              {parseResult ? (
                <div className="parse-summary">
                  <Badge tone="good">Parsed</Badge>
                  <span>Bureau: {parseResult.bureau || 'Unknown'}</span>
                  <span>Confidence: {parseResult.confidence || 0}%</span>
                  <span>Tenant: {parseResult.tenantId}</span>
                  <span>Accounts: {parseResult.accounts?.length || parseResult.parserDebug?.accountCount || 0}</span>
                  <span>OCR: {parseResult.parserDebug?.ocrUsed ? 'Used' : parseResult.parserDebug?.ocrAvailable ? 'Available' : 'Not available'}</span>
                  {parseResult.bureau === 'Datanamix' ? <span>Datanamix blocks: {parseResult.parserDebug?.datanamixSubscriberBlocks || 0}</span> : null}
                  {parseResult.warnings?.length ? <small>{parseResult.warnings.join(' ')}</small> : null}
                </div>
              ) : null}
            </div>
          </section>
        )}

        {activeView === 'profile' && (
          <section className="view-stack">
            <div className="panel-card">
              <div className="section-heading">
                <div>
                  <h2>Client profile</h2>
                  <p>Saved to <strong>{currentTenant?.name || tenantId}</strong> only.</p>
                </div>
                <div className="button-row">
                  <select value={client.applicationType} onChange={(event) => updateClient('applicationType', event.target.value as Client['applicationType'])}>
                    <option>Single</option>
                    <option>Joint</option>
                  </select>
                  <button className="primary" onClick={saveClient} disabled={saving}>{saving ? 'Saving...' : 'Save Client'}</button>
                </div>
              </div>
              <div className="form-grid">
                <Field label="First Name"><input value={client.firstName || ''} onChange={(event) => updateClientNamePart('firstName', event.target.value)} /></Field>
                <Field label="Second Name"><input value={client.secondName || ''} onChange={(event) => updateClientNamePart('secondName', event.target.value)} /></Field>
                <Field label="Surname"><input value={client.surname || ''} onChange={(event) => updateClientNamePart('surname', event.target.value)} /></Field>
                <Field label="Full Name"><input value={client.fullName} onChange={(event) => updateClient('fullName', event.target.value)} /></Field>
                <Field label="ID Number"><input value={client.idNumber} onChange={(event) => updateClient('idNumber', event.target.value)} /></Field>
                <Field label="Date of Birth"><input value={client.dateOfBirth || ''} onChange={(event) => updateClient('dateOfBirth', event.target.value)} /></Field>
                <Field label="Gender"><input value={client.gender || ''} onChange={(event) => updateClient('gender', event.target.value)} /></Field>
                <Field label="Marital Status"><input value={client.maritalStatus || ''} onChange={(event) => updateClient('maritalStatus', event.target.value)} /></Field>
                <Field label="Email"><input value={client.email} onChange={(event) => updateClient('email', event.target.value)} /></Field>
                <Field label="Phone"><input value={client.phone} onChange={(event) => updateClient('phone', event.target.value)} /></Field>
                <Field label="WhatsApp"><input value={client.whatsapp} onChange={(event) => updateClient('whatsapp', event.target.value)} /></Field>
                <Field label="Physical Address"><input value={client.physicalAddress} onChange={(event) => updateClient('physicalAddress', event.target.value)} /></Field>
                <Field label="Employer"><input value={client.employer} onChange={(event) => updateClient('employer', event.target.value)} /></Field>
                <Field label="Occupation"><input value={client.occupation} onChange={(event) => updateClient('occupation', event.target.value)} /></Field>
                <Field label="Date Employed"><input type="date" value={client.dateEmployed} onChange={(event) => updateClient('dateEmployed', event.target.value)} /></Field>
                <Field label="Salary Frequency"><select value={client.salaryFrequency} onChange={(event) => updateClient('salaryFrequency', event.target.value as Applicant['salaryFrequency'])}><option>Weekly</option><option>Fortnightly</option><option>Monthly</option></select></Field>
                <Field label="Gross Salary"><input value={client.grossSalary} onChange={(event) => updateClient('grossSalary', toNumber(event.target.value))} /></Field>
                <Field label="Nett Salary"><input value={client.nettSalary} onChange={(event) => updateClient('nettSalary', toNumber(event.target.value))} /></Field>
                <Field label="Credit Score"><input value={client.scoreFound ? String(client.creditScore ?? '') : ''} placeholder="Unknown if blank" onChange={(event) => { const value = event.target.value.trim(); updateClient('creditScore', value === '' ? null : toNumber(value)); updateClient('scoreFound', value !== ''); }} /></Field>
                <Field label="Status"><select value={client.status} onChange={(event) => updateClient('status', event.target.value)}><option>Lead Received</option><option>Credit Report Uploaded</option><option>Docs Requested</option><option>Docs Received</option><option>Handover Ready</option></select></Field>
                <label className="checkline"><input type="checkbox" checked={client.debtReviewListed} onChange={(event) => updateClient('debtReviewListed', event.target.checked)} /> Debt Review listed/flagged</label>
              </div>
            </div>

            {client.applicationType === 'Joint' && (
              <div className="panel-card spouse-card">
                <h3>Spouse / Co-applicant</h3>
                <div className="form-grid">
                  <Field label="Full Name"><input value={client.spouse.fullName} onChange={(event) => updateSpouse('fullName', event.target.value)} /></Field>
                  <Field label="ID Number"><input value={client.spouse.idNumber} onChange={(event) => updateSpouse('idNumber', event.target.value)} /></Field>
                  <Field label="Email"><input value={client.spouse.email} onChange={(event) => updateSpouse('email', event.target.value)} /></Field>
                  <Field label="Phone"><input value={client.spouse.phone} onChange={(event) => updateSpouse('phone', event.target.value)} /></Field>
                  <Field label="Employer"><input value={client.spouse.employer} onChange={(event) => updateSpouse('employer', event.target.value)} /></Field>
                  <Field label="Nett Salary"><input value={client.spouse.nettSalary} onChange={(event) => updateSpouse('nettSalary', toNumber(event.target.value))} /></Field>
                </div>
              </div>
            )}
          </section>
        )}

        {activeView === 'coach' && (
          <section className="view-stack">
            <div className="coach-card">
              <div className="coach-topline">
                <Badge tone={coach.urgency === 'High' ? 'danger' : coach.urgency === 'Medium' ? 'warn' : 'good'}>{coach.urgency} Priority</Badge>
                <Badge tone={coach.flags.doubleSaleCandidate ? 'blue' : 'neutral'}>{coach.flags.doubleSaleCandidate ? 'Double Sale Candidate' : 'Single Route'}</Badge>
                <Badge tone={coach.flags.debtReviewListed ? 'danger' : 'good'}>{coach.flags.debtReviewListed ? 'DR Flag' : 'No DR Flag'}</Badge>
              </div>
              <h2>{coach.service}</h2>
              <p>{coach.headline}</p>
              {coach.service === 'Debt Review Removal' && (
                <div className="panel-card fee-card">
                  <div><h3>DRR service fee</h3><p>R7,000 can be split over 1 to 3 months.</p></div>
                  <div className="fee-controls"><select value={drrMonths} onChange={(event) => setDrrMonths(Number(event.target.value))}><option value={1}>1 month</option><option value={2}>2 months</option><option value={3}>3 months</option></select><strong>{currency(drrFee / drrMonths)} p/m</strong></div>
                </div>
              )}
            </div>
            <div className="stats-grid compact">
              <StatCard label="Outstanding Debt" value={currency(coach.totals.outstanding)} sub="Included accounts only" />
              <StatCard label="Current Instalments" value={currency(coach.totals.originalInstalment)} sub="Before proposal" />
              <StatCard label="Reduced Proposal" value={currency(coach.totals.reducedInstalment)} sub="Editable per account" />
              <StatCard label="Estimated Relief" value={currency(coach.totals.estimatedRelief)} sub="Before final checks" />
            </div>
            <div className="two-column">
              <div className="panel-card script-card">
                <div className="section-heading"><div><h3>Call opening</h3><p>Read naturally; do not sound scripted.</p></div><button className="secondary" type="button" onClick={() => navigator.clipboard?.writeText(coach.callOpening)}>Copy Opening</button></div>
                <blockquote>{coach.callOpening}</blockquote>
                <h4>Permission / transition question</h4>
                <p className="script-line">{coach.permissionQuestion}</p>
              </div>
              <div className="panel-card">
                <h3>Discovery questions</h3>
                <ol className="clean-list numbered">{coach.discoveryQuestions.map((question) => <li key={question}>{question}</li>)}</ol>
              </div>
            </div>
            <div className="panel-card">
              <div className="section-heading"><div><h3>Conversation guide</h3><p>Move through the stages in order and listen before presenting the service.</p></div></div>
              <div className="conversation-grid">{coach.conversationGuide.map((step) => <article className="conversation-step" key={step.stage}><strong>{step.stage}</strong><span>{step.objective}</span><p>“{step.script}”</p></article>)}</div>
            </div>
            <div className="two-column">
              <div className="panel-card"><h3>Why this route</h3><ul className="clean-list">{coach.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul><h3>Value points</h3><ul className="clean-list">{coach.valuePoints.map((point) => <li key={point}>{point}</li>)}</ul></div>
              <div className="panel-card"><h3>Next steps</h3><ol className="clean-list numbered">{coach.nextSteps.map((step) => <li key={step}>{step}</li>)}</ol><h3>Closing script</h3><blockquote>{coach.closingScript}</blockquote></div>
            </div>
            <div className="panel-card">
              <div className="section-heading"><div><h3>Objections and responses</h3><p>Acknowledge, answer honestly, then use the follow-up question.</p></div></div>
              <div className="objection-grid">{coach.objections.length ? coach.objections.map((item) => <article className="objection-card" key={item.objection}><h4>“{item.objection}”</h4><p><strong>Response:</strong> {item.response}</p><p className="follow-up"><strong>Ask:</strong> {item.followUp}</p></article>) : <p>Capture more data to generate objection handling.</p>}</div>
            </div>
            <div className="panel-card compliance-card"><h3>Compliance reminders</h3><ul className="clean-list">{coach.complianceReminders.map((item) => <li key={item}>{item}</li>)}</ul></div>
          </section>
        )}

        {activeView === 'accounts' && (
          <section className="view-stack">
            <div className="panel-card">
              <div className="section-heading">
                <div><h2>Accounts and reduced amounts</h2><p>Include/exclude accounts, tag furniture/assets, and adjust reduced instalments.</p></div>
                <div className="button-row"><button className="secondary" onClick={cleanParsedAccounts}>Clean Bad Rows</button><button className="secondary" onClick={addAccount}>Add Account</button><button className="primary" onClick={saveClient}>Save Changes</button></div>
              </div>
              <div className="alert warn">Parser has been made stricter: it will reject weak rows instead of importing payment-profile fragments. Always compare the accounts against the PDF before admin/PDA handover.</div>
              <div className="table-wrap">
                <table className="accounts-table">
                  <thead><tr><th>In</th><th>Creditor</th><th>Acc No</th><th>Type</th><th>Opening</th><th>Current</th><th>Arrears</th><th>Monthly</th><th>Reduced</th><th>Last Paid</th><th>Months</th><th>Open Date</th><th>Status</th><th>Tags</th></tr></thead>
                  <tbody>
                    {accounts.map((account) => (
                      <tr key={account.id}>
                        <td><input type="checkbox" checked={account.included} onChange={(event) => updateAccount(account.id, 'included', event.target.checked)} /></td>
                        <td><input value={account.creditorName} onChange={(event) => updateAccount(account.id, 'creditorName', event.target.value)} /></td>
                        <td><input value={account.accountNumber} onChange={(event) => updateAccount(account.id, 'accountNumber', event.target.value)} /></td>
                        <td><input value={account.accountType} onChange={(event) => updateAccount(account.id, 'accountType', event.target.value)} /></td>
                        <td><input value={account.openingBalance} onChange={(event) => updateAccount(account.id, 'openingBalance', event.target.value)} /></td>
                        <td><input value={account.currentBalance} onChange={(event) => updateAccount(account.id, 'currentBalance', event.target.value)} /></td>
                        <td><input value={account.arrears} onChange={(event) => updateAccount(account.id, 'arrears', event.target.value)} /></td>
                        <td><input value={account.monthlyInstallment} onChange={(event) => updateAccount(account.id, 'monthlyInstallment', event.target.value)} /></td>
                        <td><input value={account.reducedAmount} onChange={(event) => updateAccount(account.id, 'reducedAmount', event.target.value)} /></td>
                        <td><input value={account.lastPaidDate} onChange={(event) => updateAccount(account.id, 'lastPaidDate', event.target.value)} /></td>
                        <td><input value={account.monthsInArrears} onChange={(event) => updateAccount(account.id, 'monthsInArrears', event.target.value)} /></td>
                        <td><input value={account.openDate} onChange={(event) => updateAccount(account.id, 'openDate', event.target.value)} /></td>
                        <td><input value={account.status} onChange={(event) => updateAccount(account.id, 'status', event.target.value)} /></td>
                        <td><div className="mini-tags"><label><input type="checkbox" checked={account.isFurniture} onChange={(event) => updateAccount(account.id, 'isFurniture', event.target.checked)} /> Furniture</label><label><input type="checkbox" checked={account.isAsset} onChange={(event) => updateAccount(account.id, 'isAsset', event.target.checked)} /> Asset</label></div></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}

        {activeView === 'mandate' && (
          <section className="view-stack">
            <div className="panel-card">
              <div className="section-heading"><div><h2>Banking / NuPay-ready mandate</h2><p>Capture details needed for mandate setup and later API integration.</p></div><button className="primary" onClick={saveClient}>Save Banking</button></div>
              <div className="form-grid">
                <Field label="Account Holder"><input value={client.bank.accountHolder} onChange={(event) => updateBank('accountHolder', event.target.value)} /></Field>
                <Field label="Bank Name"><input value={client.bank.bankName} onChange={(event) => updateBank('bankName', event.target.value)} /></Field>
                <Field label="Account Type"><select value={client.bank.accountType} onChange={(event) => updateBank('accountType', event.target.value as BankDetails['accountType'])}><option value="">Select type</option><option>Cheque</option><option>Savings</option><option>Transmission</option><option>Current</option></select></Field>
                <Field label="Branch Code"><input value={client.bank.branchCode} onChange={(event) => updateBank('branchCode', event.target.value)} /></Field>
                <Field label="Account Number"><input value={client.bank.accountNumber} onChange={(event) => updateBank('accountNumber', event.target.value)} /></Field>
                <Field label="Debit Day"><input value={client.bank.debitDay} onChange={(event) => updateBank('debitDay', event.target.value)} /></Field>
                <label className="checkline"><input type="checkbox" checked={client.bank.mandateAccepted} onChange={(event) => updateBank('mandateAccepted', event.target.checked)} /> Mandate accepted by client</label>
              </div>
            </div>
            <div className="panel-card">
              <div className="section-heading"><div><h2>NuPay mandate control</h2><p>Send, view status, cancel and resend a mandate when bank details or amount changes.</p></div><Badge tone={client.nupayMandate?.status === 'Pending Acceptance' ? 'warn' : client.nupayMandate?.status === 'Cancelled' ? 'danger' : client.nupayMandate?.status === 'Not Sent' ? 'neutral' : 'good'}>{client.nupayMandate?.status || 'Not Sent'}</Badge></div>
              <div className="form-grid">
                <Field label="Mandate Amount"><input value={client.nupayMandate?.amount || coach.totals.reducedInstalment || (coach.service === 'Debt Review Removal' ? drrFee / drrMonths : 0)} onChange={(event) => setClient((current) => ({ ...current, nupayMandate: { ...defaultNuPay(), ...(current.nupayMandate || {}), amount: toNumber(event.target.value), history: current.nupayMandate?.history || [] } }))} /></Field>
                <Field label="Debit Day"><input value={client.bank.debitDay} onChange={(event) => updateBank('debitDay', event.target.value)} /></Field>
                <Field label="Mandate ID"><input value={client.nupayMandate?.mandateId || ''} readOnly /></Field>
                <Field label="Mandate Link"><input value={client.nupayMandate?.link || ''} readOnly /></Field>
              </div>
              <div className="button-row"><button className="primary" onClick={sendNupayMandate}>Send NuPay Mandate</button><button className="secondary" onClick={cancelNupayMandate}>Cancel Mandate</button><button className="secondary" onClick={resendNupayMandate}>Send New Mandate</button></div>
              {client.nupayMandate?.history?.length ? <ul className="clean-list mandate-history">{client.nupayMandate.history.slice(-4).map((event, index) => <li key={`${event.at}-${index}`}>{event.at ? new Date(event.at).toLocaleString() : ''} · {event.action}{event.amount ? ` · ${currency(event.amount)}` : ''}</li>)}</ul> : <p className="muted">No mandate history yet.</p>}
            </div>
            <div className="panel-card">
              <div className="section-heading"><div><h2>Client portal links</h2><p>Links include tenant and client ID so documents/signatures stay isolated.</p></div><button className="secondary" onClick={createPortalLinks}>Create Legacy Links</button></div>
              <div className="link-grid">
                <div><span>Signature Link</span>{client.signature?.link || client.portalLinks?.signatureLink ? <a href={client.signature?.link || client.portalLinks?.signatureLink}>{client.signature?.link || client.portalLinks?.signatureLink}</a> : <small>Not created yet</small>}</div>
                <div><span>Upload Documents Link</span>{client.documents?.uploadLink || client.portalLinks?.uploadLink ? <a href={client.documents?.uploadLink || client.portalLinks?.uploadLink}>{client.documents?.uploadLink || client.portalLinks?.uploadLink}</a> : <small>Not created yet</small>}</div>
              </div>
            </div>
          </section>
        )}

        {activeView === 'documents' && (
          <section className="view-stack">
            <div className="panel-card">
              <div className="section-heading">
                <div><h2>Client document request and upload status</h2><p>Filtered by selected service route: {coach.service}. Send the upload link before submitting to admin.</p></div>
                <div className="button-row"><button className="secondary" onClick={requestDocuments}>Send Upload Link</button><button className="primary" onClick={sendSignatureLink}>Send Signature Link</button></div>
              </div>
              <div className="link-grid">
                <div><span>Upload link status</span><strong>{client.documents?.requestStatus || 'Not Sent'}</strong>{client.documents?.uploadLink ? <a href={client.documents.uploadLink}>{client.documents.uploadLink}</a> : <small>No upload link created yet</small>}</div>
                <div><span>Signature status</span><strong>{client.signature?.status || 'Not Sent'}</strong>{client.signature?.link ? <a href={client.signature.link}>{client.signature.link}</a> : <small>No signature link created yet</small>}</div>
              </div>
              <div className="document-grid">
                {(client.documents?.items || documents.map((name) => ({ name, status: 'Missing' } as DocumentItem))).map((doc) => (
                  <div className={`document-item status-${doc.status.toLowerCase().replace(/\s+/g, '-')}`} key={doc.name}>
                    <strong>{doc.name}</strong>
                    <Badge tone={doc.status === 'Uploaded' ? 'good' : doc.status === 'Requested' ? 'warn' : 'neutral'}>{doc.status}</Badge>
                    {doc.filename ? <small>{doc.filename}</small> : <small>Awaiting client upload</small>}
                  </div>
                ))}
              </div>
              <div className="button-row document-actions">
                <select value={docUploadName} onChange={(event) => setDocUploadName(event.target.value)}>
                  {(client.documents?.items || documents.map((name) => ({ name, status: 'Missing' } as DocumentItem))).map((doc) => <option key={doc.name} value={doc.name}>{doc.name}</option>)}
                </select>
                <button className="secondary" onClick={simulateDocumentUpload}>Mark Selected Doc Uploaded</button>
                <button className="secondary" onClick={markSignatureSigned}>Mark Signature Signed</button>
              </div>
            </div>
            <div className="panel-card handover-card"><h3>Admin handover summary</h3><textarea value={handoverText} readOnly /></div>
          </section>
        )}

        {activeView === 'workflow' && (
          <section className="view-stack">
            <div className="panel-card">
              <div className="section-heading">
                <div><h2>Submit client to admin workflow</h2><p>Admin receives the documents, signature, fees, reduced amount, included creditors, mandate and PDA info.</p></div>
                <Badge tone={client.adminHandover?.status === 'Submitted' ? 'good' : 'warn'}>{client.adminHandover?.status || 'Not Submitted'}</Badge>
              </div>
              <div className="stats-grid compact">
                <StatCard label="Original Instalments" value={currency(coach.totals.originalInstalment)} sub="Before proposal" />
                <StatCard label="Reduced Amount" value={currency(coach.totals.reducedInstalment)} sub="Admin/PDA proposal" />
                <StatCard label="Included Creditors" value={String(accounts.filter((account) => account.included).length)} sub="To hand over" />
                <StatCard label="NuPay Status" value={client.nupayMandate?.status || 'Not Sent'} sub={client.nupayMandate?.mandateId || 'No mandate ID'} />
              </div>
              <div className="form-grid">
                <Field label="PDA Name"><input value={client.pdaInfo?.pdaName || ''} onChange={(event) => updatePdaField('pdaName', event.target.value)} placeholder="e.g. Hyphen PDA / CollectNet / NPDA" /></Field>
                <Field label="PDA Reference"><input value={client.pdaInfo?.pdaReference || ''} onChange={(event) => updatePdaField('pdaReference', event.target.value)} /></Field>
                <Field label="PDA Proposal Amount"><input value={client.pdaInfo?.proposalAmount || coach.totals.reducedInstalment} onChange={(event) => updatePdaField('proposalAmount', toNumber(event.target.value))} /></Field>
                <Field label="Payment Start Date"><input type="date" value={client.pdaInfo?.paymentStartDate || ''} onChange={(event) => updatePdaField('paymentStartDate', event.target.value)} /></Field>
                <Field label="PDA Status"><select value={client.pdaInfo?.status || 'Not Submitted'} onChange={(event) => updatePdaField('status', event.target.value)}><option>Not Submitted</option><option>Ready for PDA</option><option>Submitted to PDA</option><option>PDA Active</option><option>PDA Query</option></select></Field>
                <Field label="PDA Notes"><input value={client.pdaInfo?.notes || ''} onChange={(event) => updatePdaField('notes', event.target.value)} /></Field>
              </div>
              <div className="button-row"><button className="secondary" onClick={savePdaInfo}>Save PDA Info</button></div>
              <Field label="Admin handover notes"><textarea value={handoverNotes} onChange={(event) => setHandoverNotes(event.target.value)} placeholder="Add anything admin must know before statutory workflow starts..." /></Field>
              <div className="button-row"><button className="primary" onClick={submitToAdmin}>Submit to Admin Department</button><button className="secondary" onClick={() => setActiveView('admin')}>Open Admin Queue</button></div>
            </div>
            <div className="panel-card handover-card"><h3>What admin will see</h3><textarea value={handoverText} readOnly /></div>
          </section>
        )}

        {activeView === 'admin' && (
          !isAdminRole ? (
            <section className="view-stack"><div className="panel-card"><h2>Admin access only</h2><p>Your current role is {currentUser?.role || 'Unknown'}. Please switch to an Admin or Manager login to view the admin queue.</p></div></section>
          ) : (
          <section className="view-stack">
            <div className="panel-card">
              <div className="section-heading"><div><h2>Admin queue</h2><p>Tenant-isolated admin view showing submitted clients, documents, fees, reduced amounts, included creditors, signature, NuPay and PDA info.</p></div><button className="secondary" onClick={loadAdminClients}>Refresh Admin Queue</button></div>
              <div className="client-grid admin-grid">
                {(adminClients.length ? adminClients : clients).map((item) => (
                  <button key={item.id} className={`client-card ${client.id === item.id ? 'selected' : ''}`} onClick={() => setClient(withWorkflowDefaults(item))}>
                    <div className="client-card-top"><strong>{item.fullName || 'Unnamed Client'}</strong><Badge tone={item.adminHandover?.status === 'Submitted' ? 'good' : 'neutral'}>{item.adminHandover?.status || 'Not Submitted'}</Badge></div>
                    <span>{item.serviceType}</span>
                    <span>Reduced: {currency(item.coach?.totals.reducedInstalment || 0)}</span>
                    <span>NuPay: {item.nupayMandate?.status || 'Not Sent'}</span>
                    <span>PDA: {item.pdaInfo?.status || 'Not Submitted'}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="two-column">
              <div className="panel-card">
                <h3>Admin package for {client.fullName}</h3>
                <div className="info-list">
                  <div><span>Service</span><strong>{coach.service}</strong></div>
                  <div><span>DRR Fee</span><strong>{coach.service === 'Debt Review Removal' ? currency(drrFee) : 'N/A'}</strong></div>
                  <div><span>Original instalments</span><strong>{currency(coach.totals.originalInstalment)}</strong></div>
                  <div><span>Reduced amount</span><strong>{currency(coach.totals.reducedInstalment)}</strong></div>
                  <div><span>Signature</span><strong>{client.signature?.status || 'Not Sent'}</strong></div>
                  <div><span>NuPay</span><strong>{client.nupayMandate?.status || 'Not Sent'}</strong></div>
                  <div><span>PDA</span><strong>{client.pdaInfo?.status || 'Not Submitted'} {client.pdaInfo?.pdaReference ? `· ${client.pdaInfo.pdaReference}` : ''}</strong></div>
                </div>
                <div className="button-row"><button className="secondary" onClick={cancelNupayMandate}>Cancel Mandate</button><button className="primary" onClick={resendNupayMandate}>Send New Mandate</button></div>
              </div>
              <div className="panel-card">
                <h3>Uploaded docs and included creditors</h3>
                <ul className="clean-list">
                  {(client.documents?.items || []).map((doc) => <li key={doc.name}>{doc.name}: <strong>{doc.status}</strong>{doc.filename ? ` · ${doc.filename}` : ''}</li>)}
                </ul>
                <div className="table-wrap slim"><table className="accounts-table"><thead><tr><th>Creditor</th><th>Current</th><th>Original</th><th>Reduced</th></tr></thead><tbody>{accounts.filter((account) => account.included).map((account) => <tr key={account.id}><td>{account.creditorName}</td><td>{currency(account.currentBalance)}</td><td>{currency(account.monthlyInstallment)}</td><td>{currency(account.reducedAmount)}</td></tr>)}</tbody></table></div>
              </div>
            </div>
          </section>
        ))}

        {activeView === 'settings' && (
          <section className="view-stack">
            <div className="panel-card">
              <h2>Tenant and API settings</h2>
              <div className="form-grid">
                <Field label="Backend API Base"><input value={apiBase} onChange={(event) => setApiBase(event.target.value)} /></Field>
                <Field label="Current Tenant"><input value={currentTenant?.name || tenantId} readOnly /></Field>
                <Field label="Current User / Role"><input value={currentUser ? `${currentUser.name} · ${currentUser.role}` : userId} readOnly /></Field>
              </div>
              <div className="button-row settings-buttons"><button className="primary" onClick={saveApiBase}>Save API and Reload</button><button className="secondary" onClick={() => loadClients()}>Reload Client List</button><button className="secondary" onClick={logout}>Sign Out</button></div>
              {isPlatformOwner ? (
                <>
                  <div className="panel-card owner-card">
                    <h3>Platform owner access</h3>
                    <p>You are authenticated as Yunoos Daniels. Only this platform-owner session can create tenants and user logins.</p>
                  </div>
                  <div className="two-column">
                    <form className="panel-card" onSubmit={createTenant}>
                      <h3>Create a new tenant</h3>
                      <p>Create the company workspace and its first administrator.</p>
                      <div className="form-grid">
                        <Field label="Tenant / Company Name"><input required value={tenantForm.name} onChange={(event) => setTenantForm({ ...tenantForm, name: event.target.value })} /></Field>
                        <Field label="NCRDC Number"><input value={tenantForm.ncr} onChange={(event) => setTenantForm({ ...tenantForm, ncr: event.target.value })} /></Field>
                        <Field label="Administrator Name"><input required value={tenantForm.adminName} onChange={(event) => setTenantForm({ ...tenantForm, adminName: event.target.value })} /></Field>
                        <Field label="Administrator Email"><input required type="email" value={tenantForm.adminEmail} onChange={(event) => setTenantForm({ ...tenantForm, adminEmail: event.target.value })} /></Field>
                        <Field label="Administrator Password"><input required minLength={12} autoComplete="new-password" type="password" value={tenantForm.adminPassword} onChange={(event) => setTenantForm({ ...tenantForm, adminPassword: event.target.value })} /></Field>
                      </div>
                      <div className="button-row"><button className="primary" type="submit" disabled={creatingTenant}>{creatingTenant ? 'Creating Tenant…' : 'Create Tenant'}</button>{tenantCreateMessage && <span>{tenantCreateMessage}</span>}</div>
                    </form>
                    <form className="panel-card" onSubmit={createUser}>
                      <h3>Create a tenant user</h3>
                      <p>Create consultants, managers or tenant administrators. Only you can perform this action.</p>
                      <div className="form-grid">
                        <Field label="Tenant"><select value={userForm.tenantId} onChange={(event) => setUserForm({ ...userForm, tenantId: event.target.value })}>{tenants.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>)}</select></Field>
                        <Field label="Role"><select value={userForm.role} onChange={(event) => setUserForm({ ...userForm, role: event.target.value })}><option>Consultant</option><option>Manager</option><option>Admin</option></select></Field>
                        <Field label="Full Name"><input required value={userForm.name} onChange={(event) => setUserForm({ ...userForm, name: event.target.value })} /></Field>
                        <Field label="Email"><input required type="email" value={userForm.email} onChange={(event) => setUserForm({ ...userForm, email: event.target.value })} /></Field>
                        <Field label="Password"><input required minLength={12} autoComplete="new-password" type="password" value={userForm.password} onChange={(event) => setUserForm({ ...userForm, password: event.target.value })} /></Field>
                      </div>
                      <div className="button-row"><button className="primary" type="submit" disabled={creatingUser}>{creatingUser ? 'Creating User…' : 'Create User'}</button>{userCreateMessage && <span>{userCreateMessage}</span>}</div>
                    </form>
                  </div>
                </>
              ) : (
                <div className="panel-card"><h3>Owner-managed access</h3><p>Tenant and user creation is restricted to Yunoos Daniels, the Fin-Tastic platform owner. Tenant admins and managers cannot create tenants or users.</p></div>
              )}
              <div className="panel-card tenant-rules"><h3>Isolation rules built in</h3><ul className="clean-list"><li>Email and password authentication is required for every staff API request.</li><li>Normal users are locked to the tenant stored in their authenticated session.</li><li>Duplicate clients are blocked inside the same tenant using ID number and fallback identity details.</li><li>The same client may exist in another tenant because tenants remain isolated.</li></ul></div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
