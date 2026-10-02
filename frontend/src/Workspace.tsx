import { useEffect, useState } from 'react'
import { Activity, ArrowRight, ArrowUpRight, BriefcaseBusiness, ChevronRight, FileCheck2, Landmark, MapPin, Search, Users } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, useResource } from './api'
import { rememberClient } from './App'
import { Button, Empty, LoadError, Loading, money, PageTitle, Panel, SourceMeta, Status, TaskList } from './ui'
import type { Account, Client, Dashboard } from './types'

function Stats({ items }: { items: { label: string; value: string | number; caption: string; icon: React.ReactNode }[] }) {
  return <div className="stats-grid">{items.map(item => <div className="stat-card" key={item.label}><div className="stat-top"><span>{item.label}</span><span className="stat-icon">{item.icon}</span></div><strong>{item.value}</strong><small>{item.caption}</small></div>)}</div>
}

export function Home() {
  const { data, error, loading, reload } = useResource<Dashboard>('/dashboard')
  if (loading) return <Loading/>
  if (error || !data) return <LoadError message={error} retry={reload}/>
  return <><PageTitle eyebrow="Your practice at a glance" title="Welcome back, Alex." description="A connected view of your clients, open work, and what needs attention." action={<span className="today-pill">Friday, October 2, 2026 · Demo day</span>}/>
    <div className="welcome-banner"><div><span className="banner-eyebrow"><span className="live-dot"/> A little clarity for life's big changes</span><h2>Life changes. Your workflow keeps up.</h2><p>Bring the records, instructions, and next steps into one review.</p><Link className="button light" to="/lifesync/C001">Open Maya's LifeSync case <ArrowRight size={15}/></Link></div><div className="banner-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="art-core"><Activity size={48}/></div><div className="art-chip chip-one"><FileCheck2 size={17}/> Human approval</div><div className="art-chip chip-two"><Landmark size={17}/> Connected context</div></div></div>
    <Stats items={[{ label: 'Assigned clients', value: data.client_count, caption: 'Within your advisor assignment', icon: <Users size={18}/> }, { label: 'Assets under review', value: money(data.total_value), caption: `${data.account_count} synthetic accounts`, icon: <BriefcaseBusiness size={18}/> }, { label: 'Open LifeSync cases', value: data.open_cases, caption: 'Persisted across sessions', icon: <Activity size={18}/> }, { label: 'Open notifications', value: data.notifications.length, caption: 'Owned tasks & client reminders', icon: <FileCheck2 size={18}/> }]}/>
    <div className="dashboard-grid"><Panel title="Open notifications" eyebrow="Keep the next step moving" action={<span className="count-pill">{data.notifications.length}</span>}><div id="notifications"><TaskList tasks={data.notifications}/></div></Panel><Panel title="Quick actions"><Link className="quick-action" to="/clients"><span className="action-icon"><Users size={19}/></span><div><strong>Review a client</strong><small>Accounts, records & relationships</small></div><ChevronRight size={16}/></Link><Link className="quick-action" to="/lifesync/C001"><span className="action-icon teal"><Activity size={19}/></span><div><strong>Start a life event review</strong><small>Confirmed intent. Clear next steps.</small></div><ChevronRight size={16}/></Link><Link className="quick-action" to="/wealthbox"><span className="action-icon plum"><Landmark size={19}/></span><div><strong>Open Wealthbox CRM</strong><small>Linked notes, tasks & account context</small></div><ChevronRight size={16}/></Link></Panel></div>
    <div className="dashboard-grid lower"><Panel title="Recent requests" action={<Link className="text-link" to="/lifesync/C001?tab=requests">View tracking <ArrowUpRight size={14}/></Link>}>{data.recent_requests.length ? <div className="table-wrap"><table><thead><tr><th>Request</th><th>Account</th><th>Status</th><th/></tr></thead><tbody>{data.recent_requests.map(request => <tr key={request.request_id}><td><span className="strong">{request.external_request_id}</span><small>Simulated institution request</small></td><td>{request.account_id}</td><td><Status value={request.status}/></td><td><Link to={`/lifesync/${request.client_id}?tab=requests`}>Open</Link></td></tr>)}</tbody></table></div> : <Empty title="No servicing requests yet">Approved requests will appear here as your review progresses.</Empty>}</Panel><Panel title="System news & alerts"><div className="news-card"><span className="eyebrow">Workspace update</span><h3>LifeSync is ready for review.</h3><p>This build covers stages 1–4 with deterministic, cited fixture findings.</p><span className="muted small">Synthetic data · Oct 2, 2026</span></div><div className="compliance-note"><FileCheck2 size={18}/><div><strong>Review stays with the advisor</strong><p>Exact draft approvals and simulated signature gates are checked by the backend.</p></div></div></Panel></div>
  </>
}

