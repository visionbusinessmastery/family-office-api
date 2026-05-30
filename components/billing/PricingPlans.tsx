"use client";

import { useState } from "react";
import CockpitBackLink from "@/components/CockpitBackLink";
import { apiRequest } from "@/lib/api";

type BillingInterval = "monthly" | "yearly";

type Plan = {
  id: "gold" | "elite" | "liberty" | "legacy";
  name: string;
  subtitle: string;
  rank: string;
  badge: string;
  altBadge: string;
  transformation: string;
  unlock: string;
  includes: string;
  price: Record<BillingInterval, string>;
  priceNote: Record<BillingInterval, string>;
  founderPrice: Record<BillingInterval, string>;
  founderNote: Record<BillingInterval, string>;
  tone: string;
  glow: string;
  cta: string;
  capabilityGroups: Array<{
    label: string;
    items: string[];
  }>;
};

type PricingPlansProps = {
  mode: "standard" | "founder";
};

const ladder = [
  { label: "FREE", role: "Decouverte", tone: "border-white/10 bg-white/[0.03] text-gray-500" },
  { label: "GOLD", role: "Trajectoire", tone: "border-[#3fa9f5]/25 bg-[#3fa9f5]/10 text-[#8bd0ff]" },
  { label: "ELITE", role: "Optimisation", tone: "border-emerald-300/45 bg-emerald-300/10 text-emerald-100" },
  { label: "LIBERTY", role: "Arbitrages", tone: "border-amber-300/50 bg-amber-300/[0.12] text-amber-100" },
  { label: "LEGACY", role: "Dynasty Office", tone: "border-yellow-300/60 bg-yellow-300/[0.16] text-yellow-100" },
];

