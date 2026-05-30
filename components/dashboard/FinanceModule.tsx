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
          {overview?.reading ||
            "Ajoute tes revenus et charges pour obtenir une lecture fiable de ta marge de liberte mensuelle."}
        </p>
        {overview?.priority && (
          <p className="mt-3 rounded-xl border border-amber-300/20 bg-amber-300/10 p-3 text-sm text-amber-100">
            {overview.priority}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
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

        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-5">
          <p className="mb-2 text-sm text-gray-400">Patrimoine liquide</p>
          <h3 className="text-2xl font-black text-emerald-300">
            {money.format(n(totals.savings))} EUR
          </h3>
          <p className="mt-2 text-xs text-gray-400">
            {n(ratios.liquid_months).toFixed(1)} mois de charges
          </p>
        </div>

        <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-5">
          <p className="mb-2 text-sm text-gray-400">Dette totale</p>
          <h3 className="text-2xl font-black text-amber-200">
            {money.format(n(totals.debt))} EUR
          </h3>
          <p className="mt-2 text-xs text-gray-400">
            Ratio dette / revenu {n(ratios.debt_to_income).toFixed(2)}x
          </p>
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
            Taux de marge
          </p>
          <p className="mt-2 text-xl font-black text-white">
            {n(ratios.savings_rate).toFixed(1)}%
          </p>
        </div>
      </div>
    </div>
  );
}
