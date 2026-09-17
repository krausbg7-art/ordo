"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post("/auth/register", { email, password });
      router.push("/today");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось зарегистрироваться");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm bg-white border border-[var(--line2)] rounded-2xl p-8 flex flex-col gap-4">
        <h1 className="serif text-3xl mb-2">Регистрация</h1>
        <label className="text-sm text-[var(--stone)] flex flex-col gap-1">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-[var(--line2)] rounded-xl px-3 py-2.5 text-base"
          />
        </label>
        <label className="text-sm text-[var(--stone)] flex flex-col gap-1">
          Пароль (минимум 8 символов)
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border border-[var(--line2)] rounded-xl px-3 py-2.5 text-base"
          />
        </label>
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="bg-ink text-cream rounded-xl px-4 py-2.5 font-semibold disabled:opacity-60"
        >
          Создать аккаунт
        </button>
        <p className="text-sm text-[var(--stone)] text-center">
          Уже есть аккаунт?{" "}
          <Link href="/login" className="text-[var(--brass-ink)]">
            Войти
          </Link>
        </p>
      </form>
    </div>
  );
}
