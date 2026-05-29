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
  { label: "FREE", role: "Découverte" },
  { label: "GOLD", role: "Structuration" },
  { label: "ELITE", role: "Pilotage" },
  { label: "LIBERTY", role: "Liberté" },
  { label: "LEGACY", role: "Dynastie" },
];

const plans: Plan[] = [
  {
    id: "gold",
    name: "Gold",
    subtitle: "Fondations financières intelligentes",
    rank: "Niveau 1",
    badge: "Investor Favorite",
    altBadge: "Most Popular",
    transformation: "Structurer votre croissance patrimoniale",
    unlock: "Unlock advanced analytics",
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
    cta: "Débloquer Gold",
    capabilityGroups: [
      {
        label: "Wealth Intelligence",
        items: ["Score patrimonial lisible", "20 assets maximum", "Signaux d'amélioration"],
      },
      {
        label: "Opportunity Engine",
        items: ["Opportunités guidées", "Allocation de départ", "Lecture immobilier/investissements"],
      },
    ],
  },
  {
    id: "elite",
    name: "Elite",
    subtitle: "Wealth Operating System",
    rank: "Niveau 2",
    badge: "Wealth OS",
    altBadge: "Most Popular",
    transformation: "Piloter votre Wealth OS",
    unlock: "Unlock Wealth Intelligence",
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
    tone: "border-white/20 bg-white/[0.06]",
    glow: "from-white/16 via-[#3fa9f5]/10 to-transparent",
    cta: "Passer Elite",
    capabilityGroups: [
      {
        label: "Investment Operating System",
        items: ["Cockpit Family Office", "Limite historique: assets illimites", "Priorités patrimoniales"],
      },
      {
        label: "AI Strategic Guidance",
        items: ["Copilote avance", "Guidance contextuelle", "Syntheses executives"],
      },
    ],
  },
  {
    id: "liberty",
    name: "Liberty",
    subtitle: "Freedom Engine",
    rank: "Niveau 3",
    badge: "Freedom Tier",
    altBadge: "Private Access",
    transformation: "Construire votre liberté financière",
    unlock: "Unlock Freedom Systems",
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
    tone: "border-orange-300/40 bg-orange-300/10",
    glow: "from-orange-300/22 via-transparent to-[#3fa9f5]/8",
    cta: "Activer Liberty",
    capabilityGroups: [
      {
        label: "Freedom Systems",
        items: ["Pilotage liberté financière", "50 assets maximum", "Trajectoire d'indépendance"],
      },
      {
        label: "Business Command Center",
        items: ["Opportunités premium", "Business assets", "Stratégie de croissance"],
      },
    ],
  },
  {
    id: "legacy",
    name: "Legacy",
    subtitle: "Dynasty Office",
    rank: "Niveau 4",
    badge: "Dynasty Grade",
    altBadge: "Private Office",
    transformation: "Créer une dynastie familiale",
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
    tone: "border-amber-300/45 bg-amber-300/10",
    glow: "from-amber-300/24 via-orange-300/10 to-transparent",
    cta: "Entrer Legacy",
    capabilityGroups: [
      {
        label: "Dynasty Layer",
        items: ["Transmission familiale", "Assets illimites", "Vision générationnelle"],
      },
      {
        label: "Family Office Infrastructure",
        items: ["Dynasty Office", "Protection et continuité", "Architecture institutionnelle"],
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

      setMessage("Checkout Stripe indisponible pour le moment.");
    } catch (err) {
      console.error(err);
      setMessage(
        "Impossible d'ouvrir Stripe. Vérifie la configuration billing ou réessaie dans quelques instants."
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
          <div className="pointer-events-none absolute -bottom-28 left-1/3 h-72 w-72 rounded-full bg-orange-300/10 blur-3xl" />

          <div className="relative">
            <p className="text-xs uppercase tracking-[0.35em] text-[#3fa9f5]">
              WHITE ROCK Billing
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
                      {item === "monthly" ? "Monthly" : "Yearly"}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-7 grid gap-2 sm:grid-cols-5">
              {ladder.map((step, index) => (
                <div
                  key={step.label}
                  className={`rounded-2xl border px-4 py-3 ${
                    index === 0
                      ? "border-white/10 bg-white/[0.03]"
                      : "border-[#3fa9f5]/20 bg-[#3fa9f5]/8"
                  }`}
                >
                  <p className="text-xs font-black tracking-widest text-gray-500">{step.label}</p>
                  <p className="mt-1 text-sm font-bold text-gray-200">{step.role}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {founder && (
          <div className="mt-5 rounded-2xl border border-orange-300/25 bg-orange-300/10 p-4 text-sm leading-relaxed text-orange-100">
            Founder Access est pensé comme une entrée rare : même moteur Stripe,
            même sécurité, mais une présentation plus exclusive pour les premiers membres.
          </div>
        )}

        {message && (
          <div className="mt-5 rounded-2xl border border-red-400/25 bg-red-500/10 p-4 text-sm text-red-100">
            {message}
          </div>
        )}

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-4">
          {plans.map((plan, index) => {
            const displayPrice = founder ? plan.founderPrice[interval] : plan.price[interval];
            const displayNote = founder ? plan.founderNote[interval] : plan.priceNote[interval];

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
                      <p className="pb-1 text-xs font-bold text-gray-500">{displayNote}</p>
                    </div>
                    <p className="mt-3 text-sm font-semibold text-gray-200">
                      {plan.transformation}
                    </p>
                  </div>

                  <div className="mt-4 rounded-2xl border border-[#3fa9f5]/20 bg-[#3fa9f5]/10 p-4">
                    <p className="text-xs uppercase tracking-widest text-[#8bd0ff]">
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
                              <span className="text-[#3fa9f5]">•</span>
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
                    {index > 1 && (
                      <span className="rounded-full border border-orange-300/25 bg-orange-300/10 px-3 py-1 text-[11px] font-bold text-orange-200">
                        Private Office
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => startCheckout(plan)}
                    disabled={loadingPlan !== null}
                    className="mt-6 w-full rounded-2xl bg-[#3fa9f5] px-4 py-3 text-sm font-black text-white shadow-lg shadow-[#3fa9f5]/20 transition hover:-translate-y-0.5 hover:bg-[#2588d2] disabled:opacity-60"
                  >
                    {loadingPlan === plan.id
                      ? "Ouverture Stripe..."
                      : founder
                        ? `Rejoindre ${plan.name} Founder`
                        : plan.cta}
                  </button>
                </div>
              </article>
            );
          })}
        </div>

        <section className="mt-6 rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
          <p className="text-xs uppercase tracking-[0.3em] text-[#3fa9f5]">
            Lecture de valeur
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <p className="text-sm font-black">Chaque niveau inclut le précédent</p>
              <p className="mt-2 text-sm leading-relaxed text-gray-400">
                La montée en gamme se lit comme une progression, pas comme une liste de cartes séparées.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <p className="text-sm font-black">Chaque niveau débloque un univers</p>
              <p className="mt-2 text-sm leading-relaxed text-gray-400">
                Analytics, Wealth OS, Freedom Engine puis Dynasty Office apparaissent comme des couches.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <p className="text-sm font-black">Le statut devient visible</p>
              <p className="mt-2 text-sm leading-relaxed text-gray-400">
                Les badges et la pyramide rendent la valeur plus émotionnelle, premium et aspirationnelle.
              </p>
            </div>
          </div>
        </section>

        <section className="mt-6 rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
          <p className="text-xs uppercase tracking-[0.3em] text-[#3fa9f5]">
            Limites assets
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            {[
              ["FREE", "10 assets"],
              ["GOLD", "20 assets"],
              ["LIBERTY", "50 assets"],
              ["LEGACY", "Illimite"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl border border-white/10 bg-black/25 p-4">
                <p className="text-xs font-black tracking-widest text-gray-500">{label}</p>
                <p className="mt-1 text-sm font-bold text-white">{value}</p>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
