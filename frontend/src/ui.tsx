import { useEffect, useRef, type ReactNode } from 'react'
import { AlertCircle, ArrowUpRight, Check, FileText, LoaderCircle, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useResource } from './api'
import type { Evidence, Meta, Task } from './types'

export const money = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value)
export const date = (value: string | null | undefined) => value ? new Date(value.length === 10 ? `${value}T12:00:00` : value).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Needs date'
export const owners: Record<string, string> = { 'advisor-01': 'Alex Morgan', 'support-01': 'Taylor Chen' }

export function Status({ value }: { value: string }) {
  const tone = ['Completed', 'No change', 'Ready to submit', 'Linked', 'complete', 'Resolved'].includes(value) ? 'green' : ['Rejected', 'Needs review', 'conflict', 'unavailable', 'missing'].includes(value) ? 'red' : ['Needs information', 'Manual review', 'Waiting for signature', 'Unlinked', 'Needs date'].includes(value) ? 'amber' : 'blue'
  return <span className={`status ${tone}`}><span className="status-dot"/>{value}</span>
}
export function Button({ children, className = '', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`button ${className}`} {...props}>{children}</button>
}
export function Panel({ title, eyebrow, action, children, className = '' }: { title?: string; eyebrow?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{title && <div className="panel-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2></div>{action}</div>}{children}</section>
}
export function PageTitle({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{description && <p className="muted">{description}</p>}</div>{action}</div>
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="empty"><FileText size={30}/><h3>{title}</h3>{children && <p>{children}</p>}</div>
}
export function Notice({ error, success }: { error?: string; success?: string }) {
  return <>{error && <div className="notice error" role="alert"><AlertCircle size={18}/><span>{error}</span></div>}{success && <div className="notice success" role="status"><Check size={18}/><span>{success}</span></div>}</>
}
export function Loading() { return <div className="loading" role="status"><LoaderCircle className="spin" size={22}/>Loading workspace…</div> }
export function LoadError({ message, retry }: { message: string; retry: () => void }) {
  return <Panel><Notice error={message}/><Button onClick={retry}>Retry connection</Button><p className="muted small">Start the FastAPI backend on port 8000 and refresh this view.</p></Panel>
}
export function SourceMeta({ record }: { record: Meta }) {
  return <div className="source-meta"><code>{record.source_id}</code><span>v{record.version}</span><span>Refreshed {date(record.refreshed_at)}</span><span>{record.coverage}</span></div>
}
export function TaskList({ tasks }: { tasks: Task[] }) {
  return tasks.length ? <div className="task-list">{tasks.map(task => <div className="task-row" key={task.task_id}><div className="task-icon"><Check size={15}/></div><div className="grow"><strong>{task.title}</strong><div className="muted small">{owners[task.owner] ?? task.owner} · {date(task.due_date)}{task.delivery && ` · ${task.delivery}`}</div></div>{task.case_id ? <Link className="icon-link" aria-label={`Open task: ${task.title}`} to={`/lifesync/${task.client_id}`}><ArrowUpRight size={18}/></Link> : <Status value={task.status}/>}</div>)}</div> : <Empty title="No open tasks"/>
}
export function EvidenceModal({ sourceId, onClose }: { sourceId: string; onClose: () => void }) {
  const { data, error, loading, reload } = useResource<Evidence>(`/sources/${encodeURIComponent(sourceId)}`)
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => { dialog.current?.showModal() }, [])
  return <dialog ref={dialog} className="evidence-dialog" onCancel={onClose} onClick={event => { if (event.target === dialog.current) onClose() }}>
    <div className="dialog-heading"><div><div className="eyebrow">Authorized source evidence</div><h2>{String(data?.title ?? sourceId)}</h2></div><button className="icon-button" aria-label="Close evidence" onClick={onClose}><X/></button></div>
    {loading ? <Loading/> : error ? <LoadError message={error} retry={reload}/> : data && <><SourceMeta record={data}/>{data.recorded_at !== undefined && <p className="muted small">Recorded {date(String(data.recorded_at))} · {String(data.author ?? 'Source system')}</p>}{data.content !== undefined ? <p className="evidence-content">{String(data.content)}</p> : <pre className="record-json">{JSON.stringify(data, null, 2)}</pre>}<div className="notice info"><FileText size={18}/><span>Synthetic source record. Source content supplies evidence; workflow gates remain enforced by the backend.</span></div></>}
  </dialog>
}