function QuickViews({ mode, active, onSelect }: { mode: 'Clients' | 'Accounts'; active: string; onSelect: (value: string) => void }) {
  const views = mode === 'Clients' ? [['', 'All assigned clients'], ['Divorce', 'Divorce review'], ['Death', 'Death review']] : [['', 'All accounts'], ['Individual', 'Individual accounts'], ['Retirement', 'Retirement accounts']]
  return <aside className="quick-views"><div className="eyebrow">Quick Views</div><h3>{mode}</h3>{views.map(([value, label]) => <button className={active === value ? 'selected' : ''} key={label} onClick={() => onSelect(value)}><span className="view-dot"/>{label}</button>)}<div className="sidebar-note"><FileCheck2 size={17}/><p>Showing records assigned to Alex Morgan. Access is checked by the server.</p></div></aside>
}

export function ClientsPage() {
  const { data, error, loading, reload } = useResource<Client[]>('/clients')
  const [params, setParams] = useSearchParams(sessionStorage.getItem('lifesync:clients-query') ?? '')
  useEffect(() => { sessionStorage.setItem('lifesync:clients-query', params.toString()) }, [params])
  const search = params.get('q') ?? '', filter = params.get('event') ?? ''
  function update(key: string, value: string) { setParams(previous => { value ? previous.set(key, value) : previous.delete(key); return previous }, { replace: true }) }
  const clients = (data ?? []).filter(client => (!filter || client.event_hint === filter) && `${client.display_name} ${client.client_id} ${client.primary_email}`.toLowerCase().includes(search.toLowerCase()))
  return <><PageTitle eyebrow="Client Management" title="Clients" description="Know the person. Connect the whole picture."/><div className="list-layout"><QuickViews mode="Clients" active={filter} onSelect={value => update('event', value)}/><div className="list-content"><div className="list-summary"><div><span className="muted small">Assigned relationships</span><strong>{data?.length ?? '—'}</strong></div><div><span className="muted small">Total account value</span><strong>{money((data ?? []).reduce((sum, client) => sum + (client.total_value ?? 0), 0))}</strong></div><div className="list-tools"><button disabled title="Column customization is unavailable">Edit columns</button><button disabled title="Exports are unavailable">Export</button></div></div><Panel><div className="table-toolbar"><label className="search"><Search size={17}/><input aria-label="Search clients" placeholder="Search clients by name, email, or ID" value={search} onChange={event => update('q', event.target.value)}/></label><span className="filter-chip">Assigned to me</span>{filter && <button className="filter-chip" onClick={() => update('event', '')}>{filter} ×</button>}</div>{loading ? <Loading/> : error ? <LoadError message={error} retry={reload}/> : clients.length ? <div className="table-wrap"><table><thead><tr><th>Client name</th><th>Client ID</th><th>Accounts</th><th>Total value</th><th>Life event</th><th/></tr></thead><tbody>{clients.map(client => <tr key={client.client_id}><td><Link className="client-cell" to={`/clients/${client.client_id}`} onClick={() => rememberClient(client.client_id)}><span className="client-avatar">{client.display_name.split(' ').map(word => word[0]).join('')}</span><span><strong>{client.display_name}</strong><small>{client.primary_email}</small></span></Link></td><td>{client.client_id}</td><td>{client.account_count}</td><td className="number">{money(client.total_value ?? 0)}</td><td><span className="event-tag">{client.event_hint}</span></td><td><Link className="text-link" to={`/lifesync/${client.client_id}`} onClick={() => rememberClient(client.client_id)}>Open LifeSync <ArrowUpRight size={14}/></Link></td></tr>)}</tbody></table></div> : <Empty title="No matching clients">Try a different search or Quick View.</Empty>}<div className="table-footer">{clients.length} relationships · synthetic assigned records</div></Panel></div></div></>
}

