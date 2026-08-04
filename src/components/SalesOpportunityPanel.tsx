import React, { useState } from "react";
import { buildSalesOpportunity } from "../services/salesOpportunityEngine";

type Props = {
  parsedReport: any;
};

export default function SalesOpportunityPanel({ parsedReport }: Props) {
  const [copied, setCopied] = useState(false);

  if (!parsedReport) return null;

  const opportunity = buildSalesOpportunity(parsedReport);

  const priorityClass =
    opportunity.priority === "High"
      ? "badge-error"
      : opportunity.priority === "Medium"
      ? "badge-warning"
      : "badge-success";

  const copySalesScript = async () => {
    const textToCopy = `
SALES OPPORTUNITY

Best Service:
${opportunity.recommendedService}

Main Sales Angle:
${opportunity.salesAngle}

Opening:
${opportunity.consultantOpening}

Pitch:
${opportunity.pitchScript}

Pain Points:
${opportunity.painPoints.map((item) => `- ${item}`).join("\n")}

Accounts to Mention:
${opportunity.accountsToMention.map((item) => `- ${item}`).join("\n")}

Questions:
${opportunity.questionsToAsk.map((item, index) => `${index + 1}. ${item}`).join("\n")}

Next Best Actions:
${opportunity.nextBestActions.map((item, index) => `${index + 1}. ${item}`).join("\n")}

Compliance:
${opportunity.complianceNote}
    `.trim();

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      alert("Could not copy. Please copy manually.");
    }
  };

  return (
    <div className="card bg-base-100 shadow-xl border border-base-300">
      <div className="card-body space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="card-title text-2xl">Sales Opportunity</h2>
            <p className="text-sm opacity-70">
              Consultant sales guidance generated from the parsed credit report.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <span className={`badge ${priorityClass} badge-lg`}>
              {opportunity.priority} Priority
            </span>

            <span className="badge badge-primary badge-lg">
              {opportunity.confidence}% Match
            </span>

            <button type="button" className="btn btn-sm btn-outline" onClick={copySalesScript}>
              {copied ? "Copied" : "Copy Script"}
            </button>
          </div>
        </div>

        <div className="alert alert-info">
          <div>
            <h3 className="font-bold">Best Service to Sell</h3>
            <p>{opportunity.recommendedService}</p>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <Section title="Main Sales Angle">
            <p>{opportunity.salesAngle}</p>
          </Section>

          <Section title="Consultant Opening">
            <p>{opportunity.consultantOpening}</p>
          </Section>
        </div>

        <Section title="Pitch Script">
          <p>{opportunity.pitchScript}</p>
        </Section>

        <div className="grid gap-4 xl:grid-cols-2">
          <ListSection
            title="Pain Points Found"
            items={opportunity.painPoints}
            emptyText="No major pain points detected."
          />

          <ListSection
            title="Accounts to Mention"
            items={opportunity.accountsToMention}
            emptyText="No account highlights available."
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <ListSection
            title="Possible Prescribed Debt"
            items={opportunity.prescribedDebtCandidates}
            emptyText="None detected."
          />

          <ListSection
            title="Furniture Accounts"
            items={opportunity.furnitureAccounts}
            emptyText="None detected."
          />
        </div>

        <ListSection
          title="Questions the Consultant Must Ask"
          items={opportunity.questionsToAsk}
          emptyText="No questions available."
          ordered
        />

        <Section title="Objection Handling">
          <div className="space-y-3">
            {opportunity.objectionHandlers.map((item, index) => (
              <div key={index} className="border-b border-base-300 pb-3 last:border-b-0">
                <p className="font-semibold">Client says: “{item.objection}”</p>
                <p className="opacity-80">Consultant replies: {item.response}</p>
              </div>
            ))}
          </div>
        </Section>

        <ListSection
          title="Next Best Actions"
          items={opportunity.nextBestActions}
          emptyText="No next actions available."
        />

        <div className="alert alert-warning">
          <div>
            <h3 className="font-bold">Compliance Note</h3>
            <p>{opportunity.complianceNote}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  children
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl bg-base-200 p-4">
      <h3 className="font-bold mb-2">{title}</h3>
      {children}
    </div>
  );
}

function ListSection({
  title,
  items,
  emptyText,
  ordered = false
}: {
  title: string;
  items: string[];
  emptyText: string;
  ordered?: boolean;
}) {
  return (
    <Section title={title}>
      {items.length === 0 ? (
        <p className="opacity-70">{emptyText}</p>
      ) : ordered ? (
        <ol className="list-decimal pl-5 space-y-1">
          {items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ol>
      ) : (
        <ul className="list-disc pl-5 space-y-1">
          {items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </Section>
  );
}
