"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { UserOut } from "@/lib/types";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    api
      .get<UserOut>("/auth/me")
      .then(() => router.replace("/today"))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
      });
  }, [router]);

  return null;
}
