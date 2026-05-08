"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function MonEspacePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/connexion");
    } else {
      router.replace("/monespace/profil");
    }
  }, [user, loading, router]);

  return null;
}
