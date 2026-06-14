import { useEffect, useState } from 'react';

// Lightweight toast store (no provider/prop-drilling) — call toast.success(...)
// from anywhere; <ToastContainer /> renders the stack.
export type ToastType = 'success' | 'error' | 'info';
export type ToastItem = { id: number; type: ToastType; message: string };

let counter = 0;
let items: ToastItem[] = [];
const listeners = new Set<(items: ToastItem[]) => void>();

function emit() {
  listeners.forEach((l) => l(items));
}

function dismiss(id: number) {
  items = items.filter((t) => t.id !== id);
  emit();
}

function push(type: ToastType, message: string) {
  const id = ++counter;
  items = [...items, { id, type, message }];
  emit();
  window.setTimeout(() => dismiss(id), type === 'error' ? 6500 : 3500);
}

export const toast = {
  success: (message: string) => push('success', message),
  error: (message: string) => push('error', message),
  info: (message: string) => push('info', message),
};

export function useToasts() {
  const [current, setCurrent] = useState<ToastItem[]>(items);
  useEffect(() => {
    listeners.add(setCurrent);
    return () => {
      listeners.delete(setCurrent);
    };
  }, []);
  return { toasts: current, dismiss };
}

const ICONS: Record<ToastType, string> = { success: '✓', error: '!', info: 'i' };

export function ToastContainer() {
  const { toasts, dismiss: drop } = useToasts();
  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {toasts.map((t) => (
        <button key={t.id} className={`toast toast-${t.type}`} onClick={() => drop(t.id)} title="Dismiss">
          <span className="toast-icon">{ICONS[t.type]}</span>
          <span className="toast-msg">{t.message}</span>
        </button>
      ))}
    </div>
  );
}
