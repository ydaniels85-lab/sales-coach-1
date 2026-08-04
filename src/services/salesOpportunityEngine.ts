export type SalesPriority = "High" | "Medium" | "Low";

export type SalesOpportunity = {
  recommendedService: string;
  priority: SalesPriority;
  confidence: number;
  salesAngle: string;
  painPoints: string[];
  accountsToMention: string[];
  prescribedDebtCandidates: string[];
  furnitureAccounts: string[];
  consultantOpening: string;
  pitchScript: string;
  questionsToAsk: string[];
  objectionHandlers: {
    objection: string;
    response: string;
  }[];
  nextBestActions: string[];
  complianceNote: string;
};

function money(value: any): number {
  if (value === undefined || value === null || value === "") return 0;

  if (typeof value === "number") {
    return Number.isFinite(value) ? value : 0;
  }

  const cleaned = String(value)
    .replace(/R/gi, "")
    .replace(/,/g, "")
    .replace(/\s/g, "")
    .replace(/[^\d.-]/g, "")
    .trim();

  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : 0;
}

function safeText(value: any): string {
  if (value === undefined || value === null) return "";
  return String(value).trim();
}

function lower(value: any): string {
  return safeText(value).toLowerCase();
}

function formatMoney(value: number): string {
  return `R${Math.round(value).toLocaleString("en-ZA")}`;
}

function getAccounts(parsedReport: any): any[] {
  const possible =
    parsedReport?.creditors ||
    parsedReport?.accounts ||
    parsedReport?.creditAccounts ||
    parsedReport?.credit_accounts ||
    parsedReport?.data?.creditors ||
    parsedReport?.data?.accounts ||
    parsedReport?.result?.creditors ||
    parsedReport?.result?.accounts ||
    [];

  return Array.isArray(possible) ? possible : [];
}

function getScore(parsedReport: any): number {
  const raw =
    parsedReport?.score ??
    parsedReport?.creditScore ??
    parsedReport?.credit_score ??
    parsedReport?.client?.score ??
    parsedReport?.client?.creditScore ??
    parsedReport?.data?.score ??
    parsedReport?.result?.score ??
    0;

  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
}

function getRawText(parsedReport: any): string {
  return lower(
    parsedReport?.rawText ||
      parsedReport?.text ||
      parsedReport?.fullText ||
      parsedReport?.extractedText ||
      parsedReport?.summary ||
      JSON.stringify(parsedReport || {})
  );
}

function isDebtReviewListed(parsedReport: any): boolean {
  const reportText = getRawText(parsedReport);

  return (
    reportText.includes("debt review listed") ||
    reportText.includes("debt review listed against consumer") ||
    reportText.includes("under debt review") ||
    reportText.includes("consumer is under debt review") ||
    reportText.includes("debt counselling") ||
    reportText.includes("debt counseling") ||
    reportText.includes("debt counsellor") ||
    reportText.includes("debt counselor") ||
    reportText.includes("form 17.2") ||
    reportText.includes("ncrdc")
  );
}

function getCreditorName(account: any): string {
  return safeText(
    account?.creditorName ||
      account?.creditor_name ||
      account?.name ||
      account?.creditor ||
      account?.subscriberName ||
      account?.supplierName ||
      "Unknown creditor"
  );
}

function getAccountType(account: any): string {
  return safeText(
    account?.accountType ||
      account?.account_type ||
      account?.type ||
      account?.loanType ||
      account?.category
  );
}

function getCurrentBalance(account: any): number {
  return money(
    account?.currentBalance ??
      account?.current_balance ??
      account?.balance ??
      account?.outstandingBalance ??
      account?.outstanding_balance
  );
}

function getOpeningBalance(account: any): number {
  return money(
    account?.openingBalance ??
      account?.opening_balance ??
      account?.originalBalance ??
      account?.original_balance
  );
}

function getArrears(account: any): number {
  return money(
    account?.arrears ??
      account?.arrearsAmount ??
      account?.arrears_amount ??
      account?.amountInArrears ??
      account?.amount_in_arrears
  );
}

function getMonthlyInstallment(account: any): number {
  return money(
    account?.monthlyInstallment ??
      account?.monthlyInstalment ??
      account?.monthly_installment ??
      account?.monthly_instalment ??
      account?.installment ??
      account?.instalment
  );
}

function getLastPaidDate(account: any): any {
  return (
    account?.lastPaidDate ||
    account?.lastPaymentDate ||
    account?.last_paid_date ||
    account?.last_payment_date ||
    account?.lastPayment ||
    account?.last_payment
  );
}

