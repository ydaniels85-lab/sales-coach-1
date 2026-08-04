import { useEffect, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { DashboardView } from "./components/DashboardView";
import { UploadView } from "./components/UploadView";
import { ReportsView } from "./components/ReportsView";
import { WorkspaceView } from "./components/WorkspaceView";
import { StatutoryWorkflowView } from "./components/StatutoryWorkflowView";
import { ClientPortalView } from "./components/ClientPortalView";
import { TenantSecurityPortal } from "./components/TenantSecurityPortal";
import { SettingsView } from "./components/SettingsView";
import { mockCases, tenants as starterTenants } from "./data";
import { MockCase, TabKey, Tenant } from "./types";

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("dashboard");
  const [tenants] = useState<Tenant[]>(starterTenants);
  const [activeTenant, setActiveTenant] = useState<Tenant>(starterTenants[0]);
  const [leads, setLeads] = useState<MockCase[]>(() => {
    const saved = localStorage.getItem("fin-tastic-leads");
    return saved ? JSON.parse(saved) : mockCases;
  });
  const [selectedClient, setSelectedClient] = useState<MockCase>(leads[0] || mockCases[0]);
  const [targetInterestRate, setTargetInterestRate] = useState(3.5);
  const [targetTerm, setTargetTerm] = useState(60);

  useEffect(() => { localStorage.setItem("fin-tastic-leads", JSON.stringify(leads)); }, [leads]);
  const tenantLeads = leads.filter(l => l.tenantId === activeTenant.id || !l.tenantId);
  const selectAndOpen = (lead: MockCase) => { setSelectedClient(lead); setActiveTab("workspace"); };
  const addImported = (lead: MockCase) => { const withTenant = {...lead, tenantId: activeTenant.id}; setLeads(prev => [withTenant, ...prev]); setSelectedClient(withTenant); setActiveTab("workspace"); };

  return <div className="app">
    <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} activeTenant={activeTenant}/>
    <main className="main">
      <div className="header"><div><h1>Fin-Tastic Enterprise</h1><span className="muted">Parser-only restored workflow | {activeTenant.name}</span></div><span className="badge green">Backend: localhost:5000</span></div>
      {activeTab === "dashboard" && <DashboardView leads={tenantLeads} onOpen={selectAndOpen}/>}      
      {activeTab === "upload" && <UploadView onImported={addImported}/>}      
      {activeTab === "reports" && <ReportsView leads={tenantLeads} selected={selectedClient} setSelected={setSelectedClient}/>}      
      {activeTab === "workspace" && <WorkspaceView selectedClient={selectedClient}/>}      
      {activeTab === "statutory" && <StatutoryWorkflowView selectedClient={selectedClient}/>}      
      {activeTab === "portal" && <ClientPortalView selectedClient={selectedClient}/>}      
      {activeTab === "practices" && <TenantSecurityPortal tenants={tenants} activeTenant={activeTenant} setActiveTenant={setActiveTenant}/>}      
      {activeTab === "settings" && <SettingsView targetInterestRate={targetInterestRate} setTargetInterestRate={setTargetInterestRate} targetTerm={targetTerm} setTargetTerm={setTargetTerm}/>}      
      <div className="footer">© 2026 {activeTenant.name} / Fin-Tastic Multi-Tenant Network</div>
    </main>
  </div>;
}
