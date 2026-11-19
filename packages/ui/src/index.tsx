import React from 'react';
import { Activity, ArrowLeft, ArrowRight, Bell, HelpCircle, Home, Layers3, UserRound, UsersRound } from 'lucide-react';
import './styles.css';

export { Activity, ArrowLeft, ArrowRight, Bell, HelpCircle as CircleHelp, Home as House, Layers3, UserRound, UsersRound };
export type Locale = 'ru' | 'en';
export function Button({ variant='primary', className='', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary'|'secondary'|'ghost' }) {
  return <button className={`ui-btn ui-btn-${variant} ${className}`} {...props}/>;
}
export function Card({ className='', ...props }: React.HTMLAttributes<HTMLElement>) {
  return <section className={`ui-card ${className}`} {...props}/>;
}
export function Field({ label, hint, error, id, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string }) {
  const fieldId=id || React.useId();
  return <div className="grid gap-2"><label htmlFor={fieldId} className="text-sm font-semibold">{label}</label><input id={fieldId} className="ui-field" aria-invalid={!!error} aria-describedby={error||hint?`${fieldId}-help`:undefined} {...props}/>{(error||hint)&&<p id={`${fieldId}-help`} className={`text-sm ${error?'text-negative':'ui-muted'}`}>{error||hint}</p>}</div>;
}
export function Notice({ children, tone='info' }: { children: React.ReactNode; tone?: 'info'|'warning'|'error'|'success' }) {
  return <div role={tone==='error'?'alert':'status'} className="ui-status" data-tone={tone}>{children}</div>;
}
export function Segmented<T extends string>({ options, value, onChange, label }: {options: readonly {value:T;label:string}[];value:T;onChange:(v:T)=>void;label:string}) {
  return <div className="flex gap-2" role="group" aria-label={label}>{options.map(o=><button key={o.value} className="ui-btn ui-btn-secondary min-w-0 flex-1" aria-pressed={value===o.value} style={value===o.value?{background:'#7044e0',borderColor:'#7044e0'}:undefined} onClick={()=>onChange(o.value)}>{o.label}</button>)}</div>;
}
