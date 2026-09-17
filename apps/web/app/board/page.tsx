"use client";

import AppShell from "@/components/AppShell";
import Board from "@/components/Board";
import { useAuth } from "@/lib/useAuth";

export default function BoardPage() {
  const { user, loading } = useAuth();
  if (loading || !user) return null;

  return (
    <AppShell>
      <Board />
    </AppShell>
  );
}