function isFurnitureAccount(account: any): boolean {
  const name = lower(getCreditorName(account));
  const type = lower(getAccountType(account));

  return (
    name.includes("lewis") ||
    name.includes("russells") ||
    name.includes("bradlows") ||
    name.includes("ok furniture") ||
    name.includes("fair price") ||
    name.includes("beares") ||
    name.includes("house & home") ||
    name.includes("furniture") ||
    type.includes("furniture")
  );
}

function monthsSince(dateValue: any): number | null {
  if (!dateValue) return null;

  const raw = String(dateValue).trim();
  let date: Date | null = null;

  if (/^\d{4}[-/]\d{1,2}[-/]\d{1,2}$/.test(raw)) {
    date = new Date(raw.replace(/\//g, "-"));
  } else if (/^\d{1,2}[-/]\d{1,2}[-/]\d{4}$/.test(raw)) {
    const [d, m, y] = raw.split(/[-/]/);
    date = new Date(`${y}-${m}-${d}`);
  } else if (/^\d{4}[-/]\d{1,2}$/.test(raw)) {
    date = new Date(`${raw.replace(/\//g, "-")}-01`);
  }

  if (!date || Number.isNaN(date.getTime())) return null;

  const now = new Date();

  return (
    (now.getFullYear() - date.getFullYear()) * 12 +
    now.getMonth() -
    date.getMonth()
  );
}

function uniqueList(items: string[]): string[] {
  return Array.from(new Set(items.filter(Boolean)));
}

export function buildSalesOpportunity(parsedReport: any): SalesOpportunity {
  const accounts = getAccounts(parsedReport);
  const score = getScore(parsedReport);
  const debtReviewListed = isDebtReviewListed(parsedReport);

  const totalBalance = accounts.reduce((sum, account) => sum + getCurrentBalance(account), 0);
  const totalOpeningBalance = accounts.reduce((sum, account) => sum + getOpeningBalance(account), 0);
  const totalArrears = accounts.reduce((sum, account) => sum + getArrears(account), 0);
  const totalInstallments = accounts.reduce((sum, account) => sum + getMonthlyInstallment(account), 0);

  const accountsWithArrears = accounts.filter((account) => getArrears(account) > 0);

  const furnitureAccounts = uniqueList(
    accounts.filter(isFurnitureAccount).map((account) => getCreditorName(account))
  );

  const prescribedDebtCandidates = uniqueList(
    accounts
      .filter((account) => {
        const months = monthsSince(getLastPaidDate(account));
        return months !== null && months >= 36 && getCurrentBalance(account) > 0;
      })
      .map((account) => getCreditorName(account))
  );

  const painPoints: string[] = [];

  if (debtReviewListed) painPoints.push("Debt Review listing detected");
  if (score === 0) painPoints.push("Credit score is 0, possible Debt Review listing or severe credit restriction");
  if (score > 0 && score < 550) painPoints.push(`Low credit score detected: ${score}`);
  if (accounts.length > 0) painPoints.push(`${accounts.length} credit account(s) found`);
  if (totalOpeningBalance > 0) painPoints.push(`Opening balances total: ${formatMoney(totalOpeningBalance)}`);
  if (totalBalance > 0) painPoints.push(`Current balances total: ${formatMoney(totalBalance)}`);
  if (totalArrears > 0) painPoints.push(`Arrears detected: ${formatMoney(totalArrears)}`);
  if (accountsWithArrears.length > 0) painPoints.push(`${accountsWithArrears.length} account(s) appear to be in arrears`);
  if (totalInstallments > 0) painPoints.push(`Monthly instalments total: ${formatMoney(totalInstallments)}`);
  if (furnitureAccounts.length > 0) painPoints.push("Furniture account(s) detected");
  if (prescribedDebtCandidates.length > 0) painPoints.push("Possible prescribed debt candidate(s) detected");

  let recommendedService = "Debt Mediation";
  let priority: SalesPriority = "Medium";
  let confidence = 70;
  let salesAngle = "";

  if (debtReviewListed || score === 0) {
    if (totalBalance > 0) {
      recommendedService = "Debt Review Removal + Debt Mediation";
      priority = "High";
      confidence = 92;
      salesAngle =
        "The report indicates a possible Debt Review restriction or zero score, but there are still outstanding balances. First sell the removal assessment, then position mediation for the remaining balances.";
    } else {
      recommendedService = "Debt Review Removal";
      priority = "High";
      confidence = 90;
      salesAngle =
        "The report indicates a possible Debt Review restriction or zero score. Focus on checking whether the client can be removed from Debt Review and restored to a better credit position.";
    }
  } else if (prescribedDebtCandidates.length > 0) {
    recommendedService = "Prescribed Debt Investigation + Debt Mediation";
    priority = "High";
    confidence = 86;
    salesAngle =
      "The report shows old accounts that may need prescribed debt investigation. Use this as the hook, then offer mediation on active accounts that still need negotiation.";
  } else if (totalArrears > 0 && accounts.length >= 4) {
    recommendedService = "Debt Mediation";
    priority = "High";
    confidence = 82;
    salesAngle =
      "The client has arrears and multiple creditors. Focus on reducing pressure, negotiating with creditors, and creating one affordable repayment plan.";
  } else if (totalBalance > 0) {
    recommendedService = "Debt Mediation";
    priority = "Medium";
    confidence = 72;
    salesAngle =
      "The client has active outstanding debt. Focus on affordability, creditor negotiation, and preventing the credit profile from getting worse.";
  } else {
    recommendedService = "Credit Profile Assessment";
    priority = "Low";
    confidence = 55;
    salesAngle =
      "No major debt opportunity was detected. Offer a credit profile assessment and check whether the client needs dispute, removal, or affordability assistance.";
  }

  const accountsToMention = accounts
    .slice()
    .sort((a, b) => getCurrentBalance(b) - getCurrentBalance(a))
    .slice(0, 5)
    .map((account) => {
      const name = getCreditorName(account);
      const balance = getCurrentBalance(account);
      const arrears = getArrears(account);
      const installment = getMonthlyInstallment(account);

      const parts = [`${name}`];
      if (balance > 0) parts.push(`balance ${formatMoney(balance)}`);
      if (arrears > 0) parts.push(`arrears ${formatMoney(arrears)}`);
      if (installment > 0) parts.push(`instalment ${formatMoney(installment)}`);

      return parts.join(" — ");
    });

  return {
    recommendedService,
    priority,
    confidence,
    salesAngle,
    painPoints,
    accountsToMention,
    prescribedDebtCandidates,
    furnitureAccounts,
    consultantOpening:
      "I have reviewed your credit report and I can already see where the pressure is coming from. The good news is that there is a clear action plan we can follow.",
    pitchScript:
      `Based on your credit report, the best option to look at is ${recommendedService}. ` +
      `${salesAngle} ` +
      "The aim is not only to look at the debt, but to identify which accounts are damaging your profile, which accounts can be negotiated, and what documents we need to start the correct process.",
    questionsToAsk: [
      "Are you currently under Debt Review, or were you previously under Debt Review?",
      "Are you still paying any of these accounts every month?",
      "When last did you make payment on the oldest accounts?",
      "Which creditor is putting the most pressure on you right now?",
      "Can you afford one reduced repayment arrangement if we negotiate with creditors?",
      "Do you want me to send the document upload link now so we can start your assessment?"
    ],
    objectionHandlers: [
      {
        objection: "I don’t have money right now.",
        response:
          "I understand. That is exactly why we need to look at this properly. The first step is to see which accounts are causing the biggest damage and which option gives you the most relief."
      },
      {
        objection: "I need to think about it.",
        response:
          "That is fine. Before you decide, let me send you the document link so we can confirm exactly what you qualify for. Then you can make a decision based on the facts, not pressure."
      },
      {
        objection: "I am already under Debt Review.",
        response:
          "That is important. Then we need to check whether the Debt Review is still active, whether there is a court order, and whether removal or restructuring is possible."
      },
      {
        objection: "I do not know who I owe.",
        response:
          "That is exactly why the credit report helps. We can see the creditors, balances, arrears, and which accounts need attention first."
      },
      {
        objection: "I cannot afford another debit order.",
        response:
          "That is why we first calculate affordability. We do not want to add pressure. We want to find the most realistic option based on your income, expenses, and creditors."
      }
    ],
    nextBestActions: [
      "Confirm client full names, ID number, cellphone, WhatsApp number, and email address",
      "Confirm whether the client wants a single or joint application",
      "Send the client document upload link",
      "Send the client signature link",
      "Request ID copy, payslip, bank statement, and proof of address",
      "Mark accounts to include or exclude",
      "Generate the correct workflow documents for the recommended service",
      "Log the sales discussion under the client profile"
    ],
    complianceNote:
      "Do not promise guaranteed removal, write-off, settlement, approval, or credit score improvement. Explain that the final recommendation depends on verified documents, creditor responses, NCA requirements, prescription rules, and the client’s affordability."
  };
}
