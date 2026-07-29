import { FormEvent, useEffect, useMemo, useState } from "react";
import "./App.css";

type Tenant = {
  id: string;
  name: string;
  companyName?: string;
  ncrNumber?: string;
  email?: string;
  phone?: string;
  status?: string;
};

type Applicant = {
  fullName?: string;
  idNumber?: string;
  tel?: string;
  whatsapp?: string;
  email?: string;
};

type Account = {
  id: string;
  creditorName: string;
  accountNumber?: string;
  openingBalance?: number;
  currentBalance?: number;
  arrearsAmount?: number;
  monthlyInstalment?: number;
  reducedAmount?: number;
  accountStatus?: string;
  included?: boolean;
};

type Client = {
  id: string;
  tenantId: string;
  caseNumber?: string;
  serviceType?: string;
  workflowStage?: string;
  primaryApplicant?: Applicant;
  accounts?: Account[];
  flags?: Record<string, boolean>;
  creditReport?: {
    filename?: string;
    bureau?: string;
    confidence?: number;
    warnings?: string[];
    uploadedAt?: string;
  };
};

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000";

function currency(value?: number) {
  return Number(value || 0).toLocaleString("en-ZA", {
    style: "currency",
    currency: "ZAR",
  });
}

async function api(path: string, options: RequestInit = {}) {
  const headers: HeadersInit = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  const raw = await response.text();
  let data: any = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    throw new Error(`Backend returned invalid JSON: ${raw.slice(0, 160)}`);
  }

  if (!response.ok || data.success === false) {
    throw new Error(data.error || data.message || `Request failed (${response.status})`);
  }
  return data;
}

