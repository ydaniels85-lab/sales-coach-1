export type SalesPriority = "High" | "Medium" | "Low";

export type SalesOpportunity = {
  recommendedService: string;
  priority: SalesPriority;
  confidence: number;
  salesAngle: string;
  painPoints: string[];
  accountsToMention: string[];
  questionsToAsk: string[];
  nextBestActions: string[];
  complianceNote: string;
};

function money(value: any): number {
  if (value === undefined || value === null || value === "") return 0;
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  const cleaned = String(value).replace(/R/gi, "").replace(/,/g, "").replace(/\s/g, "").replace(/[^\d.-]/g, "").trim();
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : 0;
}
function accounts(report: any): any[] { const list = report?.accounts || report?.creditors || report?.creditAccounts || report?.credit_accounts || report?.client?.accounts || report?.data?.accounts || []; return Array.isArray(list) ? list : []; }
function score(report: any): number { const n = Number(report?.score ?? report?.creditScore ?? report?.credit_score ?? report?.client?.score ?? 0); return Number.isFinite(n) ? n : 0; }
function raw(report: any): string { return String(report?.rawText || report?.text || report?.fullText || report?.raw_text || JSON.stringify(report || {})).toLowerCase(); }
function creditorName(a: any): string { return String(a?.creditor || a?.creditorName || a?.creditor_name || a?.name || "Unknown creditor"); }
function balance(a: any): number { return money(a?.current_balance ?? a?.currentBalance ?? a?.balance ?? a?.outstandingBalance); }
function arrears(a: any): number { return money(a?.arrears ?? a?.arrearsAmount ?? a?.arrears_amount); }
function instalment(a: any): number { return money(a?.monthly_instalment ?? a?.monthlyInstallment ?? a?.monthlyInstalment ?? a?.installment ?? a?.instalment); }
function zar(n: number): string { return `R${Math.round(n).toLocaleString("en-ZA")}`; }

export function buildSalesOpportunity(report: any): SalesOpportunity {
  const list = accounts(report);
  const totalBalance = list.reduce((s, a) => s + balance(a), 0);
  const totalArrears = list.reduce((s, a) => s + arrears(a), 0);
  const totalInstalments = list.reduce((s, a) => s + instalment(a), 0);
  const dr = raw(report).includes("debt review") || raw(report).includes("under debt review") || score(report) === 0;

  let recommendedService = "Debt Mediation";
  let priority: SalesPriority = "Medium";
  let confidence = 72;
  let salesAngle = "The client has outstanding debt. Focus on affordability, creditor negotiation, and preventing the credit profile from getting worse.";

  if (dr && totalBalance > 0) {
    recommendedService = "Debt Review Removal + Debt Mediation"; priority = "High"; confidence = 92;
    salesAngle = "The report indicates Debt Review or a zero score with remaining balances. Sell the removal assessment first, then position mediation for the outstanding balances.";
  } else if (dr) {
    recommendedService = "Debt Review Removal"; priority = "High"; confidence = 90;
    salesAngle = "The report indicates Debt Review or a zero score. Focus on checking whether removal is possible and what documents are needed.";
  } else if (totalArrears > 0 && list.length >= 4) {
    priority = "High"; confidence = 84;
    salesAngle = "The client has arrears and multiple creditors. Focus on reducing pressure and creating one affordable repayment plan.";
  }

  const painPoints: string[] = [];
  if (dr) painPoints.push("Debt Review / zero score warning detected");
  if (list.length) painPoints.push(`${list.length} credit account(s) found`);
  if (totalBalance) painPoints.push(`Current balances total: ${zar(totalBalance)}`);
  if (totalArrears) painPoints.push(`Arrears detected: ${zar(totalArrears)}`);
  if (totalInstalments) painPoints.push(`Monthly instalments total: ${zar(totalInstalments)}`);

  return {
    recommendedService, priority, confidence, salesAngle, painPoints,
    accountsToMention: list.slice().sort((a,b) => balance(b) - balance(a)).slice(0,5).map(a => `${creditorName(a)} — balance ${zar(balance(a))}${arrears(a) ? `, arrears ${zar(arrears(a))}` : ""}`),
    questionsToAsk: ["Are you currently under Debt Review, or were you previously under Debt Review?", "Are you still paying any of these accounts every month?", "Which creditor is putting the most pressure on you right now?", "Can you afford one reduced repayment arrangement if we negotiate with creditors?", "Do you want me to send the document upload link now so we can start your assessment?"],
    nextBestActions: ["Confirm client contact details", "Confirm single or joint application", "Send document upload link", "Send signature link", "Request ID, payslip, bank statement, and proof of address", "Generate the correct workflow documents"],
    complianceNote: "Do not promise guaranteed removal, write-off, settlement, approval, or credit score improvement. Final recommendation depends on verified documents, creditor responses, NCA requirements, and affordability."
  };
}
