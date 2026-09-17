"use client";

import AppShell from "@/components/AppShell";
import { useAuth } from "@/lib/useAuth";

export default function FilesPage() {
  const { user, loading } = useAuth();
  if (loading || !user) return null;

  return (
    <AppShell>
      <h1 className="serif text-4xl mb-4">Файлы</h1>
      <p className="text-[var(--stone)]">Раздел появится на шаге 4 — приём файлов и извлечение задач.</p>
    </AppShell>
  );
}
