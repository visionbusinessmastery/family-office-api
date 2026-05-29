"use client";

import { FormEvent, useMemo, useState } from "react";
import { apiRequest } from "@/lib/api";
import type {
  OpportunityIntelligenceData,
  OpportunityUniverse,
} from "@/lib/types";

type OpportunityDiscoveryPanelProps = {
  universe: OpportunityUniverse;
  title: string;
  description: string;
  plan?: string | null;
  token?: string | null;
};

const universeCopy: Record<
  OpportunityUniverse,
  {
    eyebrow: string;
    submit: string;
    defaults: Record<string, string>;
  }
> = {
  real_estate: {
    eyebrow: "Immobilier",
    submit: "Explorer l'immobilier",
    defaults: {
      objective: "investissement locatif",
      estate_type: "ancien",
      city: "Paris",
      country: "France",
      budget_min: "50000",
      budget_max: "250000",
      target_yield: "5",
    },
  },
  investments: {
    eyebrow: "Investissements",
    submit: "Explorer les actifs",
    defaults: {
      asset_classes: "stocks,etf,crypto,commodities",
      strategy: "diversification",
      horizon: "5 ans",
      risk: "medium",
      country: "global",
      sector: "",
    },
  },
  business: {
    eyebrow: "Business",
    submit: "Explorer les opportunités",
    defaults: {
      business_type: "digital business",
      budget: "10000",
      country: "France",
      sector: "",
      ambition: "cashflow",
      risk: "medium",
    },
  },
};

const fieldLabels: Record<string, string> = {
  objective: "Objectif",
  estate_type: "Type",
  city: "Ville",
  country: "Pays",
  budget_min: "Budget min",
  budget_max: "Budget max",
  target_yield: "Rendement cible",
  asset_classes: "Classes d'actifs",
  strategy: "Stratégie",
  horizon: "Horizon",
  risk: "Risque",
  sector: "Secteur",
  business_type: "Type business",
  budget: "Budget",
  ambition: "Ambition",
};

const selectOptions: Record<string, string[]> = {
  objective: [
    "résidence principale",
    "résidence secondaire",
    "investissement locatif",
    "achat/revente",
    "commercial",
  ],
  estate_type: ["ancien", "neuf", "VEFA", "travaux", "enchères"],
  country: ["France", "Canada", "Belgique", "Suisse", "Luxembourg", "Global"],
  asset_classes: [
    "stocks,etf",
    "stocks,etf,crypto,commodities",
    "etf,forex,commodities",
    "crypto,stocks",
  ],
  strategy: ["diversification", "dividendes", "croissance", "value", "défensive"],
  horizon: ["1 an", "3 ans", "5 ans", "10 ans", "20 ans"],
  risk: ["low", "medium", "high"],
  business_type: [
    "digital business",
    "reprise entreprise",
    "fonds de commerce",
    "franchise",
    "startup",
    "side business",
  ],
  ambition: ["cashflow", "croissance", "impact", "acquisition", "transmission"],
};

const formatMoney = (value?: string | number | null) => {
  const number = Number(value);
  if (!Number.isFinite(number) || number === 0) return null;
  return `${new Intl.NumberFormat("fr-FR", {
    maximumFractionDigits: 0,
  }).format(number)} EUR`;
};

const strategyLabel: Record<string, string> = {
  cashflow: "Cashflow",
  capital_appreciation: "Valorisation",
  hybrid: "Hybride",
};

const horizonLabel: Record<string, string> = {
  short: "Court terme",
  medium: "Moyen terme",
  long: "Long terme",
};

const riskLabel: Record<string, string> = {
  low: "Risque faible",
  medium: "Risque modere",
  high: "Risque eleve",
};

const scoreBreakdownLabels: Record<string, string> = {
  return_score: "Retour",
  risk_score: "Risque",
  liquidity_score: "Liquidite",
  diversification_score: "Diversification",
  portfolio_fit_score: "Fit",
  novelty_score: "Nouveaute",
};

