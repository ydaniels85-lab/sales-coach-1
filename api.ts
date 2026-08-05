const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

async function parseJson(response: Response) {
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok || data.success === false) {
    throw new Error(data.error || `Request failed with status ${response.status}`);
  }
  return data;
}

export async function health() {
  const response = await fetch(`${API_BASE}/api/health`);
  return parseJson(response);
}

export async function fetchLeads() {
  const response = await fetch(`${API_BASE}/api/leads`);
  return parseJson(response);
}

export async function fetchHandoffs() {
  const response = await fetch(`${API_BASE}/api/admin/handoffs`);
  return parseJson(response);
}

export async function uploadCreditReport(file: File, clientName?: string) {
  const form = new FormData();
  form.append('file', file);
  if (clientName) form.append('client_name', clientName);
  const response = await fetch(`${API_BASE}/api/upload/credit-report`, {
    method: 'POST',
    body: form,
  });
  return parseJson(response);
}

export async function createManualLead(payload: any) {
  const response = await fetch(`${API_BASE}/api/leads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return parseJson(response);
}

export async function leadAction(leadId: string, action: string, payload: any = {}) {
  const response = await fetch(`${API_BASE}/api/leads/${leadId}/${action}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return parseJson(response);
}
