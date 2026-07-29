import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useState } from 'react';
import khuselaLogo from './assets/khusela-logo.png';

type ViewKey = 'dashboard' | 'clients' | 'upload' | 'profile' | 'budget' | 'coach' | 'accounts' | 'mandate' | 'documents' | 'workflow' | 'admin' | 'knowledge' | 'settings';
type ServiceType = 'Debt Review Sales Coach' | 'Debt Review Removal' | 'Debt Mediation' | 'Needs Manual Review';
type Urgency = 'Low' | 'Medium' | 'High';

type Tenant = { id: string; name: string; tradingName?: string; fullName?: string; ncr: string; phone?: string; fax?: string; email?: string; finalRegistrationDate?: string; physicalAddress?: string; postalAddress?: string; town?: string; userCount: number; clientCount: number };
type TenantUser = { id: string; name: string; role: string; email: string; team?: string };

const tenantLogoSrc = (tenant?: Tenant | null): string | null => {
  if (!tenant) return null;
  return tenant.id === 'khusela-debt-management' ? khuselaLogo : null;
};
type ConsultantMetric = {
  rank: number;
  userId: string;
  name: string;
  role: string;
  team?: string;
  email: string;
  leadsGenerated: number;
  uploadedReports: number;
  activeClients: number;
  clientsSubmitted: number;
  reducedInstallments: number;
  removalFees: number;
  dcValue: number;
  documentsReceived: number;
  requiredDocuments: number;
  documentCompletionRate: number;
  performanceScore: number;
  heatBlocks?: number;
  heatLabel?: string;
  heatEmoji?: string;
  progressToNextHeat?: number;
  nextHeatGap?: number;
  lastActivityAt?: string;
};

type TeamMetric = {
  rank: number;
  team: string;
  consultants: number;
  leadsGenerated: number;
  uploadedReports: number;
  clientsSubmitted: number;
  reducedInstallments: number;
  removalFees: number;
  dcValue: number;
  documentsReceived: number;
  requiredDocuments: number;
  documentCompletionRate: number;
  performanceScore: number;
  heatBlocks?: number;
  heatLabel?: string;
  heatEmoji?: string;
  progressToNextHeat?: number;
  nextHeatGap?: number;
};

type ConsultantDashboardSummary = {
  tenantClients: number;
  uploadedReports: number;
  leadsGenerated: number;
  dcValue: number;
  reducedInstallments: number;
  removalFees: number;
  documentsReceived: number;
  clientsSubmitted: number;
  requiredDocuments?: number;
  consultants: number;
  teams?: number;
  heatBlocks?: number;
  heatLabel?: string;
  heatEmoji?: string;
  progressToNextHeat?: number;
  nextHeatGap?: number;
};

type CommissionSnapshot = {
  id: string;
  createdAt: string;
  createdBy: string;
  period: string;
  summary: ConsultantDashboardSummary;
  leaderboard: ConsultantMetric[];
  notes?: string;
};

type KnowledgeModule = { id: string; title: string; service: string; summary: string; keyPoints: string[]; salesAngles: string[] };
type KnowledgeQuestion = { id: string; moduleId: string; service: string; question: string; options: string[] };
type AssessmentReview = { id: string; moduleId: string; service: string; question: string; selectedIndex: number; correctIndex: number; correct: boolean };
type AssessmentResult = { id?: string; scorePercent: number; correct: number; total: number; level: string; passed: boolean; submittedAt?: string; review?: AssessmentReview[] };
type KnowledgeRank = { rank: number; userId: string; name: string; email: string; scorePercent: number; correct: number; total: number; level: string; passed: boolean; submittedAt?: string; attempts: number };

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

