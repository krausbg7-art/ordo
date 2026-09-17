"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AppShell from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { CalendarAccountOut, CalendarEventOut } from "@/lib/types";

export default function CalendarsPage() {
  const { user, loading } = useAuth();
  const [accounts, setAccounts] = useState<CalendarAccountOut[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [events, setEvents] = useState<CalendarEventOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showCaldavForm, setShowCaldavForm] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refreshAccounts = useCallback(async () => {
    const list = await api.get<CalendarAccountOut[]>("/calendars");
    setAccounts(list);
    if (!selectedId && list.length > 0) setSelectedId(list[0].id);
  }, [selectedId]);

  useEffect(() => {
    if (user) refreshAccounts();
  }, [user, refreshAccounts]);

  useEffect(() => {
    if (!selectedId) return;
    api.get<CalendarEventOut[]>(`/calendars/${selectedId}/events`).then(setEvents);
  }, [selectedId]);

  async function onIcsFile(file: File) {
    setError(null);
    try {
      await api.uploadField("/calendars/ics-import", "file", file);
      await refreshAccounts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось импортировать .ics");
    }
  }

  async function toggleEnabled(account: CalendarAccountOut) {
    await api.patch(`/calendars/${account.id}`, { enabled: !account.enabled });
    setAccounts((prev) => prev.map((a) => (a.id === account.id ? { ...a, enabled: !a.enabled } : a)));
  }

  async function syncNow(account: CalendarAccountOut) {
    await api.post(`/calendars/${account.id}/sync`);
  }

  async function eventToTask(eventId: string) {
    await api.post(`/calendar-events/${eventId}/to-task`);
  }

  async function addAll() {
    if (!selectedId) return;
    await api.post(`/calendars/${selectedId}/events/add-all`);
  }

  async function addCaldav(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const formData = new FormData(e.currentTarget);
    try {
      await api.post("/calendars", {
        kind: "caldav",
        name: formData.get("name"),
        url: formData.get("url"),
        username: formData.get("username"),
        password: formData.get("password"),
      });
      setShowCaldavForm(false);
      await refreshAccounts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось подключить календарь");
    }
  }

  if (loading || !user) return null;

  return (
    <AppShell>
      <h1 className="serif text-4xl mb-4">Календари</h1>
      {error && <p className="text-sm text-red-700 mb-3">{error}</p>}

      <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-5">
        <div className="bg-cream border border-[var(--line)] rounded-2xl p-4 flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            {accounts.map((a) => (
              <button
                key={a.id}
                onClick={() => setSelectedId(a.id)}
                className={`text-left rounded-xl px-3 py-2 text-sm ${
                  selectedId === a.id ? "bg-ink text-cream" : "hover:bg-[var(--linen)]"
                }`}
              >
                {a.name} {!a.enabled && "· выкл"}
              </button>
            ))}
          </div>

          <button
            onClick={() => fileInputRef.current?.click()}
            className="border border-dashed border-[var(--line2)] rounded-xl px-3 py-2 text-sm text-[var(--stone)]"
          >
            Импорт .ics
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".ics,text/calendar"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onIcsFile(e.target.files[0])}
          />

          <button
            onClick={() => setShowCaldavForm((v) => !v)}
            className="border border-[var(--line2)] rounded-xl px-3 py-2 text-sm bg-white"
          >
            + CalDAV (Яндекс, iCloud)
          </button>

          {showCaldavForm && (
            <form onSubmit={addCaldav} className="flex flex-col gap-2 bg-white border border-[var(--line)] rounded-xl p-3">
              <input name="name" placeholder="Название" required className="border border-[var(--line2)] rounded-lg px-2 py-1.5 text-sm" />
              <input name="url" placeholder="URL CalDAV-сервера" required className="border border-[var(--line2)] rounded-lg px-2 py-1.5 text-sm" />
              <input name="username" placeholder="Логин" required className="border border-[var(--line2)] rounded-lg px-2 py-1.5 text-sm" />
              <input name="password" type="password" placeholder="Пароль приложения" required className="border border-[var(--line2)] rounded-lg px-2 py-1.5 text-sm" />
              <button type="submit" className="bg-ink text-cream rounded-lg px-3 py-1.5 text-sm">
                Подключить
              </button>
            </form>
          )}
        </div>

        <div>
          {selectedId && accounts.find((a) => a.id === selectedId) && (
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-sm text-[var(--stone)]">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={accounts.find((a) => a.id === selectedId)!.enabled}
                    onChange={() => toggleEnabled(accounts.find((a) => a.id === selectedId)!)}
                  />
                  включён
                </label>
                {accounts.find((a) => a.id === selectedId)!.kind === "caldav" && (
                  <button
                    onClick={() => syncNow(accounts.find((a) => a.id === selectedId)!)}
                    className="border border-[var(--line2)] rounded-lg px-3 py-1.5 bg-white"
                  >
                    Синхронизировать
                  </button>
                )}
              </div>
              <button onClick={addAll} className="bg-ink text-cream rounded-lg px-4 py-2 text-sm font-semibold">
                Добавить все
              </button>
            </div>
          )}

          <div className="flex items-center gap-2 text-xs text-[var(--stone)] mb-4">
            <span className="px-2 py-0.5 rounded-full bg-[var(--linen)]">скоро</span>
            <span>Обратная синхронизация — срок задачи будет переносить событие в календарь (TODO)</span>
          </div>

          {events.length === 0 ? (
            <p className="text-[var(--stone)]">Событий пока нет.</p>
          ) : (
            <div className="flex flex-col divide-y divide-[var(--line)]">
              {events.map((ev) => (
                <div key={ev.id} className="flex items-center gap-4 py-3">
                  <div className="serif text-xl w-16 flex-shrink-0">
                    {new Date(ev.start_at).toLocaleDateString("ru-RU", { day: "2-digit", month: "short" })}
                  </div>
                  <div className="flex-1 min-w-0">
                    <b className="block text-sm font-semibold">{ev.title}</b>
                    {ev.description && <span className="text-xs text-[var(--stone)]">{ev.description}</span>}
                  </div>
                  <button
                    onClick={() => eventToTask(ev.id)}
                    className="text-xs border border-[var(--line2)] rounded-lg px-3 py-1.5 bg-white whitespace-nowrap"
                  >
                    В задачи
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