export function ClientProfile() {
  const { clientId = 'C001' } = useParams()
  const { data: client, error, loading, reload } = useResource<Client>(`/clients/${clientId}`)
  const accounts = useResource<Account[]>(`/clients/${clientId}/accounts`)
  useEffect(() => { if (client) rememberClient(clientId) }, [client, clientId])
  if (loading) return <Loading/>
  if (error || !client) return <LoadError message={error} retry={reload}/>
  return <><Link className="back-link" to="/clients">← Back to clients</Link><PageTitle eyebrow={`Client profile / ${clientId}`} title={client.display_name} description="Contact details and the accounts behind the relationship." action={<Link className="button primary" to={`/lifesync/${clientId}`}><Activity size={16}/>Open LifeSync</Link>}/><div className="profile-grid"><Panel title="Relationship details"><div className="profile-contact"><div className="large-avatar">{client.display_name.split(' ').map(word => word[0]).join('')}</div><div><h3>{client.display_name}</h3><p className="muted">Individual client · {clientId}</p><Status value="Assigned to Alex Morgan"/></div></div><dl className="details-list"><div><dt>Mailing address</dt><dd>{client.address}</dd></div><div><dt>Primary email</dt><dd>{client.primary_email}</dd></div><div><dt>Telephone</dt><dd>{client.phone}</dd></div><div><dt>Wealthbox contact</dt><dd>{client.crm_contact_id ? <Link className="text-link" to={`/wealthbox/contacts/${client.crm_contact_id}`}>Open linked contact <ArrowUpRight size={14}/></Link> : <Status value="Unlinked"/>}</dd></div></dl><SourceMeta record={client}/></Panel><Panel title="Life event review" className="event-panel"><div className="event-orb"><Activity size={29}/></div><h3>A connected place for the next chapter.</h3><p className="muted">{client.event_hint} is the seeded review example. Confirm the event before loading fixture findings.</p><Link className="button primary" to={`/lifesync/${clientId}`}>Open Lifecycle page <ArrowRight size={16}/></Link><div className="small muted spaced">Fixture analysis · Human instructions · Simulated outcomes</div></Panel></div><Panel title="Financial accounts" action={<Link className="text-link" to={`/clients/${clientId}/accounts`}>View all accounts <ArrowUpRight size={14}/></Link>}>{accounts.loading ? <Loading/> : accounts.error ? <LoadError message={accounts.error} retry={accounts.reload}/> : <AccountTable accounts={accounts.data ?? []}/>}</Panel></>
}

export function AccountTable({ accounts }: { accounts: Account[] }) {
  return accounts.length ? <div className="table-wrap"><table><thead><tr><th>Account / Client</th><th>Account number</th><th>Class</th><th>Value</th><th>Objective</th><th>ACH</th><th>Distribution</th></tr></thead><tbody>{accounts.map(account => <tr key={account.account_id}><td><Link className="strong" to={`/accounts/${account.account_id}`} onClick={() => rememberClient(account.client_id)}>{account.title}</Link><small>{account.account_id} · {account.client_id}</small></td><td className="masked">{account.masked_number}</td><td><span className="event-tag">{account.class}</span></td><td className="number">{money(account.value)}</td><td>{account.objective}</td><td>{account.ach}</td><td>{account.distribution}</td></tr>)}</tbody></table></div> : <Empty title="No matching accounts"/>
}

