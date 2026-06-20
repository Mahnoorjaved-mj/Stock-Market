import { useEffect, useRef, useState } from 'react'
import { Bell } from 'lucide-react'
import { useApp } from '../context/context'

export default function NotificationBell() {
  const { getNotifications, readAllNotifications } = useApp()
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState([])
  const [unread, setUnread] = useState(0)
  const ref = useRef(null)

  const load = async () => {
    try {
      const res = await getNotifications()
      setItems(res.items || [])
      setUnread(res.unread || 0)
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 60000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const handleOpen = async () => {
    const next = !open
    setOpen(next)
    if (next && unread > 0) {
      await readAllNotifications()
      setUnread(0)
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={handleOpen}
        className="relative rounded p-2 text-secondary hover:bg-surface-hover hover:text-primary"
      >
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-down px-1 text-[10px] font-semibold text-white">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 ss-card z-50 max-h-96 overflow-y-auto shadow-lg">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-primary">
            Notifications
          </div>
          {items.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-tertiary">No notifications</div>
          ) : (
            items.map((n) => (
              <div key={n.id} className="border-b border-subtle px-4 py-2.5">
                <div className="text-sm font-medium text-primary">{n.title}</div>
                {n.body && <div className="text-xs text-secondary">{n.body}</div>}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