type LivingBudget = {
  rentOrBond: number;
  groceries: number;
  electricityWater: number;
  transport: number;
  schoolFees: number;
  insurance: number;
  medical: number;
  cellphoneInternet: number;
  clothing: number;
  maintenance: number;
  otherLivingExpenses: number;
  dependants: number;
  notes: string;
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

type CoachResult = {
  service: ServiceType;
  urgency: Urgency;
  headline: string;
  reasons: string[];
  nextSteps: string[];
  objectionHandlers: string[];
  painPoints: string[];
  budgetBenefits: string[];
  tonalityTips: string[];
  talkTrack: string[];
  totals: {
    outstanding: number;
    arrears: number;
    originalInstalment: number;
    reducedInstalment: number;
    estimatedRelief: number;
    householdIncome?: number;
    livingExpenses?: number;
    availableAfterLivingExpenses?: number;
    availableAfterReducedPayment?: number;
    savingsPercent?: number;
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
type NuPayMandateKind = 'removal' | 'mediation';
type NuPayComponents = { reducedPayment: number; drrServiceFeeTotal: number; drrServiceFeeMonthly: number; totalMonthlyCollection: number; ongoingMonthlyCollection?: number; drrFeeMonthsRemaining?: number; collectionMode?: string; product?: string; reducedPaymentLabel?: string; drrFeeLabel?: string; startDate?: string; mandateKind?: NuPayMandateKind };
type NuPayMandate = { status: string; mandateId?: string; link?: string; amount: number; debitDay: string; startDate?: string; mandateType?: NuPayMandateKind; drrMonths?: number; includesDrrFee?: boolean; components?: NuPayComponents; sentAt?: string; cancelledAt?: string; acceptedAt?: string; history: { at: string; action: string; amount?: number; debitDay?: string; startDate?: string; reason?: string; drrMonths?: number; includesDrrFee?: boolean; mandateType?: string }[] };
type NuPayMandates = { removal: NuPayMandate; mediation: NuPayMandate };
type AdminHandover = { status: string; submittedAt?: string; submittedBy?: string; notes?: string; snapshot?: Record<string, unknown> };
type PdaInfo = { pdaName: string; pdaReference: string; proposalAmount: number; paymentStartDate: string; status: string; notes: string };
type AdminTask = { id: string; service: ServiceType; sequence?: number; stepCode?: string; phase: string; label: string; status: string; notes?: string; completedAt?: string; updatedAt?: string; ownerRole?: string; dueBusinessDays?: number | null; dueFrom?: string; regulationRef?: string; evidenceRequired?: string; ncaMinimum?: boolean; gate?: string; outcome?: string };
type AdminCreditorAction = { id: string; service: ServiceType; creditorName: string; accountNumber: string; status: string; currentBalance: number; originalInstallment: number; proposedAmount: number; response?: string; notes?: string; updatedAt?: string };
type AdminFeeItem = { id: string; label: string; service: ServiceType; amount: number; status: string; dueDate?: string; paidAt?: string; notes?: string };
type AdminWorkflow = { services: ServiceType[]; activeService: ServiceType; overallStatus: string; tasks: AdminTask[]; creditorActions: AdminCreditorAction[]; feeItems: AdminFeeItem[]; lastUpdatedAt?: string };

type Client = Applicant & {
  id: string;
  tenantId: string;
  assignedUserId: string;
  applicationType: 'Single' | 'Joint';
  spouse: Applicant;
  bank: BankDetails;
  budget: LivingBudget;
  creditScore: number | null;
  scoreFound?: boolean;
  debtReviewListed: boolean;
  notes: string;
  status: string;
  serviceType: ServiceType;
  serviceTypes?: ServiceType[];
  accounts: DebtAccount[];
  coach?: CoachResult;
  portalLinks?: { clientPortalLink?: string; signatureLink?: string; uploadLink?: string; createdAt?: string };
  documents?: ClientDocuments;
  signature?: ClientSignature;
  nupayMandate?: NuPayMandate;
  nupayMandates?: NuPayMandates;
  adminHandover?: AdminHandover;
  adminWorkflow?: AdminWorkflow;
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

const defaultLivingBudget = (): LivingBudget => ({
  rentOrBond: 0,
  groceries: 0,
  electricityWater: 0,
  transport: 0,
  schoolFees: 0,
  insurance: 0,
  medical: 0,
  cellphoneInternet: 0,
  clothing: 0,
  maintenance: 0,
  otherLivingExpenses: 0,
  dependants: 0,
  notes: ''
});

const emptyCoach = (): CoachResult => ({
  service: 'Needs Manual Review',
  urgency: 'Low',
  headline: 'Create or select a client',
  reasons: ['Add a client or upload a credit report to generate the sales route.'],
  nextSteps: ['Open the client list, select a tenant, and start with a new client or upload a report.'],
  objectionHandlers: [],
  painPoints: [],
  budgetBenefits: [],
  tonalityTips: [],
  talkTrack: [],
  totals: { outstanding: 0, arrears: 0, originalInstalment: 0, reducedInstalment: 0, estimatedRelief: 0, householdIncome: 0, livingExpenses: 0, availableAfterLivingExpenses: 0, availableAfterReducedPayment: 0, savingsPercent: 0 },
  flags: { debtReviewListed: false, hasAsset: false, hasFurniture: false, scoreZeroRule: false, doubleSaleCandidate: false }
});


const requiredDocumentsFor = (service: ServiceType): string[] => {
  if (service === 'Debt Review Sales Coach') return ['Signed Form 16', 'ID copy', 'Latest payslip', '3 months bank statements'];
  if (service === 'Debt Review Removal') return ['ID copy', '3 months bank statements', 'Signed Form 17.W / 17.3', 'Latest payslip', 'Power of Attorney (POA)'];
  if (service === 'Debt Mediation') return ['ID copy', '3 months bank statements', 'Latest payslip', 'Power of Attorney (POA)'];
  return ['ID copy', 'Latest payslip', '3 months bank statements'];
};

const defaultDocuments = (service: ServiceType): ClientDocuments => ({
  required: requiredDocumentsFor(service),
  items: requiredDocumentsFor(service).map((name) => ({ name, status: 'Missing' })),
  requestStatus: 'Not Sent',
  sentAt: '',
  uploadLink: ''
});

const defaultSignature = (): ClientSignature => ({ status: 'Not Sent', link: '', sentAt: '', signedAt: '' });
const defaultNuPay = (mandateType?: NuPayMandateKind): NuPayMandate => ({
  status: 'Not Sent',
  mandateId: '',
  link: '',
  amount: 0,
  debitDay: '25',
  startDate: '',
  mandateType,
  drrMonths: mandateType === 'removal' ? 3 : 0,
  includesDrrFee: mandateType === 'removal',
  components: { reducedPayment: 0, drrServiceFeeTotal: 0, drrServiceFeeMonthly: 0, totalMonthlyCollection: 0, ongoingMonthlyCollection: 0, drrFeeMonthsRemaining: 0, collectionMode: 'Not Sent', mandateKind: mandateType },
  sentAt: '',
  cancelledAt: '',
  history: []
});
const defaultSplitMandates = (): NuPayMandates => ({ removal: defaultNuPay('removal'), mediation: defaultNuPay('mediation') });
const defaultAdminHandover = (): AdminHandover => ({ status: 'Not Submitted', submittedAt: '', submittedBy: '', notes: '', snapshot: {} });
const defaultPda = (): PdaInfo => ({ pdaName: '', pdaReference: '', proposalAmount: 0, paymentStartDate: '', status: 'Not Submitted', notes: '' });

const uniqueServices = (items: ServiceType[]): ServiceType[] => Array.from(new Set(items.filter(Boolean))) as ServiceType[];

const servicesForAdmin = (client: Client, coach: CoachResult): ServiceType[] => {
  const primary = (client.serviceType || coach.service || 'Needs Manual Review') as ServiceType;
  const services: ServiceType[] = [];
  if (primary === 'Debt Review Removal') {
    services.push('Debt Review Removal');
    if ((coach.flags?.doubleSaleCandidate || coach.totals.outstanding > 0) && coach.totals.outstanding > 0) services.push('Debt Mediation');
  } else if (primary === 'Debt Review Sales Coach') {
    services.push('Debt Review Sales Coach');
  } else if (primary === 'Debt Mediation') {
    services.push('Debt Mediation');
  } else {
    services.push('Needs Manual Review');
  }
  return uniqueServices(services);
};


const clampDrrMonths = (months: number | string | undefined): number => {
  const parsed = Math.round(toNumber(months || 3));
  if (parsed < 1) return 1;
  if (parsed > 3) return 3;
  return parsed;
};

const mandateBreakdownFor = (client: Client, coach: CoachResult, months?: number | string): { amount: number; drrMonths: number; includesDrrFee: boolean; components: NuPayComponents } => {
  const services = client.adminWorkflow?.services || client.serviceTypes || servicesForAdmin(client, coach);
  const includesDrrFee = services.includes('Debt Review Removal') || client.serviceType === 'Debt Review Removal' || coach.service === 'Debt Review Removal';
  const reducedPaymentRaw = toNumber(coach.totals.reducedInstalment);
  const includesMediationPayment = services.includes('Debt Mediation') || client.serviceType === 'Debt Mediation' || coach.service === 'Debt Mediation' || reducedPaymentRaw > 0;
  const drrMonthsValue = includesDrrFee ? clampDrrMonths(months || client.nupayMandate?.drrMonths || 3) : 0;
  const reducedPayment = includesMediationPayment ? reducedPaymentRaw : 0;
  const drrServiceFeeTotal = includesDrrFee ? drrFee : 0;
  const drrServiceFeeMonthly = includesDrrFee && drrMonthsValue ? Number((drrServiceFeeTotal / drrMonthsValue).toFixed(2)) : 0;
  const totalMonthlyCollection = Number((reducedPayment + drrServiceFeeMonthly).toFixed(2));
  const collectionMode = includesDrrFee && reducedPayment > 0
    ? 'DebiCheck: DRR service fee plus mediation reduced payment'
    : includesDrrFee
      ? 'DebiCheck: DRR service fee only'
      : reducedPayment > 0
        ? 'DebiCheck: mediation reduced payment only'
        : 'No NuPay DebiCheck collection configured';
  return {
    amount: totalMonthlyCollection,
    drrMonths: drrMonthsValue,
    includesDrrFee,
    components: {
      reducedPayment,
      drrServiceFeeTotal,
      drrServiceFeeMonthly,
      totalMonthlyCollection,
      ongoingMonthlyCollection: reducedPayment,
      drrFeeMonthsRemaining: drrMonthsValue,
      collectionMode,
      product: 'NuPay DebiCheck',
      reducedPaymentLabel: 'Debt Mediation / reduced creditor payment',
      drrFeeLabel: 'Debt Review Removal service fee'
    }
  };
};


type SplitDebiCheckPart = { applicable: boolean; amount: number; debitDay: string; startDate: string; drrMonths: number; includesDrrFee: boolean; components: NuPayComponents };
const splitDebiCheckFor = (client: Client, coach: CoachResult, months?: number | string): { removal: SplitDebiCheckPart; mediation: SplitDebiCheckPart } => {
  const services = client.adminWorkflow?.services || client.serviceTypes || servicesForAdmin(client, coach);
  const hasRemoval = services.includes('Debt Review Removal') || client.serviceType === 'Debt Review Removal' || coach.service === 'Debt Review Removal';
  const hasMediation = services.includes('Debt Mediation') || client.serviceType === 'Debt Mediation' || coach.service === 'Debt Mediation';
  const monthsValue = hasRemoval ? clampDrrMonths(months || client.nupayMandates?.removal?.drrMonths || client.nupayMandate?.drrMonths || 3) : 0;
  const removalMonthly = hasRemoval && monthsValue ? Number((drrFee / monthsValue).toFixed(2)) : 0;
  const mediationMonthly = hasMediation ? Number(toNumber(coach.totals.reducedInstalment).toFixed(2)) : 0;
  const defaultDebitDay = client.bank?.debitDay || '25';
  return {
    removal: {
      applicable: hasRemoval,
      amount: removalMonthly,
      debitDay: client.nupayMandates?.removal?.debitDay || defaultDebitDay,
      startDate: client.nupayMandates?.removal?.startDate || '',
      drrMonths: monthsValue,
      includesDrrFee: hasRemoval,
      components: {
        reducedPayment: 0,
        drrServiceFeeTotal: hasRemoval ? drrFee : 0,
        drrServiceFeeMonthly: removalMonthly,
        totalMonthlyCollection: removalMonthly,
        ongoingMonthlyCollection: 0,
        drrFeeMonthsRemaining: monthsValue,
        collectionMode: hasRemoval ? 'Separate DebiCheck: Debt Review Removal service fee' : 'Not applicable',
        product: 'NuPay DebiCheck',
        drrFeeLabel: 'Debt Review Removal service fee',
        startDate: client.nupayMandates?.removal?.startDate || '',
        mandateKind: 'removal'
      }
    },
    mediation: {
      applicable: hasMediation && mediationMonthly > 0,
      amount: mediationMonthly,
      debitDay: client.nupayMandates?.mediation?.debitDay || defaultDebitDay,
      startDate: client.nupayMandates?.mediation?.startDate || '',
      drrMonths: 0,
      includesDrrFee: false,
      components: {
        reducedPayment: mediationMonthly,
        drrServiceFeeTotal: 0,
        drrServiceFeeMonthly: 0,
        totalMonthlyCollection: mediationMonthly,
        ongoingMonthlyCollection: mediationMonthly,
        drrFeeMonthsRemaining: 0,
        collectionMode: mediationMonthly > 0 ? 'Separate DebiCheck: Debt Mediation reduced payment' : 'Not applicable',
        product: 'NuPay DebiCheck',
        reducedPaymentLabel: 'Debt Mediation / reduced creditor payment',
        startDate: client.nupayMandates?.mediation?.startDate || '',
        mandateKind: 'mediation'
      }
    }
  };
};


const adminTaskTemplates = (services: ServiceType[]): AdminTask[] => {
  const rows: AdminTask[] = [];
  const slug = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const addStep = (
    service: ServiceType,
    sequence: number,
    phase: string,
    label: string,
    options: Partial<AdminTask> = {}
  ) => rows.push({
    id: `${slug(service)}-step-${String(sequence).padStart(2, '0')}-${slug(label).slice(0, 42)}`,
    service,
    sequence,
    stepCode: `${slug(service).toUpperCase().slice(0, 3)}-${String(sequence).padStart(2, '0')}`,
    phase,
    label,
    status: 'Not Started',
    notes: '',
    ownerRole: options.ownerRole || (phase.includes('PDA') || phase.includes('Collections') || phase.includes('Monitoring') ? 'Admin/PDA' : 'Admin'),
    dueBusinessDays: options.dueBusinessDays ?? null,
    dueFrom: options.dueFrom || '',
    regulationRef: options.regulationRef || '',
    evidenceRequired: options.evidenceRequired || '',
    ncaMinimum: Boolean(options.ncaMinimum),
    gate: options.gate || '',
    outcome: options.outcome || ''
  });

  services.forEach((service) => {
    if (service === 'Debt Review Sales Coach') {
      const dr = 'NCA s86 / Regulation 24 operational control';
      addStep(service, 1, 'Sales Handover', 'Capture sale tracker fields: PDA, lead, closer, sale date, sale type, DC value, debit order amount and payment method', { evidenceRequired: 'Consultant handover snapshot with lead/closer, sale date, service type, DC value, debit day and payment method', outcome: 'Admin file opened' });
      addStep(service, 2, 'Sales Handover', 'Confirm client status, application status and reason notes before admin starts processing', { evidenceRequired: 'Client status, application status and reasoning notes from sales tracker' });
      addStep(service, 3, 'Client Docs', 'Confirm only required client documents: signed Form 16, ID copy, latest payslip and 3 months bank statements', { evidenceRequired: 'Signed Form 16, ID copy, latest payslip, 3 months bank statements', ncaMinimum: true, gate: 'Do not send 17.1 until signed Form 16 and minimum docs are confirmed' });
      addStep(service, 4, 'Client Docs', 'Verify ID number, contact details, marital/joint status, single/joint application and spouse details where applicable', { evidenceRequired: 'Verified client profile and single/joint application status', ncaMinimum: true });
      addStep(service, 5, 'Payment / DebiCheck', 'Confirm debit day, debit month/frequency, DebiCheck or payment method and first collection readiness', { evidenceRequired: 'DebiCheck/payment method record, debit day and collection month', ownerRole: 'Admin/PDA' });
      addStep(service, 6, 'DHS / Flag', 'Capture DHS status, flag number and flagged date from tracker/DHS/credit-report evidence', { evidenceRequired: 'DHS status, flag number and flagged date', ncaMinimum: true });
      addStep(service, 7, '17.1 / COB', 'Send Form 17.1 to all included credit providers and bureaus', { dueBusinessDays: 5, dueFrom: 'Signed Form 16/application received', regulationRef: dr, evidenceRequired: '17.1 sent date, proof of dispatch and 17.1 due date per creditor/bureau', ncaMinimum: true });
      addStep(service, 8, '17.1 / COB', 'Request and follow up Certificates of Balance for every included creditor', { dueBusinessDays: 5, dueFrom: '17.1 dispatch', regulationRef: dr, evidenceRequired: 'COB requested/received date, COB due date and creditor follow-up notes', ncaMinimum: true });
      addStep(service, 9, '17.1 / COB', 'Capture and reconcile COB balances, arrears, instalments and account statuses against the credit report', { evidenceRequired: 'Reconciled COB schedule with discrepancy notes', ncaMinimum: true });
      addStep(service, 10, 'Assessment / 17.2', 'Complete affordability and over-indebtedness assessment using income, bank statements, payslip, budget and COBs', { dueBusinessDays: 30, dueFrom: 'Application date', regulationRef: 'NCA s86(6) assessment control', evidenceRequired: 'Assessment worksheet and budget affordability summary', ncaMinimum: true });
      addStep(service, 11, 'Assessment / 17.2', 'Issue/capture Form 17.2 outcome and date; stop Debt Review if rejected/not over-indebted', { dueBusinessDays: 30, dueFrom: 'Application date', regulationRef: 'NCA s86 / Regulation 24 decision notification', evidenceRequired: '17.2 sent/accepted/rejected date and proof of dispatch', ncaMinimum: true, gate: 'Rejected matters must close or move to mediation/removal only if applicable' });
      addStep(service, 12, 'Proposal', 'Send client calculation and capture date sent before finalising the proposal', { evidenceRequired: 'Client calculation sent flag/date and calculation copy' });
      addStep(service, 13, 'Proposal', 'Prepare and send provisional proposal to included creditors', { evidenceRequired: 'Proposal sent date, proposal due date and dispatch proof', ncaMinimum: true });
      addStep(service, 14, 'Acceptances / Rework', 'Track acceptances, outstanding acceptances, counters and acceptance due dates per creditor', { evidenceRequired: 'Acceptance register, due dates and creditor responses', ncaMinimum: true });
      addStep(service, 15, 'Acceptances / Rework', 'Manage rework items and capture rework date, reason and updated proposal values', { evidenceRequired: 'Rework note/date and updated proposal pack' });
      addStep(service, 16, 'Final Proposal / Legal', 'Finalise proposal and capture final proposal date and due date', { evidenceRequired: 'Final proposal copy/date and due date', ncaMinimum: true });
      addStep(service, 17, 'Final Proposal / Legal', 'Send to legal/magistrate/NCT/court route where required and capture magistrate/court order status', { dueBusinessDays: 60, dueFrom: 'Application date', regulationRef: 'NCA s86(8), s87 and s86(10) risk control', evidenceRequired: 'Legal pack, magistrate/case number, court order or submission proof', ncaMinimum: true });
      addStep(service, 18, 'PDA / Collections', 'Capture PDA name/reference, collection amount, first payment date and active payment status', { evidenceRequired: 'PDA reference/payment schedule/collection status', ncaMinimum: true, ownerRole: 'Admin/PDA' });
      addStep(service, 19, 'PDA / Collections', 'Track collections, failed payments, reasons for no payment, restrike date, cash deposits and follow-up dates', { evidenceRequired: 'Collections notes, failed-payment reason, restrike/cash deposit/follow-up/solved dates', ownerRole: 'Admin/PDA' });
      addStep(service, 20, 'PDA / Collections', 'Monitor monthly M1/M2 payment status, missed payments, disputes and payment confirmations', { evidenceRequired: 'Monthly payment notes and proof of payment/distribution', ownerRole: 'Admin/PDA' });
      addStep(service, 21, 'Paid-Up / Clearance', 'Collect paid-up letters and settlement confirmations when accounts settle', { evidenceRequired: 'Paid-up letters and settlement confirmations', ownerRole: 'Admin/PDA' });
      addStep(service, 22, 'Paid-Up / Clearance', 'Issue Form 19 only when legal clearance requirements are met', { regulationRef: 'NCA s71 / NCR Form 19', evidenceRequired: 'Form 19, paid-up proof and debt counsellor approval', ncaMinimum: true, ownerRole: 'Admin/PDA', gate: 'Successful legal end of Debt Review' });
      addStep(service, 23, 'Bureau Closure', 'Send clearance/update to bureaus and verify debt-review flag removal/update', { evidenceRequired: 'Bureau update proof and final credit-report/status check', ncaMinimum: true, ownerRole: 'Admin/PDA' });
      addStep(service, 24, 'Closed', 'Notify client, lock audit trail and close admin file', { evidenceRequired: 'Client closure notice and final audit note', ownerRole: 'Admin/PDA', outcome: 'Debt Review file completed' });
    }
    if (service === 'Debt Review Removal') {
      addStep(service, 1, 'Removal Handover', 'Capture removal tracker fields: sale date, code/reference, consultant, debit amount/date/month/duration and application status', { evidenceRequired: 'Removal handover snapshot with fee, debit duration, app status and notes' });
      addStep(service, 2, 'Removal Docs', 'Confirm only required docs: ID copy, 3 months bank statements, signed 17.W/17.3, latest payslip and POA', { evidenceRequired: 'ID, 3 months bank statements, signed 17.W/17.3, latest payslip, POA', ncaMinimum: true });
      addStep(service, 3, 'Removal Docs', 'Confirm signature received and client authority before removal work starts', { evidenceRequired: 'Signature/POA status', ncaMinimum: true });
      addStep(service, 4, 'Removal DebiCheck', 'Send/confirm separate NuPay DebiCheck for the DRR removal fee only', { evidenceRequired: 'Removal DebiCheck mandate, accepted status, debit date/month and M1-M6 split', ncaMinimum: true });
      addStep(service, 5, 'DHS / Transfer', 'Verify DHS/debt-review status, transfer status and previous debt counsellor/17.7 status where applicable', { evidenceRequired: 'DHS status, transfer status, transfer accepted/declined and previous DC notes', ncaMinimum: true });
      addStep(service, 6, '17.W / 17.3', 'Confirm 17.W/17.3 route and received date/status', { evidenceRequired: '17.W/17.3 document and route decision', ncaMinimum: true, gate: 'Do not promise removal until route is verified' });
      addStep(service, 7, 'Removal Pack', 'Prepare bureau/NCR/previous-DC/court/NCT removal pack based on verified route', { evidenceRequired: 'Removal pack and supporting documents', ncaMinimum: true });
      addStep(service, 8, 'Court / Legal', 'Capture court date, case number, court order, PS Legal/Freemee allocation where applicable', { evidenceRequired: 'Case number, court date/order or legal allocation note' });
      addStep(service, 9, 'Paid-Up / Clearance', 'Track paid-up letters, cash deposits, transfer completed and clearance certificate where needed', { evidenceRequired: 'Paid-up letters, cash deposit proof, transfer completion or clearance certificate' });
      addStep(service, 10, 'Confirmation', 'Verify final bureau/credit-report update and confirm flag removed or corrected', { evidenceRequired: 'Final bureau/report status proof', ncaMinimum: true });
      addStep(service, 11, 'Closed', 'Notify client and close the DRR file', { evidenceRequired: 'Client closure notice and audit note' });
    }
    if (service === 'Debt Mediation') {
      addStep(service, 1, 'Mediation Handover', 'Capture sales tracker fields: lead, closer, sale date, sale type, DC value/reduced payment and payment method', { evidenceRequired: 'Mediation handover snapshot with consultant, sale date and reduced payment' });
      addStep(service, 2, 'Mediation Docs', 'Confirm only required docs: ID copy, 3 months bank statements, latest payslip and POA', { evidenceRequired: 'ID, 3 months bank statements, latest payslip, POA', ncaMinimum: true });
      addStep(service, 3, 'Budget / Affordability', 'Verify budget, income and available amount for mediation proposal', { evidenceRequired: 'Living budget and affordability summary', ncaMinimum: true });
      addStep(service, 4, 'Mediation DebiCheck', 'Send/confirm separate NuPay DebiCheck for the ongoing mediation/reduced payment only', { evidenceRequired: 'Mediation DebiCheck mandate, start date and amount', ownerRole: 'Admin/PDA' });
      addStep(service, 5, 'Creditor Schedule', 'Confirm included creditors and remove excluded/closed/non-negotiated accounts', { evidenceRequired: 'Mediation creditor schedule', ncaMinimum: true });
      addStep(service, 6, 'Client Calc / Proposal', 'Send client calculation and capture date sent', { evidenceRequired: 'Client calc sent flag/date and calculation copy' });
      addStep(service, 7, 'Proposal', 'Prepare and send creditor proposals', { evidenceRequired: 'Proposal sent date, due date and dispatch proof', ncaMinimum: true });
      addStep(service, 8, 'Acceptances / Counter', 'Track acceptances, outstanding acceptances, counters and follow-up notes', { evidenceRequired: 'Creditor acceptance/counter/outstanding register', ncaMinimum: true });
      addStep(service, 9, 'Rework', 'Capture rework items, more-money requests or revised reduced amount', { evidenceRequired: 'Rework/more-money note and revised proposal' });
      addStep(service, 10, 'Collections', 'Track first payment, failed DebiCheck, collections feedback, restrike and client promise-to-pay', { evidenceRequired: 'Collection notes, failed payment reasons and solved/follow-up dates', ownerRole: 'Admin/PDA' });
      addStep(service, 11, 'Active / Closed', 'Move to active monitoring or close when arrangement is completed/cancelled', { evidenceRequired: 'Active-monitoring or closure note', ownerRole: 'Admin/PDA' });
    }
    if (service === 'Needs Manual Review') {
      addStep(service, 1, 'Manual Review', 'Review parser output and select the correct service route before admin processing', { evidenceRequired: 'Manual-review note', ncaMinimum: true });
      addStep(service, 2, 'Manual Review', 'Confirm required documents, payment and compliance risk before processing', { evidenceRequired: 'Admin decision note', ncaMinimum: true });
    }
  });
  return rows;
};

const defaultAdminWorkflowFor = (client: Client, coach: CoachResult): AdminWorkflow => {
  const services = servicesForAdmin(client, coach);
  const tasks = adminTaskTemplates(services);
  const creditorActions: AdminCreditorAction[] = (client.accounts || []).filter((account) => account.included).map((account) => ({
    id: account.id,
    service: services.includes('Debt Mediation') ? 'Debt Mediation' : services[0],
    creditorName: account.creditorName,
    accountNumber: account.accountNumber,
    status: 'Not Contacted',
    currentBalance: toNumber(account.currentBalance),
    originalInstallment: toNumber(account.monthlyInstallment),
    proposedAmount: toNumber(account.reducedAmount),
    response: '',
    notes: ''
  }));
  const feeItems: AdminFeeItem[] = [];
  if (services.includes('Debt Review Removal')) feeItems.push({ id: 'drr-service-fee', label: 'Debt Review Removal service fee', service: 'Debt Review Removal', amount: drrFee, status: 'Not Invoiced', notes: 'Can be split over 1 to 3 months.' });
  if (coach.totals.reducedInstalment > 0) feeItems.push({ id: 'reduced-payment-proposal', label: 'Reduced payment / NuPay proposal', service: services.includes('Debt Mediation') ? 'Debt Mediation' : services[0], amount: coach.totals.reducedInstalment, status: client.nupayMandate?.status || 'Not Sent', notes: 'Must match affordability and mandate.' });
  return { services, activeService: services[0], overallStatus: 'Handover Received', tasks, creditorActions, feeItems, lastUpdatedAt: '' };
};

const mergeAdminWorkflow = (client: Client, coach: CoachResult): AdminWorkflow => {
  const generated = defaultAdminWorkflowFor(client, coach);
  const existing = client.adminWorkflow;
  if (!existing) return generated;
  const existingTasks = new Map((existing.tasks || []).map((task) => [task.id, task]));
  const existingCreditors = new Map((existing.creditorActions || []).map((item) => [item.id, item]));
  const existingFees = new Map((existing.feeItems || []).map((item) => [item.id, item]));
  return {
    ...generated,
    activeService: (existing.activeService || generated.activeService) as ServiceType,
    overallStatus: existing.overallStatus || generated.overallStatus,
    tasks: generated.tasks.map((task) => ({ ...task, ...(existingTasks.get(task.id) || {}) })),
    creditorActions: generated.creditorActions.map((item) => ({ ...item, ...(existingCreditors.get(item.id) || {}) })),
    feeItems: generated.feeItems.map((item) => ({ ...item, ...(existingFees.get(item.id) || {}) })),
    lastUpdatedAt: existing.lastUpdatedAt || generated.lastUpdatedAt
  };
};

const withWorkflowDefaults = (client: Client): Client => {
  const service = (client.serviceType || client.coach?.service || 'Needs Manual Review') as ServiceType;
  const required = requiredDocumentsFor(service);
  const previousItems = client.documents?.items || [];
  const existingItems = new Map(previousItems.map((item) => [item.name, item]));
  const documents: ClientDocuments = {
    required,
    items: required.map((name) => existingItems.get(name) || { name, status: 'Missing' }),
    requestStatus: client.documents?.requestStatus || 'Not Sent',
    sentAt: client.documents?.sentAt || '',
    uploadLink: client.documents?.uploadLink || client.portalLinks?.uploadLink || ''
  };
  return {
    ...client,
    bank: client.bank || { accountHolder: '', bankName: '', accountType: '', branchCode: '', accountNumber: '', debitDay: '25', mandateAccepted: false },
    budget: { ...defaultLivingBudget(), ...(client.budget || {}) },
    spouse: client.spouse || emptyApplicant(),
    accounts: client.accounts || [],
    documents,
    signature: { ...defaultSignature(), ...(client.signature || {}), link: client.signature?.link || client.portalLinks?.signatureLink || '' },
    nupayMandate: (() => {
      const coachForMandate = client.coach || emptyCoach();
      const breakdown = mandateBreakdownFor(client, coachForMandate, client.nupayMandate?.drrMonths || 3);
      const storedAmount = toNumber(client.nupayMandate?.amount || 0);
      const shouldUseCalculated = !storedAmount || (breakdown.includesDrrFee && storedAmount <= breakdown.components.reducedPayment + 0.01);
      return {
        ...defaultNuPay(),
        ...(client.nupayMandate || {}),
        amount: shouldUseCalculated ? breakdown.amount : storedAmount,
        debitDay: client.nupayMandate?.debitDay || client.bank?.debitDay || '25',
        drrMonths: client.nupayMandate?.drrMonths || breakdown.drrMonths,
        includesDrrFee: breakdown.includesDrrFee,
        components: client.nupayMandate?.components || breakdown.components,
        history: client.nupayMandate?.history || []
      };
    })(),
    nupayMandates: (() => {
      const splitDefaults = defaultSplitMandates();
      return {
        removal: { ...splitDefaults.removal, ...(client.nupayMandates?.removal || {}), mandateType: 'removal', history: client.nupayMandates?.removal?.history || [] },
        mediation: { ...splitDefaults.mediation, ...(client.nupayMandates?.mediation || {}), mandateType: 'mediation', history: client.nupayMandates?.mediation?.history || [] }
      };
    })(),
    adminHandover: { ...defaultAdminHandover(), ...(client.adminHandover || {}) },
    pdaInfo: { ...defaultPda(), ...(client.pdaInfo || {}), proposalAmount: toNumber(client.pdaInfo?.proposalAmount || client.coach?.totals.reducedInstalment || 0) },
    serviceTypes: mergeAdminWorkflow(client, client.coach || emptyCoach()).services,
    adminWorkflow: mergeAdminWorkflow(client, client.coach || emptyCoach())
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
  budget: defaultLivingBudget(),
  creditScore: null,
  scoreFound: false,
  debtReviewListed: false,
  notes: '',
  status: 'Lead Received',
  serviceType: 'Needs Manual Review',
  serviceTypes: ['Needs Manual Review'],
  accounts: [],
  coach: emptyCoach(),
  documents: defaultDocuments('Needs Manual Review'),
  signature: defaultSignature(),
  nupayMandate: defaultNuPay(),
  nupayMandates: defaultSplitMandates(),
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

function heatMeta(value: number | string | undefined) {
  const total = toNumber(value);
  const heatBlocks = Math.floor(total / 5000);
  const progressToNextHeat = Math.min(100, Math.round(((total % 5000) / 5000) * 100));
  const nextHeatGap = Math.max(0, 5000 - (total % 5000 || 0));
  const heatLabel = heatBlocks >= 10 ? 'Inferno' : heatBlocks >= 6 ? 'Blazing' : heatBlocks >= 3 ? 'Heating Up' : heatBlocks >= 1 ? 'Warm' : 'Cold Start';
  const heatEmoji = heatBlocks >= 10 ? '🔥🔥🔥' : heatBlocks >= 6 ? '🔥🔥' : heatBlocks >= 3 ? '🔥' : heatBlocks >= 1 ? '♨️' : '🌡️';
  return { heatBlocks, progressToNextHeat, nextHeatGap, heatLabel, heatEmoji };
}

function HeatMeter({ value, label }: { value: number; label?: string }) {
  const heat = heatMeta(value);
  return (
    <div className="heat-meter">
      <div className="heat-top"><span>{heat.heatEmoji} {label || heat.heatLabel}</span><strong>{heat.heatBlocks} heat block(s)</strong></div>
      <div className="thermometer-track"><span style={{ width: `${heat.progressToNextHeat}%` }} /></div>
      <small>{currency(value)} · {currency(heat.nextHeatGap)} to next R5,000 heat boost</small>
    </div>
  );
}

function livingExpenseTotal(budget: LivingBudget | undefined): number {
  const item = { ...defaultLivingBudget(), ...(budget || {}) };
  return ['rentOrBond', 'groceries', 'electricityWater', 'transport', 'schoolFees', 'insurance', 'medical', 'cellphoneInternet', 'clothing', 'maintenance', 'otherLivingExpenses']
    .reduce((total, key) => total + toNumber(item[key as keyof LivingBudget] as number), 0);
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
  const rawCreditor = String(account.creditorName || '').trim();
  const creditor = rawCreditor.toLowerCase();
  const accountNumber = String(account.accountNumber || '').trim();
  const badWords = ['total no', 'total number', 'counts', 'payment profile', 'account summary', 'enquiry', 'friday', 'monday', 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday', 'months in arrears'];
  if (!creditor || creditor === 'unknown creditor') return true;
  if (badWords.some((word) => creditor.includes(word))) return true;
  const letters = (rawCreditor.match(/[A-Za-z]/g) || []).length;
  const digits = (rawCreditor.match(/\d/g) || []).length;
  if (letters === 0 && digits >= 4) return true;
  if (digits >= 5 && digits > letters * 2) return true;
  if (/^[A-Za-z]?\d[\d\- /]{4,}$/.test(rawCreditor)) return true;
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
  const savingsPercent = originalInstalment > 0 ? Math.round((estimatedRelief / originalInstalment) * 100) : 0;
  const householdIncome = toNumber(client.nettSalary) + (client.applicationType === 'Joint' ? toNumber(client.spouse?.nettSalary) : 0);
  const livingExpenses = livingExpenseTotal(client.budget);
  const availableAfterLivingExpenses = householdIncome - livingExpenses;
  const availableAfterOriginalPayments = availableAfterLivingExpenses - originalInstalment;
  const availableAfterReducedPayment = availableAfterLivingExpenses - reducedInstalment;
  const hasAsset = included.some((account) => account.isAsset || /vehicle|home loan|bond|mortgage|wesbank|mfc/i.test(account.creditorName));
  const hasFurniture = included.some((account) => account.isFurniture || /russells|bradlows|lewis|furniture|beares|jd/i.test(account.creditorName));
  const scoreIsKnown = Boolean(client.scoreFound) && client.creditScore !== null && client.creditScore !== undefined && String(client.creditScore) !== '';
  const numericScore = scoreIsKnown ? Number(client.creditScore) : null;
  const scoreZeroRule = scoreIsKnown && numericScore === 0;
  const debtReviewListed = Boolean(client.debtReviewListed || scoreZeroRule);
  const selectedServices = Array.isArray(client.serviceTypes) ? client.serviceTypes : [];
  const selectedRemovalService = client.serviceType === 'Debt Review Removal' || selectedServices.includes('Debt Review Removal');
  const noActiveBalances = outstanding <= 0 && originalInstalment <= 0 && arrears <= 0;
  const noBalanceRemovalLead = noActiveBalances && (debtReviewListed || selectedRemovalService);

  let service: ServiceType = 'Debt Mediation';
  let urgency: Urgency = 'Medium';
  let headline = 'Debt mediation opportunity detected';
  const reasons: string[] = [];
  let nextSteps: string[] = [];
  let objectionHandlers: string[] = [];
  const painPoints: string[] = [];
  const budgetBenefits: string[] = [];
  const tonalityTips: string[] = [];
  const talkTrack: string[] = [];

  if (noBalanceRemovalLead) {
    service = 'Debt Review Removal';
    urgency = 'High';
    headline = 'Debt Review Removal: clear the flag and restore credit-worthiness';
    reasons.push('No active balances or monthly instalments are showing, so the sale should not be positioned as debt reduction.');
    reasons.push('Focus on verifying and removing the debt-review flag so the client can become credit-worthy again.');
  } else if (debtReviewListed) {
    service = 'Debt Review Removal';
    urgency = 'High';
    headline = 'Debt Review Removal lead';
    reasons.push('The report indicates a debt-review flag or score-zero rule, so DR removal must be checked first.');
    if (outstanding > 0) reasons.push('Balances still show on the report, so this can become a double sale: removal plus mediation.');
  } else if (hasAsset) {
    service = 'Debt Review Sales Coach';
    urgency = 'High';
    headline = 'Asset-protection opportunity';
    reasons.push('Home loan or vehicle finance style accounts were detected. Lead with protecting the client’s asset.');
  } else if (scoreIsKnown && numericScore !== null && numericScore >= 400 && numericScore <= 650 && arrears > 0) {
    service = 'Debt Mediation';
    urgency = 'High';
    headline = 'Debt mediation lead with arrears pressure';
    reasons.push('The score and arrears pattern suggest the client needs urgent affordability relief.');
  } else if (outstanding > 0) {
    service = 'Debt Mediation';
    urgency = 'Medium';
    headline = 'Debt mediation lead';
    reasons.push('Outstanding balances are present and can be negotiated into a structured repayment plan.');
  } else {
    service = 'Needs Manual Review';
    urgency = 'Low';
    headline = 'Manual assessment needed';
    reasons.push('The current data does not show enough debt to recommend a sale safely.');
  }

  if (hasFurniture) reasons.push('Furniture accounts detected. Tag them because clients often ask whether household goods are at risk.');
  if (originalInstalment > 0) reasons.push(`Estimated instalment relief is ${currency(estimatedRelief)} before final affordability checks.`);

  if (householdIncome > 0 && livingExpenses > 0) {
    const livingRatio = Math.round((livingExpenses / householdIncome) * 100);
    painPoints.push(`Living expenses are using about ${livingRatio}% of household nett income before debt repayments.`);
  }
  if (originalInstalment > 0 && householdIncome > 0) {
    if (availableAfterOriginalPayments < 0) {
      painPoints.push(`Before the proposed reduction, the client is short by ${currency(Math.abs(availableAfterOriginalPayments))} after living expenses and normal instalments.`);
    } else {
      painPoints.push(`Before the proposed reduction, only ${currency(availableAfterOriginalPayments)} remains after living expenses and normal instalments.`);
    }
  }
  if (arrears > 0) painPoints.push(`Arrears of ${currency(arrears)} show that the pressure is already visible, not only theoretical.`);
  if (estimatedRelief > 0) {
    budgetBenefits.push(`The proposed reduction can free up about ${currency(estimatedRelief)} per month, roughly ${savingsPercent}% less than current instalments.`);
    budgetBenefits.push(`That saving can be positioned as breathing room for groceries, transport, electricity and keeping the payment plan consistent.`);
  }
  if (availableAfterReducedPayment >= 0 && reducedInstalment > 0) {
    budgetBenefits.push(`After living expenses and the proposed payment, the budget still shows ${currency(availableAfterReducedPayment)} available.`);
  } else if (reducedInstalment > 0) {
    budgetBenefits.push(`The current reduced proposal still does not fit the captured budget. Lower the reduced amounts before promising affordability.`);
  }

  if (noBalanceRemovalLead) {
    painPoints.push('The pressure point is no longer monthly debt relief; it is the debt-review flag still blocking the client from being seen as credit-worthy.');
    painPoints.push('With no balances showing, the client may feel “I am finished paying”, but the bureau/status flag can still stop approvals.');
    budgetBenefits.push('The main benefit is restoring borrowing power and credibility, not lowering an instalment.');
    budgetBenefits.push('Once the flag is correctly removed, the client may have a better chance of qualifying for future credit, vehicle finance, home finance, rental checks, cellphone contracts and business opportunities, subject to lender assessment.');
    budgetBenefits.push('The conversation should position the R7,000 removal fee as a clean-up and status-restoration service, not a payment-plan saving.');
    talkTrack.push('“The good news is that your report is not showing active balances to restructure. That means our focus is not mediation today — it is getting the debt-review flag removed correctly.”');
    talkTrack.push('“When that flag remains, credit providers can still treat you as high risk even if you have paid your accounts. Removing it helps you start rebuilding your credit-worthiness.”');
    talkTrack.push('“The benefit is not only today’s report; it is what becomes possible again afterwards — applying with a cleaner profile and rebuilding trust with lenders.”');
  }

  tonalityTips.push(noBalanceRemovalLead ? 'Use a positive, future-focused tone: “You have done the hard part by clearing the balances; now we need to clean up the status so your profile can move forward.”' : 'Use a calm, protective tone: “I can see why this has become stressful, let’s work from the numbers.”');
  tonalityTips.push('Do not shame the client or sound excited about their hardship; speak like you are helping them regain control.');
  tonalityTips.push('Ask permission before giving advice: “Can I show you what the budget is telling us?”');
  tonalityTips.push('Anchor the sale on relief and stability, not fear. Avoid guaranteeing approvals, removals or legal outcomes.');

  talkTrack.push(`“Based on your budget, your household income is ${currency(householdIncome)} and your living expenses are ${currency(livingExpenses)}.”`);
  if (estimatedRelief > 0) talkTrack.push(`“Your current instalments are about ${currency(originalInstalment)}. The proposed amount is ${currency(reducedInstalment)}, which could free up around ${currency(estimatedRelief)} every month.”`);
  if (availableAfterOriginalPayments < 0) talkTrack.push(`“Right now the numbers show a shortfall before we even look at emergencies. That is why a structured solution is important.”`);
  if (availableAfterReducedPayment >= 0 && reducedInstalment > 0) talkTrack.push(`“With the reduced amount, the budget becomes more manageable because there is still an estimated ${currency(availableAfterReducedPayment)} left after living expenses and the proposal.”`);

  if (service === 'Debt Review Removal') {
    if (noBalanceRemovalLead) {
      nextSteps = ['Verify that there are no remaining active balances that need mediation.', 'Confirm the debt-review flag/status and whether the route is 17.W, 17.3, clearance/bureau correction, court/NCT or previous-DC follow-up.', 'Request ID, 3 months bank statements, latest payslip, signed 17.W/17.3 and POA.', 'Send NuPay DebiCheck for the R7,000 removal fee split over 1-3 months if the client accepts.', 'Submit the removal pack and track bureau/status confirmation until the profile is updated.'];
      objectionHandlers = ['I have no debt, why must I pay anything: explain that the service is not for balances; it is to remove the status barrier that can keep causing declined applications.', 'Will my score go up immediately: explain that removal can make the profile eligible to rebuild, but no score or approval can be guaranteed.', 'I already paid everyone: agree with the client, then explain that paid-up accounts and a removed debt-review flag are two different outcomes and both must be reflected correctly.', 'I only need a loan now: keep the tone honest — first remove the flag and rebuild credit-worthiness; do not promise a loan approval.'];
    } else {
      nextSteps = ['Confirm if the client is actively under debt review or only still bureau-flagged.', 'Request ID, 3 months bank statements, latest payslip, signed 17.W/17.3 and POA.', 'Explain the R7,000 removal fee and offer 1-3 months.', 'If balances remain, present mediation as the second sale.'];
      objectionHandlers = ['I already paid my debt counsellor: explain that payment history and current flag status still need to be verified.', 'I only want my name cleared: explain removal is step one; active balances may still affect score recovery.', `I cannot afford another fee: acknowledge it, then show the monthly split and compare it to the ${currency(estimatedRelief)} potential monthly relief where mediation also applies.`];
    }
  } else if (service === 'Debt Review Sales Coach') {
    nextSteps = ['Confirm income, expenses, and whether the client is behind on home/vehicle payments.', 'Position the call around protecting the asset and creating a sustainable plan.', 'Request signed Form 16, ID, latest payslip and 3 months bank statements, then start the statutory workflow if the client qualifies.'];
    objectionHandlers = ['I do not want debt review: explain that assets at risk need urgent protection and eligibility must be assessed first.', 'I can catch up next month: compare arrears and instalments against nett income before accepting that answer.', 'I am worried about the process: explain the admin sequence clearly — Form 16, 17.1/COB, assessment, 17.2, proposal and payment setup.'];
  } else if (service === 'Debt Mediation') {
    nextSteps = ['Confirm all income and debit orders before making a proposal.', 'Use included accounts only and adjust reduced amounts where affordability changes.', 'Send POA/upload-documents link and confirm ID, 3 months bank statements and latest payslip before contacting creditors.'];
    objectionHandlers = ['I can pay creditors myself: explain that one coordinated proposal can reduce pressure.', 'I am not in arrears yet: explain mediation can prevent arrears if affordability is already strained.', `I need to think about it: bring the client back to the numbers and the potential ${currency(estimatedRelief)} monthly saving.`];
  }

  return {
    service,
    urgency,
    headline,
    reasons,
    nextSteps,
    objectionHandlers,
    painPoints,
    budgetBenefits,
    tonalityTips,
    talkTrack,
    totals: { outstanding, arrears, originalInstalment, reducedInstalment, estimatedRelief, householdIncome, livingExpenses, availableAfterLivingExpenses, availableAfterReducedPayment, savingsPercent },
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

const adminTrackerLanes = [
  {
    title: 'Sales / Handover',
    phases: ['Sales Handover', 'Removal Handover', 'Mediation Handover', 'Consultant Handover'],
    fields: 'PDA, lead, closer, sale date, sale type, DC value, debit amount, client status'
  },
  {
    title: 'Docs + Signature',
    phases: ['Client Docs', 'Removal Docs', 'Mediation Docs', 'Required Client Documents'],
    fields: 'ID received, Form 16/17.W/17.3/POA, payslip, bank statements, signature'
  },
  {
    title: 'DebiCheck / PDA / Collections',
    phases: ['Payment / DebiCheck', 'Removal DebiCheck', 'Mediation DebiCheck', 'PDA / Collections', 'Collections'],
    fields: 'Debit day, debit month, DebiCheck status, M1/M2, failed payments, restrike, cash deposits'
  },
  {
    title: 'DHS / 17.1 / COB / 17.2',
    phases: ['DHS / Flag', 'DHS / Transfer', '17.1 / COB', 'Assessment / 17.2', '17.W / 17.3'],
    fields: 'DHS status, flag number/date, 17.1 sent/due, COB received/due, 17.2 date/outcome'
  },
  {
    title: 'Proposal / Acceptances',
    phases: ['Proposal', 'Client Calc / Proposal', 'Acceptances / Rework', 'Acceptances / Counter', 'Rework'],
    fields: 'Client calc sent, proposal sent/due, acceptances received/due, counters, rework date'
  },
  {
    title: 'Legal / Court / Closure',
    phases: ['Final Proposal / Legal', 'Court / Legal', 'Removal Pack', 'Paid-Up / Clearance', 'Bureau Closure', 'Confirmation', 'Closed', 'Active / Closed'],
    fields: 'Final proposal, send to legal, magistrate, court date/order, paid-up letters, clearance, bureau update'
  }
];

export default function App() {
  const [apiBase, setApiBase] = useState(() => localStorage.getItem('fintastic_sales_api') || 'http://localhost:5000');
  const [loggedIn, setLoggedIn] = useState(() => localStorage.getItem('fintastic_logged_in') === '1');
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState(() => localStorage.getItem('fintastic_tenant_id') || 'liberty-credit-specialists');
  const [users, setUsers] = useState<TenantUser[]>([]);
  const [userId, setUserId] = useState(() => localStorage.getItem('fintastic_user_id') || 'lib-agent-1');
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
  const [drrStartDate, setDrrStartDate] = useState('');
  const [mediationStartDate, setMediationStartDate] = useState('');
  const [adminClients, setAdminClients] = useState<Client[]>([]);
  const [handoverNotes, setHandoverNotes] = useState('');
  const [docUploadName, setDocUploadName] = useState('ID copy');
  const [consultantLeaderboard, setConsultantLeaderboard] = useState<ConsultantMetric[]>([]);
  const [teamLeaderboard, setTeamLeaderboard] = useState<TeamMetric[]>([]);
  const [dashboardSummary, setDashboardSummary] = useState<ConsultantDashboardSummary>({
    tenantClients: 0,
    uploadedReports: 0,
    leadsGenerated: 0,
    dcValue: 0,
    reducedInstallments: 0,
    removalFees: 0,
    documentsReceived: 0,
    clientsSubmitted: 0,
    requiredDocuments: 0,
    consultants: 0,
    teams: 0,
    heatBlocks: 0,
    heatLabel: 'Cold Start',
    heatEmoji: '🌡️',
    progressToNextHeat: 0,
    nextHeatGap: 5000
  });
  const [commissionSnapshot, setCommissionSnapshot] = useState<CommissionSnapshot | null>(null);
  const [commissionHistory, setCommissionHistory] = useState<CommissionSnapshot[]>([]);
  const [knowledgeModules, setKnowledgeModules] = useState<KnowledgeModule[]>([]);
  const [knowledgeQuestions, setKnowledgeQuestions] = useState<KnowledgeQuestion[]>([]);
  const [assessmentAnswers, setAssessmentAnswers] = useState<Record<string, number>>({});
  const [assessmentResult, setAssessmentResult] = useState<AssessmentResult | null>(null);
  const [knowledgeLeaderboard, setKnowledgeLeaderboard] = useState<KnowledgeRank[]>([]);

  const accounts = client.accounts || [];
  const coach = useMemo(() => evaluateCoach(client, accounts), [client, accounts]);
  const currentTenant = tenants.find((tenant) => tenant.id === tenantId);
  const currentUser = users.find((user) => user.id === userId);
  const isAdminRole = ['Admin', 'Manager'].includes(currentUser?.role || '');
  const budget = { ...defaultLivingBudget(), ...(client.budget || {}) };
  const householdIncome = toNumber(client.nettSalary) + (client.applicationType === 'Joint' ? toNumber(client.spouse?.nettSalary) : 0);
  const totalLivingExpenses = livingExpenseTotal(budget);
  const availableAfterLivingExpenses = householdIncome - totalLivingExpenses;
  const availableAfterReducedPayment = availableAfterLivingExpenses - toNumber(coach.totals.reducedInstalment);
  const currentMandateBreakdown = useMemo(() => mandateBreakdownFor(client, coach, drrMonths), [client, coach, drrMonths]);
  const splitDebiChecks = useMemo(() => splitDebiCheckFor(client, coach, drrMonths), [client, coach, drrMonths]);
  const removalDebiCheck = client.nupayMandates?.removal || defaultNuPay('removal');
  const mediationDebiCheck = client.nupayMandates?.mediation || defaultNuPay('mediation');
  const hasDrrFeeCollection = splitDebiChecks.removal.applicable;
  const hasMediationCollection = splitDebiChecks.mediation.applicable;

  const trackerLaneSummary = useMemo(() => adminTrackerLanes.map((lane) => {
    const tasks = (client.adminWorkflow?.tasks || []).filter((task) => lane.phases.includes(task.phase));
    const done = tasks.filter((task) => ['Done', 'Completed', 'Submitted'].includes(task.status)).length;
    const blocked = tasks.filter((task) => ['Blocked', 'Waiting Client', 'Waiting Creditor'].includes(task.status)).length;
    const active = tasks.length - done;
    return { ...lane, tasks, done, blocked, active };
  }), [client.adminWorkflow?.tasks]);

  const quickTabs: { key: ViewKey; label: string; helper: string }[] = [
    { key: 'profile', label: 'Client Info', helper: 'Details + joint' },
    { key: 'budget', label: 'Budget', helper: 'Living expenses' },
    { key: 'upload', label: 'Credit Report', helper: 'Upload + parse' },
    { key: 'coach', label: 'Sales Coach', helper: 'Route + script' },
    { key: 'accounts', label: 'Accounts / Fees', helper: 'Reduced amounts' },
    { key: 'documents', label: 'Docs + Signature', helper: 'Links + status' },
    { key: 'mandate', label: 'NuPay DebiCheck', helper: 'Send/cancel DebiCheck' },
    { key: 'workflow', label: 'Admin / PDA', helper: 'Submit handover' }
  ];

  const apiHeaders = { 'Content-Type': 'application/json', 'X-Tenant-ID': tenantId, 'X-User-ID': userId };

  const loadTenants = async () => {
    try {
      const response = await fetch(`${apiBase}/api/tenants`);
      const data = await response.json();
      if (data.success) setTenants(data.tenants || []);
    } catch {
      setTenants([
        { id: 'liberty-credit-specialists', name: 'Liberty Credit Specialists', ncr: 'NCRDC-1829', userCount: 3, clientCount: clients.length },
        { id: 'apex-debt-solutions', name: 'Apex Debt Solutions', ncr: 'NCRDC-2491', userCount: 2, clientCount: 0 }
      ]);
    }
  };

  const loadUsers = async (nextTenantId = tenantId) => {
    try {
      const response = await fetch(`${apiBase}/api/users`, { headers: { 'X-Tenant-ID': nextTenantId, 'X-User-ID': userId } });
      const data = await response.json();
      if (data.success) {
        setUsers(data.users || []);
        if (!data.users?.some((user: TenantUser) => user.id === userId) && data.users?.[0]) setUserId(data.users[0].id);
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
      const response = await fetch(`${apiBase}/api/clients?${params.toString()}`, { headers: { 'X-Tenant-ID': nextTenantId, 'X-User-ID': userId } });
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

  const loadDashboardMetrics = async (nextTenantId = tenantId) => {
    try {
      const response = await fetch(`${apiBase}/api/dashboard/consultants`, { headers: { 'X-Tenant-ID': nextTenantId, 'X-User-ID': userId } });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not load dashboard metrics');
      setConsultantLeaderboard(data.leaderboard || []);
      setTeamLeaderboard(data.teamLeaderboard || []);
      setDashboardSummary(data.summary || dashboardSummary);
    } catch (error) {
      console.warn(error);
      const fallbackRows = users.filter((u) => u.role === 'Consultant').map((u, index) => {
        const owned = clients.filter((c) => c.assignedUserId === u.id);
        const uploaded = owned.length;
        const reduced = owned.reduce((total, c) => total + toNumber((c.coach || evaluateCoach(c, c.accounts || [])).totals.reducedInstalment), 0);
        const removal = owned.reduce((total, c) => total + ((c.serviceTypes || [c.serviceType]).includes('Debt Review Removal') ? drrFee : 0), 0);
        const docs = owned.reduce((total, c) => total + ((c.documents?.items || []).filter((d) => d.status === 'Uploaded').length), 0);
        const rowValue = reduced + removal;
        return { rank: index + 1, userId: u.id, name: u.name, role: u.role, team: u.team || 'Main Floor', email: u.email, leadsGenerated: uploaded, uploadedReports: uploaded, activeClients: owned.length, clientsSubmitted: owned.filter((c) => c.status === 'Submitted to Admin').length, reducedInstallments: reduced, removalFees: removal, dcValue: rowValue, documentsReceived: docs, requiredDocuments: owned.reduce((total, c) => total + (c.documents?.items || []).length, 0), documentCompletionRate: 0, performanceScore: 0, ...heatMeta(rowValue) } as ConsultantMetric;
      });
      const fallbackTeams = Object.values(fallbackRows.reduce((acc, row) => {
        const team = row.team || 'Main Floor';
        acc[team] = acc[team] || { rank: 0, team, consultants: 0, leadsGenerated: 0, uploadedReports: 0, clientsSubmitted: 0, reducedInstallments: 0, removalFees: 0, dcValue: 0, documentsReceived: 0, requiredDocuments: 0, documentCompletionRate: 0, performanceScore: 0 } as TeamMetric;
        acc[team].consultants += 1;
        acc[team].leadsGenerated += row.leadsGenerated;
        acc[team].uploadedReports += row.uploadedReports;
        acc[team].clientsSubmitted += row.clientsSubmitted;
        acc[team].reducedInstallments += row.reducedInstallments;
        acc[team].removalFees += row.removalFees;
        acc[team].dcValue += row.dcValue;
        acc[team].documentsReceived += row.documentsReceived;
        acc[team].requiredDocuments += row.requiredDocuments;
        return acc;
      }, {} as Record<string, TeamMetric>)).sort((a, b) => b.dcValue - a.dcValue).map((team, index) => ({ ...team, rank: index + 1, ...heatMeta(team.dcValue) }));
      const floorDcValue = fallbackRows.reduce((t, r) => t + r.dcValue, 0);
      setConsultantLeaderboard(fallbackRows);
      setTeamLeaderboard(fallbackTeams);
      setDashboardSummary({ tenantClients: clients.length, uploadedReports: clients.length, leadsGenerated: clients.length, dcValue: floorDcValue, reducedInstallments: fallbackRows.reduce((t, r) => t + r.reducedInstallments, 0), removalFees: fallbackRows.reduce((t, r) => t + r.removalFees, 0), documentsReceived: fallbackRows.reduce((t, r) => t + r.documentsReceived, 0), clientsSubmitted: fallbackRows.reduce((t, r) => t + r.clientsSubmitted, 0), requiredDocuments: fallbackRows.reduce((t, r) => t + r.requiredDocuments, 0), consultants: fallbackRows.length, teams: fallbackTeams.length, ...heatMeta(floorDcValue) });
    }
  };

  const loadCommissionStats = async () => {
    try {
      const response = await fetch(`${apiBase}/api/manager/commission-stats`, { headers: { 'X-Tenant-ID': tenantId, 'X-User-ID': userId } });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Only manager logins can store/review commission snapshots.');
      setCommissionSnapshot(data.snapshot || null);
      setCommissionHistory(data.history || []);
      if (data.snapshot?.leaderboard) setConsultantLeaderboard(data.snapshot.leaderboard);
      if (data.snapshot?.summary) setDashboardSummary(data.snapshot.summary);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not load commission stats');
    }
  };

  const loadProductKnowledge = async () => {
    try {
      const response = await fetch(`${apiBase}/api/learning/product-knowledge`, { headers: { 'X-Tenant-ID': tenantId, 'X-User-ID': userId } });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not load product knowledge');
      setKnowledgeModules(data.modules || []);
      setKnowledgeQuestions(data.questions || []);
      setKnowledgeLeaderboard(data.leaderboard || []);
      setAssessmentResult(data.latestUserResult || null);
    } catch (error) {
      console.warn(error);
    }
  };

  const submitKnowledgeAssessment = async () => {
    try {
      const response = await fetch(`${apiBase}/api/learning/assessment/submit`, {
        method: 'POST',
        headers: apiHeaders,
        body: JSON.stringify({ answers: assessmentAnswers })
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not submit assessment');
      setAssessmentResult(data.result);
      setKnowledgeLeaderboard(data.leaderboard || []);
      alert(`Assessment saved: ${data.result.scorePercent}% - ${data.result.level}`);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not submit assessment');
    }
  };


  useEffect(() => {
    loadTenants();
  }, []);

  useEffect(() => {
    localStorage.setItem('fintastic_tenant_id', tenantId);
    localStorage.setItem('fintastic_user_id', userId);
    loadUsers(tenantId);
    loadClients('', tenantId);
  }, [tenantId]);

  useEffect(() => {
    localStorage.setItem('fintastic_user_id', userId);
  }, [userId]);

  useEffect(() => {
    setDrrMonths(client.nupayMandates?.removal?.drrMonths || client.nupayMandate?.drrMonths || 3);
    setDrrStartDate(client.nupayMandates?.removal?.startDate || '');
    setMediationStartDate(client.nupayMandates?.mediation?.startDate || '');
  }, [client.id]);

  useEffect(() => {
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

  const updateBudget = <K extends keyof LivingBudget>(field: K, value: LivingBudget[K]) => {
    setClient((current) => ({ ...current, budget: { ...defaultLivingBudget(), ...(current.budget || {}), [field]: value } }));
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
      const response = await fetch(`${apiBase}/api/clients${isLocal ? '' : `/${client.id}`}`, {
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
      const response = await fetch(endpoint, { method: 'POST', headers: { 'X-Tenant-ID': tenantId, 'X-User-ID': userId }, body: formData });
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
      const response = await fetch(`${apiBase}/api/portal/links`, {
        method: 'POST',
        headers: apiHeaders,
        body: JSON.stringify({ clientId: saved.id, tenantId, baseUrl: `${apiBase}/portal` })
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not create links');
      setClient((current) => ({ ...current, id: saved.id, portalLinks: { clientPortalLink: data.clientPortalLink || data.uploadLink || data.signatureLink, signatureLink: data.signatureLink, uploadLink: data.uploadLink, createdAt: data.createdAt } }));
      setSaveMessage(`Client portal link saved at ${new Date().toLocaleTimeString()}`);
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
    const response = await fetch(`${apiBase}/api/clients/${saved.id}${path}`, {
      method,
      headers: apiHeaders,
      body: JSON.stringify({ ...body, tenantId, baseUrl: `${apiBase}/portal` })
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Action failed');
    updateClientFromResponse(data);
    return data;
  };

  const requestDocuments = async () => {
    try {
      await postClientAction('/documents/request');
      alert('Combined documents + signature client portal link created.');
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
      const response = await fetch(`${apiBase}/api/clients/${saved.id}/documents/upload`, { method: 'POST', headers: { 'X-Tenant-ID': tenantId, 'X-User-ID': userId }, body: form });
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

  const sendSplitDebiCheck = async (mandateType: NuPayMandateKind) => {
    try {
      const split = splitDebiCheckFor(client, coach, drrMonths);
      const part = split[mandateType];
      if (!part.applicable || part.amount <= 0) {
        alert(mandateType === 'removal' ? 'Debt Review Removal fee DebiCheck is not applicable for this client.' : 'Debt Mediation DebiCheck is not applicable for this client.');
        return;
      }
      await postClientAction(`/mandates/${mandateType}/send`, {
        amount: part.amount,
        debitDay: client.bank.debitDay,
        startDate: mandateType === 'removal' ? drrStartDate : mediationStartDate,
        drrMonths: mandateType === 'removal' ? drrMonths : undefined,
        includesDrrFee: mandateType === 'removal',
        components: { ...part.components, startDate: mandateType === 'removal' ? drrStartDate : mediationStartDate, mandateKind: mandateType }
      });
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not send NuPay DebiCheck');
    }
  };

  const cancelSplitDebiCheck = async (mandateType: NuPayMandateKind) => {
    try {
      await postClientAction(`/mandates/${mandateType}/cancel`);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not cancel NuPay DebiCheck');
    }
  };

  const sendNupayMandate = async () => {
    if (hasDrrFeeCollection) await sendSplitDebiCheck('removal');
    if (hasMediationCollection) await sendSplitDebiCheck('mediation');
  };

  const cancelNupayMandate = async () => {
    if (hasDrrFeeCollection) await cancelSplitDebiCheck('removal');
    if (hasMediationCollection) await cancelSplitDebiCheck('mediation');
  };

  const resendNupayMandate = async () => {
    await sendNupayMandate();
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

  const updateAdminWorkflowStatus = async (overallStatus: string, activeService?: ServiceType) => {
    try {
      await postClientAction('/admin-workflow/status', { overallStatus, activeService: activeService || client.adminWorkflow?.activeService }, 'PATCH');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not update admin workflow');
    }
  };

  const updateAdminTask = async (task: AdminTask, status: string, notes = task.notes || '') => {
    try {
      await postClientAction('/admin-workflow/task', { taskId: task.id, status, notes }, 'PATCH');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not update admin task');
    }
  };

  const updateCreditorAction = async (action: AdminCreditorAction, field: 'status' | 'response' | 'notes' | 'proposedAmount', value: string | number) => {
    try {
      await postClientAction('/admin-workflow/creditor', { actionId: action.id, [field]: value }, 'PATCH');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not update creditor action');
    }
  };

  const updateFeeItem = async (fee: AdminFeeItem, field: 'status' | 'amount' | 'dueDate' | 'notes', value: string | number) => {
    try {
      await postClientAction('/admin-workflow/fees', { feeId: fee.id, [field]: value }, 'PATCH');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Could not update fee item');
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
      const response = await fetch(`${apiBase}/api/admin/clients`, { headers: { 'X-Tenant-ID': tenantId, 'X-User-ID': userId } });
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

  const documents = useMemo(() => requiredDocumentsFor(coach.service), [coach.service]);

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
      `Household Nett Income: ${currency(householdIncome)}`,
      `Living Expenses Budget: ${currency(totalLivingExpenses)}`,
      `Available after living expenses: ${currency(availableAfterLivingExpenses)}`,
      `DRR Fee: ${coach.service === 'Debt Review Removal' ? `${currency(drrFee)} over ${drrMonths} month(s) = ${currency(drrFee / drrMonths)} p/m` : 'Not applicable'}`,
      `Signature: ${client.signature?.status || 'Not Sent'}`,
      `NuPay DebiCheck Removal: ${client.nupayMandates?.removal?.status || 'Not Sent'} ${client.nupayMandates?.removal?.mandateId ? `(${client.nupayMandates.removal.mandateId})` : ''}`,
      `NuPay DebiCheck Mediation: ${client.nupayMandates?.mediation?.status || 'Not Sent'} ${client.nupayMandates?.mediation?.mandateId ? `(${client.nupayMandates.mediation.mandateId})` : ''}`,
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
    if (activeView === 'dashboard') loadDashboardMetrics();
    if (activeView === 'knowledge') loadProductKnowledge();
  }, [activeView, tenantId, clients.length]);

  const allNavItems: { key: ViewKey; label: string; helper: string }[] = [
    { key: 'dashboard', label: 'Dashboard', helper: 'Growth league' },
    { key: 'clients', label: 'Clients', helper: 'List and search' },
    { key: 'upload', label: 'Upload Report', helper: 'Parse and route sale' },
    { key: 'profile', label: 'Client Profile', helper: 'Single or joint application' },
    { key: 'budget', label: 'Living Budget', helper: 'Expenses and affordability' },
    { key: 'coach', label: 'Sales Coach', helper: 'Best next sale' },
    { key: 'accounts', label: 'Accounts', helper: 'Reduced amount table' },
    { key: 'mandate', label: 'Banking / NuPay', helper: 'Debit order ready' },
    { key: 'documents', label: 'Documents', helper: 'Links and uploaded docs' },
    { key: 'workflow', label: 'Submit Workflow', helper: 'Admin and PDA handover' },
    { key: 'admin', label: 'Admin Queue', helper: 'Docs, fees, PDA' },
    { key: 'knowledge', label: 'Product Knowledge', helper: 'Training + assessment' },
    { key: 'settings', label: 'Settings', helper: 'API and session' }
  ];
  const navItems = allNavItems.filter((item) => isAdminRole || item.key !== 'admin');

  const login = async () => {
    const selected = users.find((user) => user.id === userId) || users[0];
    if (!selected) {
      alert('Please select a tenant user first.');
      return;
    }
    const chosenUserId = selected.id;
    setUserId(chosenUserId);
    localStorage.setItem('fintastic_tenant_id', tenantId);
    localStorage.setItem('fintastic_user_id', chosenUserId);
    localStorage.setItem('fintastic_logged_in', '1');
    setLoggedIn(true);
    setClient(newLocalClient(tenantId, chosenUserId));
    await loadClients('', tenantId);
  };

  if (!loggedIn) {
    return (
      <div className="login-shell">
        <div className="login-card">
          <div className="brand-block login-brand"><div className="brand-mark">FT</div><div><strong>Fin-Tastic</strong><span>Sales Coach</span></div></div>
          {tenantLogoSrc(currentTenant) ? <div className="login-tenant-logo-wrap"><img src={tenantLogoSrc(currentTenant) || ''} alt={`${currentTenant?.name || 'Tenant'} logo`} className="login-tenant-logo" /></div> : null}
          <h1>Sign in to your tenant workspace</h1>
          <p>Choose the tenant and user once. The live workspace will not randomly switch roles or tenants.</p>
          <Field label="Backend API Base"><input value={apiBase} onChange={(event) => setApiBase(event.target.value)} /></Field>
          <Field label="Tenant"><select value={tenantId} onChange={(event) => setCurrentTenant(event.target.value)}>{tenants.length ? tenants.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>) : <option value={tenantId}>{tenantId}</option>}</select></Field>
          <Field label="User / Role"><select value={userId} onChange={(event) => setUserId(event.target.value)}>{users.length ? users.map((user) => <option key={user.id} value={user.id}>{user.name} · {user.role}</option>) : <option value={userId}>{userId}</option>}</select></Field>
          <div className="button-row"><button className="primary" onClick={login}>Enter Workspace</button><button className="secondary" onClick={saveApiBase}>Reload Tenants</button></div>
          <div className="panel-card tenant-rules"><strong>Isolation rule:</strong><p>Clients are loaded and saved only under the selected tenant. Users inside the same tenant share the same client database.</p></div>
        </div>
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
          {tenantLogoSrc(currentTenant) ? <img src={tenantLogoSrc(currentTenant) || ''} alt={`${currentTenant?.name || 'Tenant'} logo`} className="tenant-logo" /> : null}
          <small>Active tenant</small>
          <strong>{currentTenant?.name || tenantId}</strong>
          <span>{currentTenant?.ncr || ''}</span>
          <span>{currentUser ? `${currentUser.name} · ${currentUser.role}` : "Competition workspace"}</span>
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
            <p>{activeView === 'dashboard' ? 'Healthy competition dashboard: performance only, no client details.' : 'Every user sees only the clients inside their own tenant database.'}</p>
          </div>
          <div className="topbar-actions session-chip">
            {tenantLogoSrc(currentTenant) ? <img src={tenantLogoSrc(currentTenant) || ''} alt={`${currentTenant?.name || 'Tenant'} logo`} className="topbar-tenant-logo" /> : null}
            <span><strong>{currentTenant?.name || tenantId}</strong></span>
            <span>{currentUser ? `${currentUser.name} · ${currentUser.role}` : userId}</span>
            <button className="secondary" onClick={() => { localStorage.removeItem('fintastic_logged_in'); setLoggedIn(false); setActiveView('dashboard'); }}>Switch / Logout</button>
          </div>
        </header>

        {activeView !== 'dashboard' && (
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
        )}

        {activeView === 'dashboard' && (
          <section className="view-stack dashboard-clean competition-dashboard">
            <div className="dashboard-clean-hero competition-hero">
              <div>
                <Badge tone="blue">{currentUser?.role === 'Manager' ? 'Manager competition dashboard' : 'Consultant competition dashboard'}</Badge>
                <h2>🔥 Khusela Growth League</h2>
                <p>
                  A high-energy scoreboard for motivation, healthy competition and daily focus. No client names, IDs, phone numbers or case details appear here — only consultant rankings and commission-ready totals for this tenant.
                </p>
                <div className="vibe-chip-row"><span>⚡ Beat yesterday</span><span>🏆 Top 3 podium</span><span>📈 Grow DC value</span><span>✅ Docs win deals</span></div>
              </div>
              <div className="dashboard-action-panel">
                <button className="primary" onClick={() => setActiveView('upload')}>Upload New Lead</button>
                <button className="secondary" onClick={() => loadDashboardMetrics()}>Refresh League</button>
                {currentUser?.role === 'Manager' ? <button className="secondary" onClick={loadCommissionStats}>Store Commission Snapshot</button> : null}
              </div>
            </div>

            <div className="floor-heat-card panel-card">
              <div>
                <Badge tone="warn">Floor heat target</Badge>
                <h2>{dashboardSummary.heatEmoji || '🌡️'} {dashboardSummary.heatLabel || 'Cold Start'} Floor</h2>
                <p>Every R5,000 in combined DC value / DRR fee adds another heat block to the floor scoreboard.</p>
              </div>
              <HeatMeter value={dashboardSummary.dcValue || 0} label="Entire floor heat" />
            </div>

            <div className="stats-grid dashboard-kpis competition-kpis">
              <StatCard label="Floor Leads" value={String(dashboardSummary.leadsGenerated || 0)} sub="Uploaded credit reports" />
              <StatCard label="Floor DC Value" value={currency(dashboardSummary.dcValue || 0)} sub="Reduced payments + DRR fees" />
              <StatCard label="Teams" value={String(dashboardSummary.teams || teamLeaderboard.length || 0)} sub="Healthy team competition" />
              <StatCard label="Docs Received" value={String(dashboardSummary.documentsReceived || 0)} sub="Required docs uploaded" />
            </div>

            <div className="panel-card team-heat-board">
              <div className="section-heading compact-heading no-pad-heading">
                <div>
                  <h2>Team Heat Board</h2>
                  <p>Team totals keep the whole floor pushing together while each consultant still has an individual rank.</p>
                </div>
                <Badge tone="blue">R5,000 = +1 heat</Badge>
              </div>
              <div className="team-heat-grid">
                {teamLeaderboard.map((team) => (
                  <div key={team.team} className="team-heat-card">
                    <div className="team-heat-title"><span>#{team.rank}</span><strong>{team.team}</strong><em>{team.consultants} consultant(s)</em></div>
                    <HeatMeter value={team.dcValue || 0} label={team.heatLabel || 'Team heat'} />
                    <div className="team-mini-stats"><span>{team.leadsGenerated} leads</span><span>{currency(team.dcValue)} value</span><span>{team.documentsReceived} docs</span></div>
                  </div>
                ))}
                {!teamLeaderboard.length ? <div className="empty-state">No team activity yet.</div> : null}
              </div>
            </div>

            <div className="leader-podium competition-podium hype-podium">
              {consultantLeaderboard.slice(0, 3).map((row) => (
                <div key={row.userId} className={`podium-card rank-${row.rank}`}>
                  <span>{row.rank === 1 ? '👑' : `#${row.rank}`}</span>
                  <strong>{row.name}</strong>
                  <small>{row.leadsGenerated} lead(s) · {currency(row.dcValue)} DC value · {row.documentsReceived} docs</small>
                  <em>{row.rank === 1 ? 'League leader' : row.rank === 2 ? 'Chasing hard' : 'Podium spot'}</em>
                </div>
              ))}
              {!consultantLeaderboard.length ? <div className="empty-state">No activity yet. Upload reports to start the league.</div> : null}
            </div>

            <div className="motivation-strip">
              <div><strong>Daily mission</strong><span>Upload clean leads, get docs back fast, submit complete files.</span></div>
              <div><strong>Winning habit</strong><span>Use the Sales Coach talk track before every follow-up.</span></div>
              <div><strong>Momentum rule</strong><span>One more qualified lead or one more document can move the ranking.</span></div>
            </div>

            <div className="panel-card leaderboard-card clean-leaderboard-card competition-board">
              <div className="section-heading compact-heading">
                <div>
                  <h2>Leaderboard</h2>
                  <p>Ranked for growth, consistency and commission review. This table shows consultant performance only, never client details.</p>
                </div>
                <Badge tone="good">{dashboardSummary.consultants || consultantLeaderboard.length} consultant(s)</Badge>
              </div>
              <div className="leaderboard-table-wrap">
                <table className="leaderboard-table clean-leaderboard">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Consultant</th>
                      <th>Team</th>
                      <th>Leads</th>
                      <th>Reduced Payments</th>
                      <th>DRR Fees</th>
                      <th>DC Value</th>
                      <th>Docs Received</th>
                      <th>Handovers</th>
                      <th>Heat</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {consultantLeaderboard.map((row) => (
                      <tr key={row.userId}>
                        <td><span className="rank-pill">#{row.rank}</span></td>
                        <td><strong>{row.name}</strong><small>{row.role}</small></td>
                        <td><span className="team-pill">{row.team || 'Main Floor'}</span></td>
                        <td>{row.leadsGenerated}</td>
                        <td>{currency(row.reducedInstallments)}</td>
                        <td>{currency(row.removalFees)}</td>
                        <td><strong>{currency(row.dcValue)}</strong></td>
                        <td>{row.documentsReceived}{row.requiredDocuments ? <small> / {row.requiredDocuments}</small> : null}</td>
                        <td>{row.clientsSubmitted}</td>
                        <td><div className="mini-heat"><span>{row.heatEmoji || '🌡️'}</span><strong>{row.heatBlocks || 0}</strong></div></td>
                        <td><strong>{row.performanceScore}</strong></td>
                      </tr>
                    ))}
                    {!consultantLeaderboard.length ? <tr><td colSpan={11}>No consultant activity yet. Upload reports to start ranking consultants.</td></tr> : null}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="competition-info-grid">
              <div className="panel-card compact-panel">
                <h3>How consultants move up</h3>
                <ul className="clean-list">
                  <li>Upload qualified credit reports as new leads.</li>
                  <li>Build strong DC value through reduced instalments and applicable DRR fees.</li>
                  <li>Get required documents back from clients quickly.</li>
                  <li>Submit complete, clean files to admin.</li>
                </ul>
              </div>

              <div className="panel-card compact-panel">
                <h3>What managers review</h3>
                <ul className="clean-list">
                  <li>Lead volume and conversion readiness.</li>
                  <li>Total DC value for commission calculations.</li>
                  <li>Document collection discipline.</li>
                  <li>Admin handover completion rate.</li>
                </ul>
              </div>

              {currentUser?.role === 'Manager' && commissionSnapshot ? (
                <div className="panel-card compact-panel manager-snapshot">
                  <h3>Latest commission snapshot</h3>
                  <div className="info-list compact-info">
                    <div><span>Period</span><strong>{commissionSnapshot.period}</strong></div>
                    <div><span>Saved</span><strong>{commissionSnapshot.createdAt ? new Date(commissionSnapshot.createdAt).toLocaleString() : ''}</strong></div>
                    <div><span>DC value</span><strong>{currency(commissionSnapshot.summary?.dcValue || 0)}</strong></div>
                  </div>
                </div>
              ) : (
                <div className="panel-card compact-panel">
                  <h3>Product knowledge</h3>
                  <p className="muted-copy">Consultants can improve their ranking by staying sharp on Debt Review, Removal, Mediation and DebiCheck.</p>
                  <button className="secondary" onClick={() => setActiveView('knowledge')}>Open Product Knowledge</button>
                </div>
              )}
            </div>

            <div className="panel-card dashboard-rules-strip">
              <strong>Ranking formula:</strong>
              <span>Leads = uploaded reports.</span>
              <span>DC value = reduced instalments + applicable DRR fees.</span>
              <span>Docs = required documents received.</span>
              <span>Handovers = submitted to admin.</span>
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

        {activeView === 'budget' && (
          <section className="view-stack">
            <div className="panel-card">
              <div className="section-heading">
                <div>
                  <h2>Living expenses budget</h2>
                  <p>Capture the client’s monthly household living expenses before confirming affordability and reduced payments.</p>
                </div>
                <button className="primary" onClick={saveClient} disabled={saving}>{saving ? 'Saving...' : 'Save Budget'}</button>
              </div>
              <div className="stat-grid compact">
                <StatCard label="Household nett income" value={currency(householdIncome)} sub={client.applicationType === 'Joint' ? 'Client + spouse nett salary' : 'Client nett salary'} />
                <StatCard label="Living expenses" value={currency(totalLivingExpenses)} sub="Total captured monthly expenses" />
                <StatCard label="After living expenses" value={currency(availableAfterLivingExpenses)} sub="Before reduced debt proposal" />
                <StatCard label="After reduced payment" value={currency(availableAfterReducedPayment)} sub="After proposed reduced amount" />
              </div>
              <div className="form-grid">
                <Field label="Rent / Bond"><input value={budget.rentOrBond} onChange={(event) => updateBudget('rentOrBond', toNumber(event.target.value))} /></Field>
                <Field label="Groceries"><input value={budget.groceries} onChange={(event) => updateBudget('groceries', toNumber(event.target.value))} /></Field>
                <Field label="Electricity / Water"><input value={budget.electricityWater} onChange={(event) => updateBudget('electricityWater', toNumber(event.target.value))} /></Field>
                <Field label="Transport"><input value={budget.transport} onChange={(event) => updateBudget('transport', toNumber(event.target.value))} /></Field>
                <Field label="School Fees"><input value={budget.schoolFees} onChange={(event) => updateBudget('schoolFees', toNumber(event.target.value))} /></Field>
                <Field label="Insurance"><input value={budget.insurance} onChange={(event) => updateBudget('insurance', toNumber(event.target.value))} /></Field>
                <Field label="Medical"><input value={budget.medical} onChange={(event) => updateBudget('medical', toNumber(event.target.value))} /></Field>
                <Field label="Cellphone / Internet"><input value={budget.cellphoneInternet} onChange={(event) => updateBudget('cellphoneInternet', toNumber(event.target.value))} /></Field>
                <Field label="Clothing"><input value={budget.clothing} onChange={(event) => updateBudget('clothing', toNumber(event.target.value))} /></Field>
                <Field label="Maintenance"><input value={budget.maintenance} onChange={(event) => updateBudget('maintenance', toNumber(event.target.value))} /></Field>
                <Field label="Other Living Expenses"><input value={budget.otherLivingExpenses} onChange={(event) => updateBudget('otherLivingExpenses', toNumber(event.target.value))} /></Field>
                <Field label="Dependants"><input value={budget.dependants} onChange={(event) => updateBudget('dependants', toNumber(event.target.value))} /></Field>
              </div>
              <label className="field full-width"><span>Budget Notes</span><textarea value={budget.notes} onChange={(event) => updateBudget('notes', event.target.value)} placeholder="Capture rent proof notes, dependants, shared expenses or affordability concerns." /></label>
              {availableAfterReducedPayment < 0 ? <div className="alert danger">Warning: proposed reduced payment is higher than the available amount after living expenses. Adjust the reduced amount or review the budget.</div> : <div className="alert good">Budget leaves {currency(availableAfterReducedPayment)} after the proposed reduced payment.</div>}
            </div>
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
            <div className="three-column">
              <div className="panel-card"><h3>Why this route</h3><ul className="clean-list">{coach.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>
              <div className="panel-card"><h3>Budget pain points</h3><ul className="clean-list">{coach.painPoints.length ? coach.painPoints.map((item) => <li key={item}>{item}</li>) : <li>Capture income and living expenses to expose the pressure points.</li>}</ul></div>
              <div className="panel-card"><h3>Savings benefit</h3><ul className="clean-list">{coach.budgetBenefits.length ? coach.budgetBenefits.map((item) => <li key={item}>{item}</li>) : <li>Reduced-payment benefit appears after accounts and budget are captured.</li>}</ul></div>
            </div>
            <div className="three-column">
              <div className="panel-card"><h3>Conversation script</h3><ul className="clean-list">{coach.talkTrack.length ? coach.talkTrack.map((item) => <li key={item}>{item}</li>) : <li>Capture budget figures to generate a personalised script.</li>}</ul></div>
              <div className="panel-card"><h3>Objection help</h3><ul className="clean-list">{coach.objectionHandlers.length ? coach.objectionHandlers.map((item) => <li key={item}>{item}</li>) : <li>Capture more data to generate objection handling.</li>}</ul></div>
              <div className="panel-card"><h3>Tonality advice</h3><ul className="clean-list">{coach.tonalityTips.map((item) => <li key={item}>{item}</li>)}</ul></div>
            </div>
            <div className="panel-card"><h3>Next steps</h3><ol className="clean-list numbered">{coach.nextSteps.map((step) => <li key={step}>{step}</li>)}</ol></div>
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
              <div className="section-heading"><div><h2>NuPay DebiCheck control</h2><p>Send separate DebiChecks where applicable: one for the DRR removal fee and one for Debt Mediation reduced payments. Each can have its own start date.</p></div><Badge tone="blue">Separate mandates</Badge></div>
              <div className="split-mandate-grid">
                <div className={`split-mandate-card ${hasDrrFeeCollection ? '' : 'disabled-card'}`}>
                  <div className="split-mandate-title"><div><span className="mandate-icon">🏁</span><h3>Removal DebiCheck</h3><small>R7,000 Debt Review Removal fee only</small></div><Badge tone={removalDebiCheck.status === 'Pending Acceptance' ? 'warn' : removalDebiCheck.status === 'Cancelled' ? 'danger' : removalDebiCheck.status === 'Accepted' ? 'good' : 'neutral'}>{removalDebiCheck.status || 'Not Sent'}</Badge></div>
                  <div className="form-grid">
                    <Field label="Applicable"><input value={hasDrrFeeCollection ? 'Yes - DRR fee applies' : 'No - client is not routed to DRR'} readOnly /></Field>
                    <Field label="DRR fee split"><select value={drrMonths} onChange={(event) => setDrrMonths(Number(event.target.value))} disabled={!hasDrrFeeCollection}><option value={1}>1 month</option><option value={2}>2 months</option><option value={3}>3 months</option></select></Field>
                    <Field label="Debit order start date"><input type="date" value={drrStartDate} onChange={(event) => setDrrStartDate(event.target.value)} disabled={!hasDrrFeeCollection} /></Field>
                    <Field label="Debit day"><input value={client.bank.debitDay} onChange={(event) => updateBank('debitDay', event.target.value)} disabled={!hasDrrFeeCollection} /></Field>
                    <Field label="Monthly DRR fee debit"><input value={currency(splitDebiChecks.removal.amount)} readOnly /></Field>
                    <Field label="Mandate ID"><input value={removalDebiCheck.mandateId || ''} readOnly /></Field>
                  </div>
                  <div className="calculation-card compact-calc">
                    <span>Removal fee total: <strong>{currency(drrFee)}</strong></span>
                    <span>Collection period: <strong>{hasDrrFeeCollection ? `${drrMonths} month(s)` : 'Not applicable'}</strong></span>
                    <span>Start date: <strong>{drrStartDate || removalDebiCheck.startDate || 'Choose before sending if needed'}</strong></span>
                    {removalDebiCheck.link ? <span>Client link: <a href={removalDebiCheck.link} target="_blank" rel="noreferrer">Open Removal DebiCheck</a></span> : null}
                  </div>
                  <div className="button-row"><button className="primary" onClick={() => sendSplitDebiCheck('removal')} disabled={!hasDrrFeeCollection}>Send Removal DebiCheck</button><button className="secondary" onClick={() => cancelSplitDebiCheck('removal')} disabled={!hasDrrFeeCollection}>Cancel Removal</button></div>
                </div>

                <div className={`split-mandate-card ${hasMediationCollection ? '' : 'disabled-card'}`}>
                  <div className="split-mandate-title"><div><span className="mandate-icon">🤝</span><h3>Mediation DebiCheck</h3><small>Ongoing reduced payment only</small></div><Badge tone={mediationDebiCheck.status === 'Pending Acceptance' ? 'warn' : mediationDebiCheck.status === 'Cancelled' ? 'danger' : mediationDebiCheck.status === 'Accepted' ? 'good' : 'neutral'}>{mediationDebiCheck.status || 'Not Sent'}</Badge></div>
                  <div className="form-grid">
                    <Field label="Applicable"><input value={hasMediationCollection ? 'Yes - mediation/reduced payment applies' : 'No - no mediation payment for this client'} readOnly /></Field>
                    <Field label="Mediation frequency"><input value="Ongoing monthly DebiCheck" readOnly /></Field>
                    <Field label="Debit order start date"><input type="date" value={mediationStartDate} onChange={(event) => setMediationStartDate(event.target.value)} disabled={!hasMediationCollection} /></Field>
                    <Field label="Debit day"><input value={client.bank.debitDay} onChange={(event) => updateBank('debitDay', event.target.value)} disabled={!hasMediationCollection} /></Field>
                    <Field label="Monthly mediation debit"><input value={currency(splitDebiChecks.mediation.amount)} readOnly /></Field>
                    <Field label="Mandate ID"><input value={mediationDebiCheck.mandateId || ''} readOnly /></Field>
                  </div>
                  <div className="calculation-card compact-calc">
                    <span>Reduced creditor/payment proposal: <strong>{currency(splitDebiChecks.mediation.amount)} p/m</strong></span>
                    <span>Collection period: <strong>{hasMediationCollection ? 'Ongoing monthly' : 'Not applicable'}</strong></span>
                    <span>Start date: <strong>{mediationStartDate || mediationDebiCheck.startDate || 'Choose before sending if needed'}</strong></span>
                    {mediationDebiCheck.link ? <span>Client link: <a href={mediationDebiCheck.link} target="_blank" rel="noreferrer">Open Mediation DebiCheck</a></span> : null}
                  </div>
                  <div className="button-row"><button className="primary" onClick={() => sendSplitDebiCheck('mediation')} disabled={!hasMediationCollection}>Send Mediation DebiCheck</button><button className="secondary" onClick={() => cancelSplitDebiCheck('mediation')} disabled={!hasMediationCollection}>Cancel Mediation</button></div>
                </div>
              </div>
              <div className="panel-note debicheck-note"><strong>Why separate?</strong> DRR is a short service-fee collection. Mediation is an ongoing reduced-payment collection. Keeping them separate prevents the mediation instalment from being labelled as a DRR fee and allows separate start dates.</div>
              {((removalDebiCheck.history?.length || 0) + (mediationDebiCheck.history?.length || 0)) > 0 ? <div className="mandate-history-grid"><div><h4>Removal history</h4><ul className="clean-list mandate-history">{(removalDebiCheck.history || []).slice(-4).map((event, index) => <li key={`removal-${event.at}-${index}`}>{event.at ? new Date(event.at).toLocaleString() : ''} · {event.action}{event.amount ? ` · ${currency(event.amount)}` : ''}{event.startDate ? ` · starts ${event.startDate}` : ''}</li>)}</ul></div><div><h4>Mediation history</h4><ul className="clean-list mandate-history">{(mediationDebiCheck.history || []).slice(-4).map((event, index) => <li key={`mediation-${event.at}-${index}`}>{event.at ? new Date(event.at).toLocaleString() : ''} · {event.action}{event.amount ? ` · ${currency(event.amount)}` : ''}{event.startDate ? ` · starts ${event.startDate}` : ''}</li>)}</ul></div></div> : <p className="muted">No separate DebiCheck history yet.</p>}
            </div>
            <div className="panel-card">
              <div className="section-heading"><div><h2>Client portal link</h2><p>One simple link for required document uploads and drawn electronic signature.</p></div><button className="secondary" onClick={createPortalLinks}>Create Client Portal Link</button></div>
              <div className="link-grid">
                <div><span>Docs + Signature Link</span>{client.portalLinks?.clientPortalLink || client.documents?.uploadLink || client.signature?.link ? <a href={client.portalLinks?.clientPortalLink || client.documents?.uploadLink || client.signature?.link} target="_blank" rel="noreferrer">{client.portalLinks?.clientPortalLink || client.documents?.uploadLink || client.signature?.link}</a> : <small>Not created yet</small>}</div>
                <div><span>Client action</span><strong>Upload each required document and sign on-screen</strong><small>Client can clear and redraw signature before saving.</small></div>
              </div>
            </div>
          </section>
        )}

        {activeView === 'documents' && (
          <section className="view-stack">
            <div className="panel-card">
              <div className="section-heading">
                <div><h2>Client documents and signature</h2><p>Filtered by selected service route: {coach.service}. Send one simple client portal link before submitting to admin.</p></div>
                <div className="button-row"><button className="primary" onClick={requestDocuments}>Send Docs + Signature Link</button></div>
              </div>
              <div className="link-grid">
                <div><span>Client portal status</span><strong>{client.documents?.requestStatus || client.signature?.status || 'Not Sent'}</strong>{client.portalLinks?.clientPortalLink || client.documents?.uploadLink || client.signature?.link ? <a href={client.portalLinks?.clientPortalLink || client.documents?.uploadLink || client.signature?.link} target="_blank" rel="noreferrer">{client.portalLinks?.clientPortalLink || client.documents?.uploadLink || client.signature?.link}</a> : <small>No client portal link created yet</small>}</div>
                <div><span>Signature status</span><strong>{client.signature?.status || 'Not Sent'}</strong><small>Client signs on-screen, can clear errors, and saves when correct.</small></div>
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
                <StatCard label="Living Expenses" value={currency(totalLivingExpenses)} sub="Captured monthly budget" />
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
              <div className="section-heading">
                <div><h2>Admin service workflow</h2><p>Admin now follows the exact service sequence from handover to closure. For Debt Review, statutory processing starts only after signed Form 16 is confirmed.</p></div>
                <button className="secondary" onClick={loadAdminClients}>Refresh Admin Queue</button>
              </div>
              <div className="client-grid admin-grid">
                {(adminClients.length ? adminClients : clients).map((item) => {
                  const itemWorkflow = withWorkflowDefaults(item).adminWorkflow;
                  const done = (itemWorkflow?.tasks || []).filter((task) => ['Done', 'Completed'].includes(task.status)).length;
                  const total = itemWorkflow?.tasks?.length || 0;
                  return (
                    <button key={item.id} className={`client-card ${client.id === item.id ? 'selected' : ''}`} onClick={() => setClient(withWorkflowDefaults(item))}>
                      <div className="client-card-top"><strong>{item.fullName || 'Unnamed Client'}</strong><Badge tone={item.adminHandover?.status === 'Submitted' ? 'good' : 'neutral'}>{item.adminHandover?.status || 'Not Submitted'}</Badge></div>
                      <span>{(itemWorkflow?.services || [item.serviceType]).join(' + ')}</span>
                      <span>Workflow: {done}/{total} done</span>
                      <span>NuPay: {item.nupayMandate?.status || 'Not Sent'}</span>
                      <span>PDA: {item.pdaInfo?.status || 'Not Submitted'}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="panel-card admin-service-control">
              <div className="section-heading">
                <div>
                  <h3>{client.fullName || 'Selected client'} admin file</h3>
                  <p>Service/s: {(client.adminWorkflow?.services || [coach.service]).join(' + ')}</p>
                </div>
                <div className="button-row">
                  <select value={client.adminWorkflow?.overallStatus || 'Handover Received'} onChange={(event) => updateAdminWorkflowStatus(event.target.value)}>
                    <option>Handover Received</option><option>Intake Verification</option><option>Documents Complete</option><option>Form 16 Accepted</option><option>17.1 / COB Stage</option><option>Assessment / 17.2 Stage</option><option>Proposal / Legal Stage</option><option>PDA Setup</option><option>Active Monitoring</option><option>Clearance / Closure</option><option>Completed</option><option>On Hold</option><option>Blocked</option>
                  </select>
                  <button className="primary" onClick={saveClient}>Save Admin File</button>
                </div>
              </div>
              <div className="stats-grid compact">
                <StatCard label="Original Instalments" value={currency(coach.totals.originalInstalment)} sub="Before admin proposal" />
                <StatCard label="Reduced Proposal" value={currency(coach.totals.reducedInstalment)} sub="Editable per account" />
                <StatCard label="Included Creditors" value={String(accounts.filter((account) => account.included).length)} sub="To contact / submit" />
                <StatCard label="Living Expenses" value={currency(totalLivingExpenses)} sub="Captured monthly budget" />
                <StatCard label="Documents" value={`${(client.documents?.items || []).filter((doc) => doc.status === 'Uploaded').length}/${client.documents?.items?.length || 0}`} sub="Uploaded / required" />
              </div>
              {(client.adminWorkflow?.services || [coach.service]).includes('Debt Review Sales Coach') ? (
                <div className="compliance-strip">
                  <strong>Debt Review sequence controls</strong>
                  <span>Starts internally at consultant handover. Legal Debt Review starts at signed Form 16, then 17.1/COB, assessment/17.2, proposal, legal route, PDA, aftercare, Form 19 and bureau closure.</span>
                </div>
              ) : null}
              <div className="service-chip-row">
                {(client.adminWorkflow?.services || [coach.service]).map((service) => (
                  <button key={service} className={client.adminWorkflow?.activeService === service ? 'service-chip active' : 'service-chip'} onClick={() => updateAdminWorkflowStatus(client.adminWorkflow?.overallStatus || 'Handover Received', service)}>
                    {service}
                  </button>
                ))}
              </div>
            </div>

            <div className="panel-card tracker-board">
              <div className="section-heading">
                <div>
                  <h3>Admin tracker layout</h3>
                  <p>Based on the uploaded company tracker: sales handover, docs, DebiCheck/PDA, DHS/17.1/COB/17.2, proposal, acceptances, legal and closure.</p>
                </div>
                <Badge tone="blue">No spreadsheet duplication</Badge>
              </div>
              <div className="tracker-lanes">
                {trackerLaneSummary.map((lane) => (
                  <div className="tracker-lane" key={lane.title}>
                    <div className="tracker-lane-top">
                      <strong>{lane.title}</strong>
                      <Badge tone={lane.blocked ? 'warn' : lane.active ? 'blue' : 'good'}>{lane.done}/{lane.tasks.length || 0}</Badge>
                    </div>
                    <p>{lane.fields}</p>
                    <small>{lane.active} open · {lane.blocked} waiting/blocked</small>
                  </div>
                ))}
              </div>
            </div>

            <div className="two-column">
              <div className="panel-card">
                <h3>Service-specific admin checklist</h3>
                <div className="admin-task-list">
                  {(client.adminWorkflow?.tasks || [])
                    .filter((task) => !client.adminWorkflow?.activeService || task.service === client.adminWorkflow.activeService)
                    .slice()
                    .sort((a, b) => (a.sequence || 0) - (b.sequence || 0))
                    .map((task) => (
                    <div className="admin-task" key={task.id}>
                      <div>
                        <small>{task.stepCode || `Step ${task.sequence || ''}`} · {task.service} · {task.phase}</small>
                        <strong>{task.label}</strong>
                        <div className="task-meta">
                          {task.ncaMinimum ? <em>Minimum control</em> : null}
                          {task.dueBusinessDays ? <em>Due target: {task.dueBusinessDays} business days{task.dueFrom ? ` from ${task.dueFrom}` : ''}</em> : null}
                          {task.gate ? <em>Gate: {task.gate}</em> : null}
                          {task.outcome ? <em>Outcome: {task.outcome}</em> : null}
                          {task.regulationRef ? <em>{task.regulationRef}</em> : null}
                          {task.evidenceRequired ? <em>Evidence: {task.evidenceRequired}</em> : null}
                        </div>
                        {task.notes ? <span>{task.notes}</span> : null}
                      </div>
                      <select value={task.status} onChange={(event) => updateAdminTask(task, event.target.value)}>
                        <option>Not Started</option><option>In Progress</option><option>Waiting Client</option><option>Waiting Creditor</option><option>Submitted</option><option>Done</option><option>Blocked</option><option>Not Applicable</option>
                      </select>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel-card">
                <h3>Documents, signature, NuPay and PDA controls</h3>
                <div className="info-list">
                  <div><span>Signature</span><strong>{client.signature?.status || 'Not Sent'}</strong></div>
                  <div><span>NuPay DebiCheck</span><strong>{client.nupayMandate?.status || 'Not Sent'} {client.nupayMandate?.mandateId ? `· ${client.nupayMandate.mandateId}` : ''}</strong></div>
                  <div><span>PDA status</span><strong>{client.pdaInfo?.status || 'Not Submitted'} {client.pdaInfo?.pdaReference ? `· ${client.pdaInfo.pdaReference}` : ''}</strong></div>
                  <div><span>Living expenses budget</span><strong>{currency(totalLivingExpenses)}</strong></div>
                  <div><span>Available after reduced payment</span><strong>{currency(availableAfterReducedPayment)}</strong></div>
                  <div><span>DRR fee</span><strong>{(client.adminWorkflow?.services || []).includes('Debt Review Removal') ? currency(drrFee) : 'N/A'}</strong></div>
                </div>
                <div className="button-row"><button className="secondary" onClick={cancelNupayMandate}>Cancel Mandate</button><button className="primary" onClick={resendNupayMandate}>Send New Mandate</button><button className="secondary" onClick={requestDocuments}>Send Docs + Signature Link</button></div>
                <div className="mini-doc-list">
                  {(client.documents?.items || []).map((doc) => <div key={doc.name}><span>{doc.name}</span><Badge tone={doc.status === 'Uploaded' ? 'good' : doc.status === 'Requested' ? 'warn' : 'neutral'}>{doc.status}</Badge></div>)}
                </div>
              </div>
            </div>

            <div className="panel-card">
              <div className="section-heading"><div><h3>Creditor action tracker</h3><p>Admin can track every included creditor through proposal, response, counter-offer and acceptance.</p></div></div>
              <div className="table-wrap slim"><table className="accounts-table"><thead><tr><th>Creditor</th><th>Account</th><th>Service</th><th>Current</th><th>Original</th><th>Proposal</th><th>Status</th><th>Response / Notes</th></tr></thead><tbody>
                {(client.adminWorkflow?.creditorActions || []).map((action) => (
                  <tr key={action.id}>
                    <td>{action.creditorName}</td><td>{action.accountNumber}</td><td>{action.service}</td><td>{currency(action.currentBalance)}</td><td>{currency(action.originalInstallment)}</td>
                    <td><input value={action.proposedAmount} onChange={(event) => updateCreditorAction(action, 'proposedAmount', toNumber(event.target.value))} /></td>
                    <td><select value={action.status} onChange={(event) => updateCreditorAction(action, 'status', event.target.value)}><option>Not Contacted</option><option>Proposal Sent</option><option>Accepted</option><option>Rejected</option><option>Counter Offer</option><option>Escalated</option><option>Completed</option></select></td>
                    <td><input value={action.notes || action.response || ''} onChange={(event) => updateCreditorAction(action, 'notes', event.target.value)} /></td>
                  </tr>
                ))}
              </tbody></table></div>
            </div>

            <div className="two-column">
              <div className="panel-card">
                <h3>Fees and payment controls</h3>
                <div className="fee-ledger">
                  {(client.adminWorkflow?.feeItems || []).map((fee) => (
                    <div className="fee-line" key={fee.id}>
                      <div><strong>{fee.label}</strong><small>{fee.service}</small></div>
                      <input value={fee.amount} onChange={(event) => updateFeeItem(fee, 'amount', toNumber(event.target.value))} />
                      <select value={fee.status} onChange={(event) => updateFeeItem(fee, 'status', event.target.value)}><option>Not Invoiced</option><option>Invoiced</option><option>Partially Paid</option><option>Paid</option><option>Pending Acceptance</option><option>Cancelled</option></select>
                    </div>
                  ))}
                </div>
              </div>
              <div className="panel-card">
                <h3>PDA information</h3>
                <div className="form-grid single">
                  <Field label="PDA Name"><input value={client.pdaInfo?.pdaName || ''} onChange={(event) => updatePdaField('pdaName', event.target.value)} /></Field>
                  <Field label="PDA Reference"><input value={client.pdaInfo?.pdaReference || ''} onChange={(event) => updatePdaField('pdaReference', event.target.value)} /></Field>
                  <Field label="Proposal Amount"><input value={client.pdaInfo?.proposalAmount || coach.totals.reducedInstalment} onChange={(event) => updatePdaField('proposalAmount', toNumber(event.target.value))} /></Field>
                  <Field label="Payment Start Date"><input type="date" value={client.pdaInfo?.paymentStartDate || ''} onChange={(event) => updatePdaField('paymentStartDate', event.target.value)} /></Field>
                  <Field label="PDA Status"><select value={client.pdaInfo?.status || 'Not Submitted'} onChange={(event) => updatePdaField('status', event.target.value)}><option>Not Submitted</option><option>Ready for PDA</option><option>Submitted to PDA</option><option>PDA Active</option><option>PDA Query</option><option>Cancelled</option></select></Field>
                </div>
                <div className="button-row"><button className="primary" onClick={savePdaInfo}>Save PDA Info</button></div>
              </div>
            </div>
          </section>
        ))}

        {activeView === 'knowledge' && (
          <section className="view-stack">
            <div className="dashboard-hero knowledge-hero">
              <div>
                <Badge tone="blue">Product knowledge academy</Badge>
                <h2>Services training and consultant assessment</h2>
                <p>Use this tab to train consultants on Debt Review, Debt Review Removal, Debt Mediation, NuPay DebiCheck and admin handover rules. Assessment scores are stored per tenant and ranked for manager review.</p>
                <div className="button-row">
                  <button className="primary" onClick={loadProductKnowledge}>Refresh Training</button>
                  <button className="secondary" onClick={submitKnowledgeAssessment}>Submit Assessment</button>
                </div>
              </div>
              <div className="panel-card compact-panel">
                <h3>Your latest result</h3>
                <div className="info-list">
                  <div><span>Score</span><strong>{assessmentResult ? `${assessmentResult.scorePercent}%` : 'Not assessed'}</strong></div>
                  <div><span>Level</span><strong>{assessmentResult?.level || 'Complete the quiz'}</strong></div>
                  <div><span>Correct</span><strong>{assessmentResult ? `${assessmentResult.correct}/${assessmentResult.total}` : '0/0'}</strong></div>
                </div>
              </div>
            </div>

            <div className="knowledge-grid">
              {knowledgeModules.map((module) => (
                <div className="panel-card knowledge-card" key={module.id}>
                  <Badge tone={module.service === 'Debt Review Removal' ? 'danger' : module.service === 'Debt Mediation' ? 'blue' : 'warn'}>{module.service}</Badge>
                  <h3>{module.title}</h3>
                  <p>{module.summary}</p>
                  <h4>Product knowledge</h4>
                  <ul className="clean-list">{module.keyPoints.map((point) => <li key={point}>{point}</li>)}</ul>
                  <h4>Sales positioning</h4>
                  <ul className="clean-list">{module.salesAngles.map((point) => <li key={point}>{point}</li>)}</ul>
                </div>
              ))}
              {!knowledgeModules.length ? <div className="empty-state">Training content is loading. Click Refresh Training if it does not appear.</div> : null}
            </div>

            <div className="two-column">
              <div className="panel-card">
                <div className="section-heading"><div><h2>Assessment quiz</h2><p>Consultants are ranked by their latest assessment result. This covers all services offered.</p></div><Badge tone="neutral">Pass mark 80%</Badge></div>
                <div className="question-list">
                  {knowledgeQuestions.map((question, index) => (
                    <div className="question-card" key={question.id}>
                      <small>Question {index + 1} · {question.service}</small>
                      <strong>{question.question}</strong>
                      <div className="answer-options">
                        {question.options.map((option, optionIndex) => (
                          <label key={`${question.id}-${optionIndex}`} className="checkline">
                            <input type="radio" name={question.id} checked={assessmentAnswers[question.id] === optionIndex} onChange={() => setAssessmentAnswers((current) => ({ ...current, [question.id]: optionIndex }))} />
                            {option}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="button-row"><button className="primary" onClick={submitKnowledgeAssessment}>Submit Assessment</button><button className="secondary" onClick={() => setAssessmentAnswers({})}>Clear Answers</button></div>
              </div>

              <div className="panel-card">
                <div className="section-heading"><div><h2>Knowledge leaderboard</h2><p>Manager can use this ranking to identify strong consultants and consultants needing coaching.</p></div></div>
                <div className="leaderboard-table-wrap compact-leaderboard">
                  <table className="leaderboard-table">
                    <thead><tr><th>Rank</th><th>Consultant</th><th>Score</th><th>Level</th><th>Attempts</th></tr></thead>
                    <tbody>
                      {knowledgeLeaderboard.map((row) => (
                        <tr key={row.userId}>
                          <td><span className="rank-pill">#{row.rank}</span></td>
                          <td><strong>{row.name}</strong><small>{row.email}</small></td>
                          <td><strong>{row.scorePercent}%</strong><small>{row.correct}/{row.total}</small></td>
                          <td><Badge tone={row.passed ? 'good' : row.scorePercent ? 'warn' : 'neutral'}>{row.level}</Badge></td>
                          <td>{row.attempts}</td>
                        </tr>
                      ))}
                      {!knowledgeLeaderboard.length ? <tr><td colSpan={5}>No assessment results yet.</td></tr> : null}
                    </tbody>
                  </table>
                </div>
                {assessmentResult?.review?.length ? <div className="assessment-review"><h3>Latest review</h3><ul className="clean-list">{assessmentResult.review.map((item) => <li key={item.id}>{item.correct ? '✅' : '❌'} {item.question}</li>)}</ul></div> : null}
              </div>
            </div>
          </section>
        )}

        {activeView === 'settings' && (
          <section className="view-stack">
            <div className="panel-card">
              <h2>Tenant and API settings</h2>
              <div className="form-grid">
                <Field label="Backend API Base"><input value={apiBase} onChange={(event) => setApiBase(event.target.value)} /></Field>
                <Field label="Current Tenant"><input value={currentTenant?.name || tenantId} readOnly /></Field>
                <Field label="NCR Registration"><input value={currentTenant?.ncr || ''} readOnly /></Field>
                <Field label="Tenant Contact"><input value={currentTenant?.email || currentTenant?.phone || ''} readOnly /></Field>
                <Field label="Current User / Role"><input value={currentUser ? `${currentUser.name} · ${currentUser.role}` : userId} readOnly /></Field>
              </div>
              <div className="button-row settings-buttons"><button className="primary" onClick={saveApiBase}>Save API and Reload</button><button className="secondary" onClick={() => loadClients()}>Reload Client List</button><button className="secondary" onClick={() => { localStorage.removeItem('fintastic_logged_in'); setLoggedIn(false); }}>Switch Tenant/User</button></div>
              <div className="panel-card tenant-rules"><h3>Isolation rules built in</h3><ul className="clean-list"><li>Client list calls use <code>GET /api/clients</code> with <code>X-Tenant-ID</code>.</li><li>Uploads use the same header and save files under <code>backend/uploads/&lt;tenant_id&gt;</code>.</li><li>Backend rejects client reads/updates when the client is not inside the active tenant.</li><li>Users in the same tenant share the same clients because they query the same tenant database.</li></ul></div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