const plans: Plan[] = [
  {
    id: "gold",
    name: "Gold",
    subtitle: "Trajectoire patrimoniale active",
    rank: "Niveau 1",
    badge: "Growth Layer",
    altBadge: "Ethan flottant",
    transformation: "Comprendre ou vous en etes, ou vous allez et quoi faire maintenant",
    unlock: "Patrimoine activable + Future Intelligence + Decision Intelligence",
    includes: "Inclut FREE",
    price: {
      monthly: "29 EUR",
      yearly: "290 EUR",
    },
    priceNote: {
      monthly: "par mois",
      yearly: "par an",
    },
    founderPrice: {
      monthly: "19 EUR",
      yearly: "190 EUR",
    },
    founderNote: {
      monthly: "par mois founder",
      yearly: "par an founder",
    },
    tone: "border-[#3fa9f5]/45 bg-[#3fa9f5]/10",
    glow: "from-[#3fa9f5]/18 via-transparent to-transparent",
    cta: "Debloquer Gold",
    capabilityGroups: [
      {
        label: "Future Intelligence",
        items: ["20 assets maximum", "Patrimoine visible et activable", "Wealth Narrative simple", "Wealth Map", "Projection 10 ans", "Film du futur"],
      },
      {
        label: "Decision & solidite",
        items: ["Ethan flottant Gold+", "Reconciliation profil par confirmation", "Action utile", "Risque principal", "Opportunite principale", "Scorecard et stress tests simples"],
      },
    ],
  },
  {
    id: "elite",
    name: "Elite",
    subtitle: "Wealth Operating System",
    rank: "Niveau 2",
    badge: "Strategic OS",
    altBadge: "Wealth OS",
    transformation: "Optimiser votre trajectoire au lieu de seulement la suivre",
    unlock: "Family Office CEO + simulations avancees",
    includes: "Tout GOLD inclus",
    price: {
      monthly: "79 EUR",
      yearly: "790 EUR",
    },
    priceNote: {
      monthly: "par mois",
      yearly: "par an",
    },
    founderPrice: {
      monthly: "49 EUR",
      yearly: "490 EUR",
    },
    founderNote: {
      monthly: "par mois founder",
      yearly: "par an founder",
    },
    tone: "border-emerald-300/40 bg-emerald-300/10 shadow-lg shadow-emerald-400/10",
    glow: "from-emerald-300/24 via-[#3fa9f5]/10 to-transparent",
    cta: "Passer Elite",
    capabilityGroups: [
      {
        label: "Strategic Intelligence",
        items: ["30 assets maximum", "Family Office CEO", "Burn rate", "Marge mensuelle", "Runway", "Lecture operationnelle"],
      },
      {
        label: "Family Office Intelligence",
        items: ["Wealth Narrative enrichi", "Simulations multi-scenarios", "Stress tests avances", "Detecteur de dependances", "Coffre documentaire patrimonial", "Graphiques par rubrique"],
      },
    ],
  },
  {
    id: "liberty",
    name: "Liberty",
    subtitle: "Freedom Engine",
    rank: "Niveau 3",
    badge: "Family Office",
    altBadge: "Private Access",
    transformation: "Prendre de meilleures decisions patrimoniales avec une logique Family Office",
    unlock: "Arbitrages Family Office + objectifs avances",
    includes: "Tout ELITE inclus",
    price: {
      monthly: "149 EUR",
      yearly: "1490 EUR",
    },
    priceNote: {
      monthly: "par mois",
      yearly: "par an",
    },
    founderPrice: {
      monthly: "99 EUR",
      yearly: "990 EUR",
    },
    founderNote: {
      monthly: "par mois founder",
      yearly: "par an founder",
    },
    tone: "border-amber-300/45 bg-amber-300/12",
    glow: "from-amber-300/30 via-orange-300/12 to-transparent",
    cta: "Activer Liberty",
    capabilityGroups: [
      {
        label: "Family Office personnel",
        items: ["50 assets maximum", "Family Office Mode complet", "Comptes enfants", "Multi-objectifs", "Probabilites d'atteinte", "Scenarios de vie avances"],
      },
      {
        label: "Architecture patrimoniale",
        items: ["Family Office Board", "CFO View", "Investor View", "Entrepreneur View", "Family View", "Priorites d'allocation"],
      },
    ],
  },
  {
    id: "legacy",
    name: "Legacy",
    subtitle: "Dynasty Office",
    rank: "Niveau 4",
    badge: "Dynasty Grade",
    altBadge: "Dynasty Office",
    transformation: "Organiser la protection, la transmission et la gouvernance familiale",
    unlock: "Unlock Dynasty Infrastructure",
    includes: "Tout LIBERTY inclus",
    price: {
      monthly: "399 EUR",
      yearly: "3990 EUR",
    },
    priceNote: {
      monthly: "par mois",
      yearly: "par an",
    },
    founderPrice: {
      monthly: "299 EUR",
      yearly: "2990 EUR",
    },
    founderNote: {
      monthly: "par mois founder",
      yearly: "par an founder",
    },
    tone: "border-yellow-300/55 bg-yellow-300/14",
    glow: "from-yellow-300/36 via-amber-300/20 to-orange-300/8",
    cta: "Entrer Legacy",
    capabilityGroups: [
      {
        label: "Dynasty Layer",
        items: ["Assets illimites", "Projection 30 ans", "Transmission familiale", "Vision generationnelle", "Family Vault", "Heirs mode", "Protection layer"],
      },
      {
        label: "Family Office Infrastructure",
        items: ["Gouvernance familiale", "Succession planning", "Multi-entites", "Architecture institutionnelle", "Global strategy", "Legacy timeline", "Protection et continuite"],
      },
    ],
  },
];
export default function PricingPlans({ mode }: PricingPlansProps) {
  const [interval, setInterval] = useState<BillingInterval>("monthly");
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const founder = mode === "founder";
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const parsePrice = (value: string) => Number(value.replace(/[^\d]/g, ""));
  const yearlySaving = (plan: Plan) => {
    const monthly = parsePrice(founder ? plan.founderPrice.monthly : plan.price.monthly);
    const yearly = parsePrice(founder ? plan.founderPrice.yearly : plan.price.yearly);
    return monthly * 12 - yearly;
  };
  const intervalLabel = interval === "monthly" ? "/ mois" : "/ an";

  const startCheckout = async (plan: Plan) => {
    if (!token) {
      window.location.assign(
        `/login?next=${encodeURIComponent(
          `/plans/${mode === "founder" ? "founder" : "standard"}`
        )}`
      );
      return;
    }

    setLoadingPlan(plan.id);
    setMessage("");

    try {
      const response = await apiRequest<{ url?: string }>(
        "/billing/create-checkout-session",
        token,
        {
          method: "POST",
          body: JSON.stringify({
            plan: plan.id,
            interval,
            founder,
          }),
        }
      );

      if (response.url) {
        window.location.assign(response.url);
        return;
      }

      setMessage("Paiement indisponible pour le moment.");
    } catch (err) {
      console.error(err);
      setMessage(
        "Impossible d'ouvrir le paiement. Réessaie dans quelques instants."
      );
    } finally {
      setLoadingPlan(null);
    }
  };

  return (
    <main className="min-h-screen overflow-hidden bg-black px-4 py-8 text-white">
      <section className="mx-auto max-w-7xl">
        <div className="mb-4 flex justify-end">
          <CockpitBackLink />
        </div>

        <div className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-gradient-to-br from-[#07111f] via-black to-[#101923] p-6 shadow-2xl sm:p-8">
          <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-[#3fa9f5]/20 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-28 left-1/3 h-72 w-72 rounded-full bg-emerald-300/18 blur-3xl" />

          <div className="relative">
            <p className="text-xs uppercase tracking-[0.35em] text-[#3fa9f5]">
              WHITE ROCK Plans
            </p>
            <div className="mt-4 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h1 className="max-w-4xl text-3xl font-black leading-tight sm:text-5xl">
                  {founder ? "Founder Access" : "Montez dans le Wealth OS"}
                </h1>
                <p className="mt-3 max-w-3xl text-sm leading-relaxed text-gray-300 sm:text-base">
                  {founder
                    ? "Une fenêtre limitée pour entrer plus tôt dans l'architecture White Rock, avec une perception de statut plus rare et plus fondatrice."
                    : "Chaque niveau inclut le précédent et débloque une couche plus sophistiquée de pilotage patrimonial."}
                </p>
              </div>

              <div className="w-full rounded-2xl border border-white/10 bg-white/[0.04] p-1 sm:w-auto">
                <div className="grid grid-cols-2 gap-1">
                  {(["monthly", "yearly"] as BillingInterval[]).map((item) => (
                    <button
                      key={item}
                      onClick={() => setInterval(item)}
                      className={`rounded-xl px-4 py-2 text-sm font-black transition ${
                        interval === item
                          ? "bg-white text-black shadow-lg"
                          : "text-gray-400 hover:bg-white/[0.05] hover:text-white"
                      }`}
                    >
                      {item === "monthly" ? "Monthly" : "Yearly - 2 mois offerts"}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-7 grid gap-2 sm:grid-cols-5">
              {ladder.map((step) => (
                <div
                  key={step.label}
                  className={`rounded-2xl border px-4 py-3 ${step.tone}`}
                >
                  <p className="text-xs font-black tracking-widest">{step.label}</p>
                  <p className="mt-1 text-sm font-bold text-gray-200">{step.role}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {founder && (
          <div className="mt-5 rounded-2xl border border-emerald-300/30 bg-emerald-300/10 p-4 text-sm leading-relaxed text-emerald-100">
            Founder Access est pensé comme une entrée rare : même parcours de paiement,
            même sécurité, mais une présentation plus exclusive pour les premiers membres.
          </div>
        )}

        {message && (
          <div className="mt-5 rounded-2xl border border-red-400/25 bg-red-500/10 p-4 text-sm text-red-100">
            {message}
          </div>
        )}

        <section className="mt-6 rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-xs uppercase tracking-[0.3em] text-emerald-300">
            Lecture de valeur
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl border border-emerald-300/25 bg-emerald-300/10 p-4">
              <p className="text-sm font-black">Chaque niveau inclut le precedent</p>
              <p className="mt-2 text-sm leading-relaxed text-gray-400">
                La montee en gamme se lit comme une progression, pas comme une liste de cartes separees.
              </p>
            </div>
            <div className="rounded-2xl border border-emerald-300/25 bg-emerald-300/10 p-4">
              <p className="text-sm font-black">Chaque niveau debloque un univers</p>
              <p className="mt-2 text-sm leading-relaxed text-gray-400">
                Analytics, Wealth OS, Freedom Engine puis Dynasty Office apparaissent comme des couches.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <p className="text-sm font-black">Le statut devient visible</p>
              <p className="mt-2 text-sm leading-relaxed text-gray-400">
                Les badges et la pyramide rendent la valeur plus emotionnelle, premium et aspirationnelle.
              </p>
            </div>
          </div>
        </section>

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-4">
          {plans.map((plan) => {
            const displayPrice = founder ? plan.founderPrice[interval] : plan.price[interval];
            const saving = yearlySaving(plan);

            return (
              <article
                key={plan.id}
                className={`group relative overflow-hidden rounded-[1.75rem] border p-5 shadow-xl transition duration-300 hover:-translate-y-1 hover:border-[#3fa9f5]/55 hover:shadow-2xl ${plan.tone}`}
              >
                <div className={`pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b ${plan.glow}`} />
                <div className="relative flex min-h-full flex-col">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-widest text-gray-500">
                        {plan.rank}
                      </p>
                      <h2 className="mt-2 text-3xl font-black">{plan.name}</h2>
                      <p className="mt-1 text-sm font-semibold text-gray-300">
                        {plan.subtitle}
                      </p>
                    </div>
                    <span className="rounded-full border border-white/15 bg-black/25 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-gray-200">
                      {founder ? "Founder" : plan.badge}
                    </span>
                  </div>

                  <div className="mt-5 rounded-2xl border border-white/10 bg-black/25 p-4">
                    <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                      {plan.includes}
                    </p>
                    <div className="mt-3 flex items-end gap-2">
                      <p className="text-3xl font-black tracking-tight">{displayPrice}</p>
                      <p className="pb-1 text-base font-black text-gray-300">{intervalLabel}</p>
                    </div>
                    {interval === "yearly" && saving > 0 && (
                      <p className="mt-2 rounded-full border border-emerald-300/35 bg-emerald-300/10 px-3 py-1 text-xs font-black text-emerald-100">
                        2 mois offerts - economie {saving} EUR
                      </p>
                    )}
                    <p className="mt-3 text-sm font-semibold text-gray-200">
                      {plan.transformation}
                    </p>
                  </div>

                  <div className="mt-4 rounded-2xl border border-emerald-300/30 bg-emerald-300/10 p-4">
                    <p className="text-xs uppercase tracking-widest text-emerald-300">
                      Ce que vous débloquez
                    </p>
                    <p className="mt-2 text-sm font-black text-white">{plan.unlock}</p>
                  </div>

                  <div className="mt-5 space-y-3">
                    {plan.capabilityGroups.map((group) => (
                      <div key={group.label} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                        <p className="text-xs font-black uppercase tracking-widest text-gray-500">
                          {group.label}
                        </p>
                        <ul className="mt-3 space-y-2 text-sm text-gray-300">
                          {group.items.map((item) => (
                            <li key={item} className="flex gap-2">
                              <span className="text-emerald-300">•</span>
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[11px] font-bold text-gray-300">
                      {plan.altBadge}
                    </span>
                  </div>

                  <button
                    onClick={() => startCheckout(plan)}
                    disabled={loadingPlan !== null}
                    className="mt-6 w-full rounded-2xl bg-gradient-to-r from-[#3fa9f5] to-emerald-400 px-4 py-3 text-sm font-black text-white shadow-lg shadow-emerald-400/20 transition hover:-translate-y-0.5 hover:shadow-emerald-300/30 disabled:opacity-60"
                  >
                    {loadingPlan === plan.id
                      ? "Ouverture du paiement..."
                      : founder
                        ? `Rejoindre ${plan.name} Founder`
                        : plan.cta}
                  </button>
                </div>
              </article>
            );
          })}
        </div>

      </section>
    </main>
  );
}

