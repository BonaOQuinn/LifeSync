import { Activity, Bell, ChevronDown, ExternalLink, HelpCircle, ShieldCheck } from 'lucide-react'
import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AccountDetail, AccountsPage, ClientProfile, ClientsPage, Home } from './Workspace'
import LifeSync from './LifeSync'
import Wealthbox from './Wealthbox'

export function selectedClient() { return localStorage.getItem('lifesync:selected-client') ?? 'C001' }
export function rememberClient(clientId: string) { localStorage.setItem('lifesync:selected-client', clientId) }

export default function App() {
  const location = useLocation()
  const clientId = location.pathname.match(/\/(?:clients|lifesync)\/(C\d+)/)?.[1] ?? selectedClient()
  const isCrm = location.pathname.startsWith('/wealthbox')
  return <>
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <div className="simulation-bar"><ShieldCheck size={13}/><span>Synthetic data · ClientWorks & Wealthbox simulations · Fixture analysis</span><span className="simulation-version">LPL University Hackathon / 2026</span></div>
    <header className="top-header"><Link to="/home" className="brand"><span className="brand-mark">LPL<span>FINANCIAL</span></span><span className="brand-divider"/><span>Client Management</span></Link><div className="header-tools"><Link to="/wealthbox" className="crm-launcher">Wealthbox CRM <ExternalLink size={13}/></Link><Link to="/home#notifications" className="icon-button" aria-label="Open notifications"><Bell size={18}/></Link><span className="header-divider"/><div className="advisor-avatar">AM</div><span className="advisor-name">Alex Morgan<small>Demo advisor</small></span><ChevronDown size={14}/></div></header>
    {!isCrm && <nav className="main-nav" aria-label="ClientWorks navigation"><div className="nav-content"><NavLink to="/home">Home</NavLink><button disabled title="Practice Metrics is outside the stage 1–4 build">Practice Metrics</button><NavLink to="/clients">Clients</NavLink><NavLink to="/accounts">Accounts</NavLink>{['Groups', 'Investments', 'Orders', 'Activity'].map(label => <button disabled title={`${label} is unavailable in this simulation`} key={label}>{label}</button>)}<NavLink to={`/lifesync/${clientId}?tab=requests`}>Requests</NavLink><button disabled title="Documents are available inside LifeSync evidence">Documents</button><NavLink className="lifesync-nav" to={`/lifesync/${clientId}`}><Activity size={15}/>LifeSync<span className="new-label">NEW</span></NavLink></div></nav>}
    <main id="main-content" className={isCrm ? 'crm-main' : 'workspace'} key={location.pathname}><Routes>
      <Route path="/home" element={<Home/>}/><Route path="/clients" element={<ClientsPage/>}/><Route path="/clients/:clientId" element={<ClientProfile/>}/><Route path="/clients/:clientId/accounts" element={<AccountsPage/>}/><Route path="/accounts" element={<AccountsPage/>}/><Route path="/accounts/:accountId" element={<AccountDetail/>}/><Route path="/lifesync/:clientId" element={<LifeSync/>}/><Route path="/wealthbox" element={<Wealthbox/>}/><Route path="/wealthbox/contacts/:contactId" element={<Wealthbox/>}/><Route path="/" element={<Navigate to="/home" replace/>}/><Route path="*" element={<Navigate to="/home" replace/>}/>
    </Routes></main>
    {!isCrm && <footer className="site-footer"><span><Activity size={14}/> LifeSync · An advisor workspace prototype</span><span><HelpCircle size={13}/> Sample processes, signatures, and institution outcomes are simulated.</span></footer>}
  </>
}
