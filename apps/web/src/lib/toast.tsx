/** Minimal toast system: bottom-right stack, auto-dismiss, screen-reader polite. */

import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react'

interface Toast {
  id: number
  text: string
  kind: 'ok' | 'danger'
}

const ToastContext = createContext<(text: string, kind?: Toast['kind']) => void>(() => {})

export const useToast = () => useContext(ToastContext)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const push = useCallback((text: string, kind: Toast['kind'] = 'ok') => {
    const id = nextId.current++
    setToasts((list) => [...list, { id, text, kind }])
    window.setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 3500)
  }, [])

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed bottom-5 right-5 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} role="status"
               className={`panel pointer-events-auto flex items-center gap-2 px-4 py-2.5 text-sm shadow-lift ${
                 t.kind === 'ok' ? 'text-mist-100' : 'border-danger/40 text-danger'}`}>
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${t.kind === 'ok' ? 'bg-ok' : 'bg-danger'}`} />
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
