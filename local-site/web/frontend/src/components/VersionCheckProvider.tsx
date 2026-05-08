"use client";

import { useState, useEffect, ReactNode } from "react";
import axios from "axios";
import UpdateScreen from "./UpdateScreen";

interface VersionCheckProviderProps {
  children: ReactNode;
}

interface VersionCheckResponse {
  current_version: string;
  current_date: string;
  update_available: boolean;
  latest_version?: string | null;
  download_url?: string | null;
  mandatory?: boolean | null;
  release_notes?: string | null;
}

export default function VersionCheckProvider({ children }: VersionCheckProviderProps) {
  const [updateInfo, setUpdateInfo] = useState<VersionCheckResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkVersion();
  }, []);

  async function checkVersion() {
    try {
      const { data } = await axios.get<VersionCheckResponse>("/api/version");
      if (data.update_available && data.mandatory) {
        setUpdateInfo(data);
      }
    } catch {
      // Ignore errors — start normally
    } finally {
      setLoading(false);
    }
  }

  if (loading) return null;

  if (updateInfo && updateInfo.download_url && updateInfo.latest_version) {
    return (
      <UpdateScreen
        downloadUrl={updateInfo.download_url}
        targetVersion={updateInfo.latest_version}
        releaseNotes={updateInfo.release_notes}
      />
    );
  }

  return <>{children}</>;
}
