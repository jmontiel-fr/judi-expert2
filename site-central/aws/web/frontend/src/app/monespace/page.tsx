"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function MonEspacePage() {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!user) {
      router.replace("/connexion");
    } else {
      router.replace("/monespace/profil");
    }
  }, [user, router]);

  return null;
}
