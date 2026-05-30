"use client";

import type { FinanceOverviewData, ProductContext } from "@/lib/types";

const money = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
});

const n = (value?: number | string | null) => Number(value || 0);

type HomeExecutiveSummaryProps = {
  product?: ProductContext | null;
  financeOverview?: FinanceOverviewData | null;
  plan?: string | null;
  level?: string | null;
};

export default function HomeExecutiveSummary({
  product,
  financeOverview,
  plan,
  level,
}: HomeExecutiveSummaryProps) {
  const wealth = product?.wealth_intelligence;
  const future = product?.future_intelligence;
  const position = future?.position;
  const decision = product?.decision_intelligence;
  const cashflow = n(financeOverview?.totals?.cashflow);
  const visibleWealth =
    n(product?.data_profile?.current_wealth) || n(wealth?.visible_wealth);
  const mainInsight =
    wealth?.memorable_insight ||
    wealth?.headline ||
    wealth?.gravity_reading ||
    "White Rock consolide tes donnees pour faire ressortir la prochaine decision utile.";
  const nextAction =
    decision?.next_action ||
    decision?.decision?.action ||
    decision?.decision?.description ||
    product?.strategic_brief?.next_action ||
    "Garde tes donnees a jour pour affiner la prochaine action utile.";
  const mainSignal =
    decision?.risk?.title ||
    decision?.opportunity?.title ||
    product?.strategic_brief?.main_risk ||
    product?.strategic_brief?.opportunity ||
    "Aucun signal prioritaire a traiter immediatement.";
  const signalDetail =
    decision?.risk?.description ||
    decision?.opportunity?.description ||
    decision?.risk?.action ||
    decision?.opportunity?.action ||
    "";
  const progress = Math.min(100, n(position?.progress_percent));

  return (
    <section className="space-y-5">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-[#3fa9f5]/20 bg-[#3fa9f5]/10 p-5">
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            Patrimoine suivi
          </p>
          <p className="mt-2 text-3xl font-black text-white">
            {money.format(visibleWealth)} EUR
          </p>
        </div>
        <div
          className={`rounded-2xl border p-5 ${
            cashflow >= 0
              ? "border-emerald-400/20 bg-emerald-400/10"
              : "border-red-400/20 bg-red-400/10"
          }`}
        >
          <p className="text-xs uppercase tracking-widest text-gray-400">
            Cashflow mensuel
          </p>
          <p
            className={`mt-2 text-3xl font-black ${
              cashflow >= 0 ? "text-emerald-300" : "text-red-300"
            }`}
          >
            {cashflow >= 0 ? "+" : ""}
            {money.format(cashflow)} EUR
          </p>
        </div>
        <div className="rounded-2xl border border-[#f7d154]/25 bg-[#f7d154]/10 p-5">
          <p className="text-xs uppercase tracking-widest text-[#f7d154]">
            Statut White Rock
          </p>
          <p className="mt-2 text-2xl font-black text-white">
            {level || product?.progression?.level || plan || "A confirmer"}
          </p>
          <p className="mt-1 text-sm text-gray-400">{plan || product?.plan}</p>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
        <p className="text-xs uppercase tracking-widest text-[#f7d154]">
          Insight du jour
        </p>
        <p className="mt-3 max-w-4xl text-xl font-black leading-snug text-white">
          {mainInsight}
        </p>
      </div>

      <div className="rounded-2xl border border-[#3fa9f5]/20 bg-zinc-950 p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
              Projection simple
            </p>
            <h2 className="mt-1 text-2xl font-black text-white">
              {position?.destination?.label || "Prochain palier"}
            </h2>
          </div>
          <p className="text-sm text-gray-400">
            {position?.estimated_label || future?.time_to_next || "Date a confirmer"}
          </p>
        </div>
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#3fa9f5] via-emerald-400 to-[#f7d154]"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
          <p className="rounded-xl border border-white/10 bg-white/[0.04] p-3 text-gray-300">
            Position:{" "}
            <span className="font-bold text-white">
              {money.format(n(position?.current) || visibleWealth)} EUR
            </span>
          </p>
          <p className="rounded-xl border border-white/10 bg-white/[0.04] p-3 text-gray-300">
            Distance:{" "}
            <span className="font-bold text-white">
              {money.format(n(position?.distance_remaining))} EUR
            </span>
          </p>
          <p className="rounded-xl border border-white/10 bg-white/[0.04] p-3 text-gray-300">
            Vitesse:{" "}
            <span className="font-bold text-white">
              {money.format(n(position?.monthly_velocity))} EUR/mois
            </span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-5">
          <p className="text-xs uppercase tracking-widest text-emerald-300">
            Prochaine action
          </p>
          <p className="mt-3 text-lg font-black leading-snug text-white">
            {nextAction}
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
          <p className="text-xs uppercase tracking-widest text-gray-500">
            Signal prioritaire
          </p>
          <p className="mt-3 text-lg font-black leading-snug text-white">
            {mainSignal}
          </p>
          {signalDetail ? (
            <p className="mt-2 text-sm leading-relaxed text-gray-400">
              {signalDetail}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
