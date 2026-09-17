"use client";

import AppShell from "@/components/AppShell";
import { useAuth } from "@/lib/useAuth";

export default function CalendarsPage() {
  const { user, loading } = useAuth();
  if (loading || !user) return null;

  return (
    <AppShell>
      <h1 className="serif text-4xl mb-4">Календари</h1>
      <p className="text-[var(--stone)]">Раздел появится на шаге 5 — импорт и синхронизация календарей.</p>
    </AppShell>
  );
}
