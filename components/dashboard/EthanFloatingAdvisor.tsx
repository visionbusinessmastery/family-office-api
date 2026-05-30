"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { apiRequest } from "@/lib/api";
import type { ProductContext } from "@/lib/types";

const AdvisorChat = dynamic(() => import("@/components/dashboard/AdvisorChat"), {
  ssr: false,
  loading: () => (
    <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5 text-sm text-gray-400">
      Ethan se prepare...
    </div>
  ),
});

export default function EthanFloatingAdvisor() {
  const [open, setOpen] = useState(() => {
    if (typeof window === "undefined") return false;
    return sessionStorage.getItem("ethanFloatingOpen") === "true";
  });
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let retryTimer: number | undefined;

    const loadEntitlements = async () => {
      const token = localStorage.getItem("token");
      if (!token) {
        if (cancelled) return;
        setEnabled(false);
        retryTimer = window.setTimeout(loadEntitlements, 800);
        return;
      }

      try {
        const product = await apiRequest<Pick<ProductContext, "entitlements">>(
          "/product/entitlements",
          token
        );
        if (cancelled) return;
        const features = product?.entitlements?.features || [];
        setEnabled(features.includes("ethan_floating_chat"));
      } catch {
        try {
          const product = await apiRequest<Pick<ProductContext, "entitlements">>(
            "/product/context",
            token
          );
          if (cancelled) return;
          const features = product?.entitlements?.features || [];
          setEnabled(features.includes("ethan_floating_chat"));
        } catch {
          if (!cancelled) setEnabled(false);
        }
      }
    };

    loadEntitlements();

    const handleRefresh = () => loadEntitlements();
    window.addEventListener("focus", handleRefresh);
    window.addEventListener("storage", handleRefresh);

    return () => {
      cancelled = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      window.removeEventListener("focus", handleRefresh);
      window.removeEventListener("storage", handleRefresh);
    };
  }, []);

  const toggleOpen = () => {
    setOpen((value) => {
      const next = !value;
      sessionStorage.setItem("ethanFloatingOpen", String(next));
      return next;
    });
  };

  if (!enabled) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex max-w-[calc(100vw-2rem)] flex-col items-end gap-3 sm:bottom-6 sm:right-6">
      {open && (
        <div className="max-h-[78vh] w-[min(420px,calc(100vw-2rem))] overflow-y-auto rounded-2xl border border-white/10 bg-black shadow-2xl shadow-black/50">
          <AdvisorChat compact />
        </div>
      )}

      <button
        type="button"
        onClick={toggleOpen}
        className="group relative overflow-hidden rounded-full border border-[#3fa9f5]/60 bg-[#07111f] px-4 py-3 text-left text-white shadow-2xl shadow-[#3fa9f5]/20 transition hover:-translate-y-0.5 hover:border-[#8bd0ff] hover:shadow-[#3fa9f5]/35 sm:px-5"
        aria-expanded={open}
      >
        <span className="absolute inset-0 bg-[#3fa9f5]/15 opacity-70 blur-xl transition group-hover:opacity-100" />
        <span className="relative flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-full border border-[#8bd0ff]/50 bg-[#3fa9f5] text-sm font-black shadow-lg shadow-[#3fa9f5]/35">
            AI
          </span>
          <span className="hidden leading-tight sm:block">
            <span className="block text-sm font-black">Ethan</span>
            <span className="block text-[11px] font-semibold text-[#8bd0ff]">
              Copilote strategique
            </span>
          </span>
        </span>
      </button>
    </div>
  );
}