export default function App() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState(
    localStorage.getItem("ft_tenant_id") || "fin-tastic",
  );
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClientId, setSelectedClientId] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [creatingTenant, setCreatingTenant] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [tenantForm, setTenantForm] = useState({
    name: "",
    ncrNumber: "",
    email: "",
    phone: "",
  });

  const selectedClient = useMemo(
    () => clients.find((client) => client.id === selectedClientId) || clients[0] || null,
    [clients, selectedClientId],
  );

  const activeTenant = useMemo(
    () => tenants.find((tenant) => tenant.id === tenantId) || tenants[0],
    [tenants, tenantId],
  );

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    localStorage.setItem("ft_tenant_id", tenantId);
    if (tenantId) loadClients(tenantId);
  }, [tenantId]);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const tenantData = await api("/api/tenants");
      const loadedTenants: Tenant[] = tenantData.tenants || [];
      setTenants(loadedTenants);

      const validTenant =
        loadedTenants.find((item) => item.id === tenantId)?.id ||
        loadedTenants[0]?.id ||
        "fin-tastic";
      setTenantId(validTenant);
      await loadClients(validTenant);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load Fin-Tastic.");
    } finally {
      setLoading(false);
    }
  }

  async function loadClients(currentTenantId: string) {
    try {
      const data = await api("/api/clients", {
        headers: { "X-Tenant-ID": currentTenantId },
      });
      const loaded: Client[] = data.clients || data.cases || [];
      setClients(loaded);
      setSelectedClientId((current) =>
        loaded.some((item) => item.id === current) ? current : loaded[0]?.id || "",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load clients.");
    }
  }

  async function createTenant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreatingTenant(true);
    setError("");
    setMessage("");

    try {
      const data = await api("/api/tenants", {
        method: "POST",
        body: JSON.stringify(tenantForm),
      });
      const tenant: Tenant = data.tenant;
      setTenants(data.tenants || ((current: Tenant[]) => [...current, tenant]));
      setTenantId(tenant.id);
      setTenantForm({ name: "", ncrNumber: "", email: "", phone: "" });
      setMessage(`${tenant.name} was created and saved.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create tenant.");
    } finally {
      setCreatingTenant(false);
    }
  }

  async function uploadReport(file: File) {
    setUploading(true);
    setError("");
    setMessage("");

    try {
      const body = new FormData();
      body.append("file", file);
      body.append("tenant_id", tenantId);

      const data = await api("/api/upload/credit-report", {
        method: "POST",
        body,
        headers: { "X-Tenant-ID": tenantId },
      });

      const client: Client =
        data.client ||
        data.result?.client ||
        data.parsed?.client;

      if (!client?.id) {
        throw new Error("The backend parsed the report but did not return a client record.");
      }

      setClients((current) => [
        client,
        ...current.filter((item) => item.id !== client.id),
      ]);
      setSelectedClientId(client.id);

      const accountCount =
        client.accounts?.length ||
        data.accounts?.length ||
        data.result?.accounts?.length ||
        0;

      setMessage(
        `Report parsed successfully. ${accountCount} account${
          accountCount === 1 ? "" : "s"
        } displayed.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to upload the report.");
    } finally {
      setUploading(false);
    }
  }

  const totals = useMemo(() => {
    const accounts = selectedClient?.accounts || [];
    return {
      balance: accounts.reduce((sum, item) => sum + Number(item.currentBalance || 0), 0),
      monthly: accounts.reduce((sum, item) => sum + Number(item.monthlyInstalment || 0), 0),
      reduced: accounts.reduce((sum, item) => sum + Number(item.reducedAmount || 0), 0),
    };
  }, [selectedClient]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">FT</div>
          <div>
            <h1>Fin-Tastic</h1>
            <p>Enterprise</p>
          </div>
        </div>

        <label className="field">
          <span>Active tenant</span>
          <select value={tenantId} onChange={(event) => setTenantId(event.target.value)}>
            {tenants.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.name}
              </option>
            ))}
          </select>
        </label>

        <div className="tenant-summary">
          <strong>{activeTenant?.name || "No tenant selected"}</strong>
          <span>{activeTenant?.ncrNumber || "NCR number not captured"}</span>
          <span>{activeTenant?.email || "Email not captured"}</span>
        </div>

        <button className="secondary" type="button" onClick={loadData}>
          Refresh all data
        </button>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <h2>Tenant & Credit Report Fix</h2>
            <p>Backend: {API_BASE}</p>
          </div>
          <span className="status">Connected workflow</span>
        </header>

        {message && <div className="notice success">{message}</div>}
        {error && <div className="notice error">{error}</div>}
        {loading && <div className="panel">Loading Fin-Tastic data…</div>}

        {!loading && (
          <>
            <section className="grid two">
              <form className="panel" onSubmit={createTenant}>
                <div className="section-heading">
                  <div>
                    <h3>Create Tenant</h3>
                    <p>New tenants are saved in backend/data/tenants.json.</p>
                  </div>
                </div>

                <div className="form-grid">
                  <label className="field full">
                    <span>Company / tenant name *</span>
                    <input
                      required
                      value={tenantForm.name}
                      onChange={(event) =>
                        setTenantForm({ ...tenantForm, name: event.target.value })
                      }
                      placeholder="Example Debt Solutions"
                    />
                  </label>

                  <label className="field">
                    <span>NCRDC number</span>
                    <input
                      value={tenantForm.ncrNumber}
                      onChange={(event) =>
                        setTenantForm({ ...tenantForm, ncrNumber: event.target.value })
                      }
                      placeholder="NCRDC-0000"
                    />
                  </label>

                  <label className="field">
                    <span>Phone</span>
                    <input
                      value={tenantForm.phone}
                      onChange={(event) =>
                        setTenantForm({ ...tenantForm, phone: event.target.value })
                      }
                      placeholder="021 000 0000"
                    />
                  </label>

                  <label className="field full">
                    <span>Email</span>
                    <input
                      type="email"
                      value={tenantForm.email}
                      onChange={(event) =>
                        setTenantForm({ ...tenantForm, email: event.target.value })
                      }
                      placeholder="admin@example.co.za"
                    />
                  </label>
                </div>

                <button className="primary" type="submit" disabled={creatingTenant}>
                  {creatingTenant ? "Creating tenant…" : "Create Tenant"}
                </button>
              </form>

              <section className="panel upload-panel">
                <div className="section-heading">
                  <div>
                    <h3>Upload Credit Report</h3>
                    <p>The parsed client and accounts appear immediately below.</p>
                  </div>
                </div>

                <label className={`upload-box ${uploading ? "disabled" : ""}`}>
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    disabled={uploading || !tenantId}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) uploadReport(file);
                      event.target.value = "";
                    }}
                  />
                  <strong>
                    {uploading ? "Uploading and analysing…" : "Choose PDF credit report"}
                  </strong>
                  <span>Maximum file size: 25 MB</span>
                </label>
              </section>
            </section>

            <section className="panel">
              <div className="section-heading">
                <div>
                  <h3>Clients for {activeTenant?.name || "tenant"}</h3>
                  <p>Select a client to view the parsed report.</p>
                </div>
                <span className="count">{clients.length}</span>
              </div>

              {clients.length === 0 ? (
                <div className="empty">No reports uploaded for this tenant yet.</div>
              ) : (
                <div className="client-list">
                  {clients.map((client) => (
                    <button
                      type="button"
                      key={client.id}
                      className={client.id === selectedClient?.id ? "client active" : "client"}
                      onClick={() => setSelectedClientId(client.id)}
                    >
                      <strong>
                        {client.primaryApplicant?.fullName ||
                          client.primaryApplicant?.idNumber ||
                          "Unknown client"}
                      </strong>
                      <span>{client.caseNumber || client.id}</span>
                      <span>{client.workflowStage || "Credit Report Parsed"}</span>
                    </button>
                  ))}
                </div>
              )}
            </section>

            {selectedClient && (
              <>
                <section className="summary-grid">
                  <div className="metric">
                    <span>Client</span>
                    <strong>
                      {selectedClient.primaryApplicant?.fullName || "Not detected"}
                    </strong>
                    <small>
                      ID: {selectedClient.primaryApplicant?.idNumber || "Not detected"}
                    </small>
                  </div>
                  <div className="metric">
                    <span>Bureau</span>
                    <strong>{selectedClient.creditReport?.bureau || "Unknown"}</strong>
                    <small>
                      Confidence: {selectedClient.creditReport?.confidence ?? 0}%
                    </small>
                  </div>
                  <div className="metric">
                    <span>Total balance</span>
                    <strong>{currency(totals.balance)}</strong>
                    <small>{selectedClient.accounts?.length || 0} accounts</small>
                  </div>
                  <div className="metric">
                    <span>Reduced payment</span>
                    <strong>{currency(totals.reduced)}</strong>
                    <small>Contractual: {currency(totals.monthly)}</small>
                  </div>
                </section>

                {(selectedClient.creditReport?.warnings || []).length > 0 && (
                  <section className="panel warning-panel">
                    <h3>Parser warnings</h3>
                    {(selectedClient.creditReport?.warnings || []).map((warning) => (
                      <p key={warning}>• {warning}</p>
                    ))}
                  </section>
                )}

                <section className="panel">
                  <div className="section-heading">
                    <div>
                      <h3>Parsed Accounts</h3>
                      <p>
                        {selectedClient.creditReport?.filename || "Uploaded credit report"}
                      </p>
                    </div>
                    <span className="count">{selectedClient.accounts?.length || 0}</span>
                  </div>

                  {(selectedClient.accounts || []).length === 0 ? (
                    <div className="empty">
                      The report uploaded, but no account rows were detected. Review the parser warnings.
                    </div>
                  ) : (
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Creditor</th>
                            <th>Account</th>
                            <th>Opening</th>
                            <th>Current</th>
                            <th>Arrears</th>
                            <th>Instalment</th>
                            <th>Reduced</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(selectedClient.accounts || []).map((account) => (
                            <tr key={account.id}>
                              <td>{account.creditorName || "Unknown creditor"}</td>
                              <td>{account.accountNumber || "—"}</td>
                              <td>{currency(account.openingBalance)}</td>
                              <td>{currency(account.currentBalance)}</td>
                              <td>{currency(account.arrearsAmount)}</td>
                              <td>{currency(account.monthlyInstalment)}</td>
                              <td>{currency(account.reducedAmount)}</td>
                              <td>{account.accountStatus || "Active"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
