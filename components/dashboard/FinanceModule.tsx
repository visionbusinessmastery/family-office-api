"use client";

import type { FinanceOverviewData } from "@/lib/types";

const money = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
});

const n = (value?: number | string | null) => Number(value || 0);

type FinanceModuleProps = {
  overview?: FinanceOverviewData | null;
};

export default function FinanceModule({ overview }: FinanceModuleProps) {
  const totals = overview?.totals || {};
  const ratios = overview?.ratios || {};
  const cashflow = n(totals.cashflow);

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
        <p className="text-xs font-bold uppercase tracking-widest text-emerald-300">
          Cashflow mensuel
        </p>
        <h3
          className={`mt-2 text-4xl font-black ${
            cashflow >= 0 ? "text-emerald-300" : "text-red-300"
          }`}
        >
          {cashflow >= 0 ? "+" : ""}
          {money.format(cashflow)} EUR
        </h3>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-gray-300">
          Calcul base sur les revenus et les charges renseignes ci-dessous.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-[#3fa9f5]/20 bg-[#3fa9f5]/10 p-5">
          <p className="mb-2 text-sm text-gray-400">Revenus suivis</p>
          <h3 className="text-2xl font-black text-[#3fa9f5]">
            {money.format(n(totals.income))} EUR
          </h3>
        </div>

        <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-5">
          <p className="mb-2 text-sm text-gray-400">Charges suivies</p>
          <h3 className="text-2xl font-black text-red-300">
            {money.format(n(totals.expenses))} EUR
          </h3>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-widest text-gray-500">
            Reste a vivre
          </p>
          <p className="mt-2 text-xl font-black text-white">
            {money.format(n(totals.living_margin))} EUR
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-widest text-gray-500">
            Taux d'epargne suivi
          </p>
          <p className="mt-2 text-xl font-black text-white">
            {n(ratios.savings_rate).toFixed(1)}%
          </p>
        </div>
      </div>
    </div>
  );
}