const asCriteria = (
  universe: OpportunityUniverse,
  form: Record<string, string>
) => {
  if (universe === "investments") {
    return {
      ...form,
      asset_classes: form.asset_classes
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    };
  }

  return form;
};

export default function OpportunityDiscoveryPanel({
  universe,
  title,
  description,
  plan,
  token,
}: OpportunityDiscoveryPanelProps) {
  const copy = universeCopy[universe];
  const storageKey = `whiteRockOpportunityFilters:${universe}`;
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<Record<string, string>>(() => {
    if (typeof window === "undefined") return copy.defaults;
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? { ...copy.defaults, ...JSON.parse(saved) } : copy.defaults;
    } catch {
      return copy.defaults;
    }
  });
  const [data, setData] = useState<OpportunityIntelligenceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fields = useMemo(() => Object.entries(copy.defaults), [copy.defaults]);

  const handleChange = (key: string, value: string) => {
    setForm((current) => {
      const next = { ...current, [key]: value };
      if (typeof window !== "undefined") {
        localStorage.setItem(storageKey, JSON.stringify(next));
      }
      return next;
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) {
      setError("Session expirée. Reconnecte-toi pour générer les signaux.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiRequest<OpportunityIntelligenceData>(
        "/intelligence/opportunity-intelligence",
        token,
        {
          method: "POST",
          body: JSON.stringify({
            universe,
            criteria: asCriteria(universe, form),
          }),
        }
      );
      setData(response);
      setOpen(false);
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error && err.message.includes("Failed to fetch")
          ? "Connexion API impossible. Vérifie la configuration NEXT_PUBLIC_API_URL et le backend."
          : "Les signaux de cet univers sont indisponibles pour le moment."
      );
    } finally {
      setLoading(false);
    }
  };

  const items = data?.items || [];

  return (
    <section className="rounded-2xl border border-white/10 bg-gradient-to-br from-zinc-950 via-black to-[#07111f] p-5 shadow-2xl">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            {copy.eyebrow}
          </p>
          <h2 className="mt-2 text-2xl font-black text-white">{title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-400">
            {description}
          </p>
          <p className="mt-3 text-xs text-gray-500">
            Plan {plan || data?.plan || "Foundation"}: la profondeur
            s&apos;adapte, mais l&apos;univers reste toujours visible.
          </p>
        </div>
        <button
          onClick={() => setOpen(true)}
          className="rounded-xl bg-[#3fa9f5] px-4 py-2 text-sm font-bold text-white transition hover:bg-[#2588d2]"
        >
          {copy.submit}
        </button>
      </div>

      <div className="sticky top-3 z-20 mt-5 rounded-xl border border-white/10 bg-black/75 p-3 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2 text-xs text-gray-300">
            {fields.slice(0, 4).map(([key]) => (
              <label
                key={key}
                className="flex min-w-[135px] flex-1 items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-2 py-2 sm:flex-none"
              >
                <span className="text-gray-500">{fieldLabels[key] || key.replaceAll("_", " ")}</span>
                {selectOptions[key] ? (
                  <select
                    value={form[key] || ""}
                    onChange={(event) => handleChange(key, event.target.value)}
                    className="min-w-0 flex-1 bg-black/20 text-white outline-none"
                  >
                    {selectOptions[key].map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    value={form[key] || ""}
                    onChange={(event) => handleChange(key, event.target.value)}
                    className="min-w-0 flex-1 bg-transparent text-white outline-none"
                  />
                )}
              </label>
            ))}
          </div>
          <button
            onClick={() => setOpen(true)}
            className="rounded-lg border border-[#3fa9f5]/40 bg-[#3fa9f5]/10 px-3 py-2 text-xs font-bold text-[#8bd0ff] transition hover:bg-[#3fa9f5]/20"
          >
            Filtres avances
          </button>
        </div>
      </div>

      {data?.depth?.message && (
        <div className="mt-5 rounded-xl border border-[#3fa9f5]/20 bg-[#3fa9f5]/10 p-4 text-sm text-blue-100">
          {data.depth.message}
        </div>
      )}

      {error && (
        <div className="mt-5 rounded-xl border border-red-400/20 bg-red-500/10 p-4 text-sm text-red-100">
          {error}
        </div>
      )}

      {items.length > 0 ? (
        <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">
          {items.map((item, index) => {
            const price = formatMoney(item.price);
            const cashflow = formatMoney(item.cashflow_estimate);
            const sourceAction =
              item.universe === "real_estate" ? "Ouvrir la recherche" : "Voir la source";
            const finalScore = item.score?.final_score ?? item.ethan_score ?? 0;
            const breakdown = item.score?.breakdown || {};

            return (
              <article
                key={item.id || `${item.title}-${index}`}
                className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] transition hover:border-[#3fa9f5]/40"
              >
                <div className="h-28 bg-[radial-gradient(circle_at_20%_20%,rgba(63,169,245,0.38),transparent_30%),linear-gradient(135deg,#07111f,#111827_52%,#1f2937)]" />
                <div className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-widest text-gray-500">
                        {item.source || "White Rock"}
                      </p>
                      <h3 className="mt-1 text-lg font-black text-white">
                        {item.title || "Opportunite"}
                      </h3>
                    </div>
                    <span className="rounded-full border border-emerald-300/30 bg-emerald-300/10 px-3 py-1 text-xs font-bold text-emerald-200">
                      {Number(finalScore || 0)}/100
                    </span>
                  </div>

                  <p className="mt-3 text-sm leading-relaxed text-gray-400">
                    {item.description}
                  </p>

                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                    {price && (
                      <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                        <p className="text-gray-500">Valeur</p>
                        <p className="mt-1 font-bold text-white">{price}</p>
                      </div>
                    )}
                    {item.yield_percent && (
                      <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                        <p className="text-gray-500">Rendement</p>
                        <p className="mt-1 font-bold text-white">
                          {item.yield_percent}%
                        </p>
                      </div>
                    )}
                    {cashflow && (
                      <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                        <p className="text-gray-500">Cashflow</p>
                        <p className="mt-1 font-bold text-white">{cashflow}</p>
                      </div>
                    )}
                    {item.volatility && (
                      <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                        <p className="text-gray-500">Volatilite</p>
                        <p className="mt-1 font-bold text-white">
                          {item.volatility}
                        </p>
                      </div>
                    )}
                    {item.expected_return && (
                      <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                        <p className="text-gray-500">Potentiel</p>
                        <p className="mt-1 font-bold text-white">{item.expected_return}</p>
                      </div>
                    )}
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2 text-xs">
                    {item.strategy_type && (
                      <span className="rounded-full border border-[#3fa9f5]/25 bg-[#3fa9f5]/10 px-3 py-1 font-bold text-[#8bd0ff]">
                        {strategyLabel[item.strategy_type] || item.strategy_type}
                      </span>
                    )}
                    {item.investment_horizon && (
                      <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-gray-300">
                        {horizonLabel[item.investment_horizon] || item.investment_horizon}
                      </span>
                    )}
                    {item.risk_level && (
                      <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-amber-100">
                        {riskLabel[item.risk_level] || item.risk_level}
                      </span>
                    )}
                    {item.location && (
                      <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-gray-300">
                        {item.location}
                      </span>
                    )}
                  </div>

                  {Object.keys(breakdown).length > 0 && (
                    <div className="mt-4 rounded-xl border border-white/10 bg-black/25 p-3">
                      <p className="text-xs font-bold uppercase tracking-widest text-gray-500">
                        Scoring multi-objectifs
                      </p>
                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                        {Object.entries(breakdown)
                          .filter(([key]) => key !== "momentum_score")
                          .map(([key, value]) => (
                            <div key={key} className="flex items-center justify-between gap-2 rounded-lg bg-white/[0.04] px-2 py-1.5">
                              <span className="text-gray-400">
                                {scoreBreakdownLabels[key] || key}
                              </span>
                              <span className="font-bold text-white">{Number(value || 0)}/100</span>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-4 space-y-3">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-widest text-emerald-200">
                        Points forts
                      </p>
                      <ul className="mt-2 space-y-1 text-sm text-gray-300">
                        {(item.strengths || []).slice(0, 2).map((strength) => (
                          <li key={strength}>{strength}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs font-bold uppercase tracking-widest text-amber-200">
                        Vigilance
                      </p>
                      <ul className="mt-2 space-y-1 text-sm text-gray-300">
                        {(item.risks || []).slice(0, 2).map((risk) => (
                          <li key={risk}>{risk}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <p className="mt-4 rounded-xl border border-white/10 bg-black/30 p-3 text-sm leading-relaxed text-gray-300">
                    {item.next_step}
                  </p>
                  {(item.explanation || item.why_this_is_new_vs_previous) && (
                    <div className="mt-3 rounded-xl border border-white/10 bg-white/[0.03] p-3 text-sm leading-relaxed text-gray-300">
                      {item.explanation && <p>{item.explanation}</p>}
                      {item.why_this_is_new_vs_previous && (
                        <p className="mt-2 text-gray-400">{item.why_this_is_new_vs_previous}</p>
                      )}
                    </div>
                  )}
                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-3 inline-flex w-full items-center justify-center rounded-xl border border-[#3fa9f5]/35 bg-[#3fa9f5]/10 px-4 py-3 text-sm font-bold text-[#8bd0ff] transition hover:border-[#3fa9f5]/60 hover:bg-[#3fa9f5]/20"
                    >
                      {sourceAction}
                    </a>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-gray-400">
          Lance une recherche pour obtenir jusqu&apos;à 6 signaux priorises par le backend.
        </div>
      )}

      {data?.market_signal?.headline && (
        <div className="mt-5 rounded-xl border border-white/10 bg-black/25 p-4 text-sm text-gray-300">
          <span className="font-bold text-white">Signal marche:</span>{" "}
          {data.market_signal.headline}
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-xl">
          <form
            onSubmit={handleSubmit}
            className="fade-in max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-white/10 bg-zinc-950 p-5 shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                  Filtres de signaux
                </p>
                <h3 className="mt-2 text-2xl font-black text-white">
                  {title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-400">
                  Renseigne quelques critères. Le backend renvoie des signaux:
                  potentiel, risque, coherence et donnees disponibles.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-xl border border-white/10 px-3 py-2 text-sm text-gray-300"
              >
                Fermer
              </button>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
              {fields.map(([key]) => (
                <label key={key} className="text-sm">
                  <span className="block text-xs uppercase tracking-widest text-gray-500">
                    {fieldLabels[key] || key.replaceAll("_", " ")}
                  </span>
                  {selectOptions[key] ? (
                    <select
                      value={form[key] || ""}
                      onChange={(event) => handleChange(key, event.target.value)}
                      className="mt-2 w-full rounded-xl border border-white/10 bg-black/35 px-3 py-3 text-white outline-none transition focus:border-[#3fa9f5]/60"
                    >
                      {selectOptions[key].map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      value={form[key] || ""}
                      onChange={(event) => handleChange(key, event.target.value)}
                      className="mt-2 w-full rounded-xl border border-white/10 bg-black/35 px-3 py-3 text-white outline-none transition focus:border-[#3fa9f5]/60"
                    />
                  )}
                </label>
              ))}
            </div>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs leading-relaxed text-gray-500">
                Les résultats sont limités, cachés et régénérés seulement si tes
                critères ou ton patrimoine évoluent.
              </p>
              <button
                type="submit"
                disabled={loading}
                className="rounded-xl bg-[#3fa9f5] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#2588d2] disabled:opacity-60"
              >
                {loading ? "Analyse en cours..." : "Générer les signaux"}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}