export function AccountsPage() {
  const { clientId } = useParams()
  const queryKey = `lifesync:accounts-query:${clientId ?? 'all'}`
  const [params, setParams] = useSearchParams(sessionStorage.getItem(queryKey) ?? '')
  useEffect(() => { sessionStorage.setItem(queryKey, params.toString()) }, [params, queryKey])
  const clientFilter = clientId ?? params.get('client') ?? ''
  const clients = useResource<Client[]>('/clients')
  const { data, error, loading, reload } = useResource<Account[]>(clientFilter ? `/clients/${clientFilter}/accounts` : '/clients')
  const [allAccounts, setAllAccounts] = useState<Account[]>([])
  const [allError, setAllError] = useState('')
  const [allLoading, setAllLoading] = useState(!clientFilter)
  useEffect(() => {
    let active = true
    if (!clientFilter && clients.data) {
      setAllLoading(true)
      Promise.all(clients.data.map(client => api<Account[]>(`/clients/${client.client_id}/accounts`)))
        .then(groups => { if (active) { setAllAccounts(groups.flat()); setAllError('') } })
        .catch((failure: Error) => { if (active) setAllError(failure.message) })
        .finally(() => { if (active) setAllLoading(false) })
    }
    return () => { active = false }
  }, [clients.data, clientFilter])
  function update(key: string, value: string) { setParams(previous => { value ? previous.set(key, value) : previous.delete(key); return previous }, { replace: true }) }
  const filter = params.get('class') ?? '', search = params.get('q') ?? ''
  const accounts = clientFilter ? data ?? [] : allAccounts
  const filtered = accounts.filter(account => (!filter || account.class === filter) && `${account.title} ${account.account_id} ${account.masked_number}`.toLowerCase().includes(search.toLowerCase()))
  return <>{clientId && <Link className="back-link" to={`/clients/${clientId}`}>← Back to client profile</Link>}<PageTitle eyebrow="Client Management" title="Accounts" description="Financial context, with clear boundaries for every change." action={clientFilter && <Link className="button primary" to={`/lifesync/${clientFilter}`}><Activity size={16}/>Open LifeSync</Link>}/><div className="list-layout"><QuickViews mode="Accounts" active={filter} onSelect={value => update('class', value)}/><div className="list-content"><div className="list-summary"><div><span className="muted small">Total accounts</span><strong>{accounts.length}</strong></div><div><span className="muted small">Account value</span><strong>{money(accounts.reduce((sum, account) => sum + account.value, 0))}</strong></div>{!clientId && <label className="client-filter">Client<select aria-label="Filter accounts by client" value={clientFilter} onChange={event => update('client', event.target.value)}><option value="">All assigned clients</option>{clients.data?.map(client => <option key={client.client_id} value={client.client_id}>{client.display_name}</option>)}</select></label>}</div><Panel><div className="table-toolbar"><label className="search"><Search size={17}/><input aria-label="Search accounts" placeholder="Search account name, ID, or masked number" value={search} onChange={event => update('q', event.target.value)}/></label><span className="filter-chip">Active</span>{filter && <button className="filter-chip" onClick={() => update('class', '')}>{filter} ×</button>}</div>{loading || (!clientFilter && (clients.loading || allLoading)) ? <Loading/> : error || allError || clients.error ? <LoadError message={error || allError || clients.error} retry={() => { reload(); clients.reload() }}/>: <AccountTable accounts={filtered}/>}<div className="table-footer">{filtered.length} accounts · overview identifiers are masked</div></Panel></div></div></>
}

export function AccountDetail() {
  const { accountId = 'A101' } = useParams()
  const { data: account, error, loading, reload } = useResource<Account>(`/accounts/${accountId}`)
  useEffect(() => { if (account) rememberClient(account.client_id) }, [account])
  if (loading) return <Loading/>
  if (error || !account) return <LoadError message={error} retry={reload}/>
  return <><Link className="back-link" to={`/clients/${account.client_id}/accounts`}>← Back to client accounts</Link><PageTitle eyebrow={`Account detail / ${accountId}`} title={account.title} description={`${account.type} · ${account.masked_number}`} action={<Link className="button primary" to={`/lifesync/${account.client_id}`}><Activity size={16}/>Review in LifeSync</Link>}/><div className="profile-grid"><Panel title="Account snapshot"><div className="account-value">{money(account.value)}<span>synthetic account value</span></div><dl className="details-list"><div><dt>Account owner</dt><dd>{account.owners.join(', ')}</dd></div><div><dt>Class / objective</dt><dd>{account.class} / {account.objective}</dd></div><div><dt>Account address</dt><dd><MapPin size={15}/>{account.address}</dd></div><div><dt>Client relationship</dt><dd><Link className="text-link" to={`/clients/${account.client_id}`}>Return to client profile <ArrowUpRight size={14}/></Link></dd></div></dl><SourceMeta record={account}/></Panel><Panel title="Beneficiaries">{account.beneficiaries.length ? account.beneficiaries.map(person => <div className="beneficiary-row" key={person.name}><div className="client-avatar">{person.name.split(' ').map(word => word[0]).join('')}</div><div><strong>{person.name}</strong><p className="muted small">{person.relationship}</p></div><span className="percentage">{person.percentage}%</span></div>) : <Empty title="No beneficiary entries in this fixture"/>}<div className="notice info"><FileCheck2 size={18}/><span>Beneficiary and ownership fields are outside contact synchronization. Changes require specific client instructions.</span></div></Panel></div></>
}
