"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/today", label: "Сегодня" },
  { href: "/board", label: "Задачи" },
  { href: "/files", label: "Файлы" },
  { href: "/calendars", label: "Календари" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  async function logout() {
    await api.post("/auth/logout");
    router.replace("/login");
  }

  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-[220px_1fr]">
      <aside className="hidden md:flex flex-col gap-1 bg-cream border-r border-[var(--line)] p-4">
        <div className="serif text-2xl tracking-wide px-2 pb-6">ordo</div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-xl px-3 py-2.5 text-sm ${
                  active ? "bg-ink text-cream" : "text-[var(--soft)] hover:bg-[var(--linen)]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <button
          onClick={logout}
          className="mt-auto rounded-xl px-3 py-2.5 text-sm text-left text-[var(--soft)] hover:bg-[var(--linen)]"
        >
          Выйти
        </button>
      </aside>

      <nav className="md:hidden flex overflow-x-auto border-b border-[var(--line)] bg-cream sticky top-0 z-10">
        {NAV_ITEMS.map((item) => {
          const active = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex-1 min-w-[80px] text-center px-3 py-3 text-xs ${
                active ? "text-ink font-bold" : "text-[var(--soft)]"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <main className="p-6 md:p-8 min-w-0">{children}</main>
    </div>
  );
}
