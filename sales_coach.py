from __future__ import annotations

from typing import Any


def build_sales_coach(parsed: dict[str, Any]) -> dict[str, Any]:
    report = parsed.get("report", {})
    totals = parsed.get("totals", {})
    flags = parsed.get("flags", {})
    score = report.get("credit_score")
    debt_review = bool(report.get("debt_review_flag")) or bool(flags.get("score_zero"))
    active_balances = bool(flags.get("has_active_balances"))
    arrears = bool(flags.get("has_arrears"))
    balance_total = float(totals.get("active_balance_total") or 0)
    arrears_total = float(totals.get("arrears_total") or 0)
    reduced_total = float(totals.get("reduced_total") or 0)

    if debt_review and active_balances:
        recommendation = "Debt Review Removal + Debt Mediation"
        temperature = "Hot"
        reason = "The report indicates debt review or a zero-score debt-review pattern, and there are still active balances to deal with."
        opening = (
            "I can see the debt review listing is only one part of the problem. "
            "The report also shows remaining balances, so the safest approach is to deal with both the removal process and the remaining debt plan."
        )
        closing = (
            "The next step is simple: I will send you the signature link, the document upload link, and the payment mandate. "
            "Once those are completed, admin can prepare your matter properly."
        )
    elif debt_review:
        recommendation = "Debt Review Removal"
        temperature = "Warm"
        reason = "The report indicates a debt review flag or score-zero debt-review pattern, but active balances need admin confirmation."
        opening = (
            "Your report appears to show a debt review issue. Let us first confirm the listing and the remaining obligations, "
            "then admin can advise the cleanest removal route."
        )
        closing = "I will send the signature and document upload links so admin can verify the removal requirements."
    elif arrears or active_balances:
        recommendation = "Debt Mediation"
        temperature = "Warm"
        reason = "The report shows active debt, arrears, or payment pressure but does not clearly show a debt review listing."
        opening = (
            "Your report shows balances that still need a structured plan. Debt mediation helps us approach the debt in a controlled way "
            "instead of leaving you to deal with each creditor alone."
        )
        closing = "I will send you the signature link, upload link, and mandate so we can start preparing the mediation file."
    else:
        recommendation = "Admin Review Before Sale"
        temperature = "Risky"
        reason = "The parser did not find enough clear debt pressure or the report may need manual review."
        opening = "I want to make sure we give you the correct advice. Let me send this to admin for a quick review before we commit to a product."
        closing = "I will pass this file to admin for review and come back with the correct option."

    mediation_explanation = (
        "Debt mediation can support the debt review removal application by showing that the client has a realistic plan for remaining balances, "
        "improved affordability, and creditor engagement. Do not promise that mediation guarantees removal. The final decision remains with the court "
        "or the relevant legal process."
    )

    key_questions = [
        "Are you currently paying through a PDA?",
        "Are you trying to be removed from debt review, reduce the current monthly pressure, or both?",
        "What amount can you realistically afford every month without missing essentials?",
        "Do you have recent payslips, bank statements, ID copy, and proof of residence ready?",
        "Have any creditors contacted you directly or threatened legal action recently?",
    ]

    objections = [
        {
            "objection": "I only want to be removed from debt review.",
            "reply": "Removal deals with the listing, but if balances remain, they still need to be handled. Mediation supports the file by showing a realistic plan for those balances."
        },
        {
            "objection": "Can you guarantee the judge will remove me?",
            "reply": "No one should guarantee the court's decision. What we can do is prepare the file properly and show affordability, documents, and a responsible plan."
        },
        {
            "objection": "I need to think about it.",
            "reply": "That is fine. The reason I suggest starting now is that admin cannot prepare anything until your documents and mandate are completed."
        },
        {
            "objection": "I cannot afford a big upfront fee.",
            "reply": "We can check whether the fee can be structured. The important part is that the plan must be realistic and not create more pressure."
        },
    ]

    compliance_warnings = [
        "Do not promise removal, court success, or creditor acceptance.",
        "Do not say debt mediation influences a judge. Say it supports the application with affordability and payment-plan evidence.",
        "Confirm affordability before sending a mandate.",
        "Escalate to admin/legal if the report shows judgments, sequestration, disputes, or unclear debt-review status.",
    ]

    next_best_actions = [
        "Confirm the client's goal: removal, mediation, or both.",
        "Confirm affordability and preferred debit date.",
        "Send signature link.",
        "Send document upload link.",
        "Send NuPay mandate after affordability is confirmed.",
        "Pass to admin once signature, documents, and mandate are completed or pending authorisation.",
    ]

    money_summary = {
        "balance_total": round(balance_total, 2),
        "arrears_total": round(arrears_total, 2),
        "suggested_reduced_total": round(reduced_total, 2),
    }

    return {
        "service_recommendation": recommendation,
        "lead_temperature": temperature,
        "reason": reason,
        "money_summary": money_summary,
        "opening_script": opening,
        "mediation_explanation": mediation_explanation,
        "key_questions": key_questions,
        "objections": objections,
        "closing_script": closing,
        "next_best_actions": next_best_actions,
        "compliance_warnings": compliance_warnings,
        "consultant_prompt": (
            "Lead with relief and clarity. Explain what the report shows, link the product to the client's goal, "
            "then move directly to signature, documents, mandate, and admin handoff."
        ),
        "score_used": score,
    }
