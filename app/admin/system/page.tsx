"use client";

import { useEffect, useState } from "react";
import AuthExperienceShell from "@/components/AuthExperienceShell";
import CockpitBackLink from "@/components/CockpitBackLink";
import { apiRequest } from "@/lib/api";
import { MetricCard, WealthToast } from "@/components/ui/WealthUI";

type Diagnostics = {
  health: {
    status: string;
    checks: Record<string, { status: string; latency_ms?: number; configured?: boolean }>;
  };
  feature_flags: Array<{
    key: string;
    enabled: boolean;
    rollout_percentage: number;
    subscription_min: string;
  }>;
  ethan_costs_7d: Array<{
    plan: string;
    requests: number;
    users: number;
    estimated_cost_usd: number;
    cache_hit_ratio: number;
  }>;
  ethan_models_7d: Array<{
    model: string;
    requests: number;
    estimated_cost_usd: number;
  }>;
};

export default function SystemAdminPage() {
  const [data, setData] = useState<Diagnostics | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      window.location.href = "/login";
      return;
    }

    apiRequest<Diagnostics>("/system/admin/diagnostics", token)
      .then(setData)
      .catch((error) => {
        setToast(error instanceof Error ? error.message : "Diagnostics indisponibles.");
      });
  }, []);

  const degraded = data
    ? Object.values(data.health.checks).filter((check) => check.status !== "ok").length
    : 0;

  return (
    <AuthExperienceShell fullScreen>
      <WealthToast message={toast} type="error" onClose={() => setToast(null)} />
      <main className="relative z-10 mx-auto min-h-screen max-w-6xl px-5 py-24 text-white">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
              System Diagnostics
            </p>
            <h1 className="mt-2 text-3xl font-black sm:text-5xl">
              Readiness production
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-300">
              Sante des dependances, feature flags, cache, Stripe, OpenAI et couts IA.
            </p>
          </div>
          <CockpitBackLink />
        </div>

        {!data ? (
          <div className="rounded-2xl border border-white/10 bg-black/45 p-6 backdrop-blur-xl">
            <div className="h-4 w-56 animate-pulse rounded-full bg-white/10" />
            <div className="mt-5 grid gap-4 sm:grid-cols-4">
              {[0, 1, 2, 3].map((item) => (
                <div key={item} className="h-28 animate-pulse rounded-2xl bg-white/[0.05]" />
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <section className="grid gap-3 sm:grid-cols-4">
              <MetricCard label="Statut systeme" value={data.health.status} tone={data.health.status === "ok" ? "success" : "danger"} />
              <MetricCard label="Dependances degradees" value={degraded} tone={degraded ? "danger" : "success"} />
              <MetricCard label="Feature flags" value={data.feature_flags.length} tone="primary" />
              <MetricCard label="Cout IA 7j" value={`$${data.ethan_costs_7d.reduce((sum, item) => sum + item.estimated_cost_usd, 0).toFixed(4)}`} />
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
                <h2 className="text-2xl font-black">Healthchecks</h2>
                <div className="mt-4 space-y-2">
                  {Object.entries(data.health.checks).map(([key, check]) => (
                    <div key={key} className="flex justify-between rounded-xl bg-white/[0.04] px-4 py-3 text-sm">
                      <span>{key}</span>
                      <span className={check.status === "ok" ? "text-emerald-300" : "text-amber-200"}>
                        {check.status} {check.latency_ms ? `· ${check.latency_ms}ms` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
                <h2 className="text-2xl font-black">Feature flags</h2>
                <div className="mt-4 space-y-2">
                  {data.feature_flags.map((flag) => (
                    <div key={flag.key} className="rounded-xl bg-white/[0.04] px-4 py-3 text-sm">
                      <div className="flex justify-between gap-3">
                        <span>{flag.key}</span>
                        <span className={flag.enabled ? "text-emerald-300" : "text-gray-500"}>
                          {flag.enabled ? "ON" : "OFF"} · {flag.rollout_percentage}%
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-gray-500">Plan min: {flag.subscription_min}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
                <h2 className="text-2xl font-black">IA par plan</h2>
                <div className="mt-4 space-y-2">
                  {data.ethan_costs_7d.map((row) => (
                    <div key={row.plan} className="flex justify-between rounded-xl bg-white/[0.04] px-4 py-3 text-sm">
                      <span>{row.plan || "UNKNOWN"}</span>
                      <span className="text-gray-400">
                        {row.requests} req · ${row.estimated_cost_usd.toFixed(4)} · cache {Math.round(row.cache_hit_ratio * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
                <h2 className="text-2xl font-black">Modeles</h2>
                <div className="mt-4 space-y-2">
                  {data.ethan_models_7d.map((row) => (
                    <div key={row.model} className="flex justify-between rounded-xl bg-white/[0.04] px-4 py-3 text-sm">
                      <span>{row.model || "UNKNOWN"}</span>
                      <span className="text-gray-400">{row.requests} req · ${row.estimated_cost_usd.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </div>
        )}
      </main>
    </AuthExperienceShell>
  );
}
