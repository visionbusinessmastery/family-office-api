"use client";

import { useEffect, useState } from "react";
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

type BackendPricingGroup = {
  label: string;
  items: string[];
};

type BackendBillingPlan = {
  id: string;
  name?: string;
  entitlements?: {
    pricing_groups?: BackendPricingGroup[];
  };
};

type CurrentSubscription = {
  plan: string;
  status: string;
  subscription_plan?: string;
  current_period_end?: string | null;
  pending_plan?: string | null;
  pending_effective_at?: string | null;
  pending_change_type?: string | null;
};

type ScheduleDowngradeResponse = {
  status: string;
  current_plan: string;
  pending_plan: string;
  pending_effective_at?: string | null;
  change_type?: string;
};

const planOrder: Record<string, number> = {
  FREE: 0,
  GOLD: 1,
  ELITE: 2,
  LIBERTY: 3,
  LEGACY: 4,
};

const planDepth: Record<Plan["id"], { label: string; detail: string; tone: string }> = {
  gold: {
    label: "Pilotage actif",
    detail: "Base patrimoniale + decisions",
    tone: "border-[#3fa9f5]/35 bg-[#3fa9f5]/10 text-[#8bd0ff]",
  },
  elite: {
    label: "Optimisation",
    detail: "Simulation + lecture CEO",
    tone: "border-emerald-300/40 bg-emerald-300/10 text-emerald-100",
  },
  liberty: {
    label: "Arbitrages",
    detail: "Family Office personnel",
    tone: "border-amber-300/45 bg-amber-300/10 text-amber-100",
  },
  legacy: {
    label: "Dynasty",
    detail: "Transmission + gouvernance",
    tone: "border-[#ffe600]/70 bg-[#ffe600]/15 text-[#fff8a6]",
  },
};

const ladder = [
  { label: "FREE", role: "Decouverte", tone: "border-white/10 bg-white/[0.03] text-gray-500" },
  { label: "GOLD", role: "Trajectoire", tone: "border-[#3fa9f5]/25 bg-[#3fa9f5]/10 text-[#8bd0ff]" },
  { label: "ELITE", role: "Optimisation", tone: "border-emerald-300/45 bg-emerald-300/10 text-emerald-100" },
  { label: "LIBERTY", role: "Arbitrages", tone: "border-amber-300/50 bg-amber-300/[0.12] text-amber-100" },
  { label: "DYNASTY", role: "Transmission", tone: "border-[#ffe600] bg-[#ffe600]/[0.26] text-[#fff8a6] shadow-lg shadow-[#ffe600]/20" },
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
        items: ["20 assets financiers", "3 biens immobiliers avec lecture cashflow", "2 business structures", "Patrimoine visible et activable", "Wealth Map", "Projection 10 ans"],
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
        items: ["30 assets financiers", "10 biens immobiliers avec simulations", "5 business avec valorisation", "Family Office CEO", "Runway", "Lecture operationnelle", "Multi-user", "Companies"],
      },
      {
        label: "Family Office Intelligence",
        items: ["Wealth Narrative enrichi", "Simulations multi-scenarios", "Stress tests avances", "Detecteur de dependances", "Coffre documentaire patrimonial", "Imports assistes", "Graphiques par rubrique", "Allocations avancees"],
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
        items: ["50 assets financiers", "Immobilier illimite", "Business illimites", "Family Office Mode complet", "Comptes enfants", "Multi-objectifs", "Scenarios de vie avances", "Probabilites d'atteinte", "Architecture patrimoniale", "Dynasty planning"],
      },
      {
        label: "Architecture patrimoniale",
        items: ["Family Office Board", "CFO View", "Investor View", "Entrepreneur View", "Family View", "Priorites d'allocation", "Arbitrages strategiques", "Transmission", "Automation", "Sovereign guidance"],
      },
    ],
  },
  {
    id: "legacy",
    name: "Dynasty",
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
    tone: "border-[#ffe600] bg-[#ffe600]/[0.22] shadow-2xl shadow-[#ffe600]/25 ring-1 ring-[#fff8a6]/25",
    glow: "from-[#ffe600]/65 via-[#facc15]/35 to-[#3fa9f5]/10",
    cta: "Entrer Dynasty",
    capabilityGroups: [
      {
        label: "Dynasty Layer",
        items: ["Assets financiers illimites", "Immobilier et business illimites", "Projection 30 ans", "Transmission familiale", "Family Vault", "Heirs mode", "Protection layer", "Asset protection", "Dynasty governance", "Succession planning", "Global strategy", "Dynasty timeline"],
      },
      {
        label: "Family Office Infrastructure",
        items: ["Gouvernance familiale", "Multi-entites", "Architecture institutionnelle", "Protection et continuite", "Family governance", "Dynasty guidance", "Heirs intelligence", "Global opportunities", "Vault familial", "Scenario successoral", "Continuite familiale", "Patrimoine generationnel"],
      },
    ],
  },
];
export default function PricingPlans({ mode }: PricingPlansProps) {
  const [interval, setInterval] = useState<BillingInterval>("monthly");
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [subscription, setSubscription] = useState<CurrentSubscription | null>(null);
  const [backendPlans, setBackendPlans] = useState<Record<string, BackendBillingPlan>>({});
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
  const currentPlan = (subscription?.plan || "FREE").toUpperCase();
  const pendingPlan = subscription?.pending_plan?.toUpperCase() || null;
  const formatDate = (value?: string | null) => {
    if (!value) return null;
    try {
      return new Intl.DateTimeFormat("fr-FR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      }).format(new Date(value));
    } catch {
      return value;
    }
  };

  useEffect(() => {
    if (!token) return;

    let alive = true;
    apiRequest<CurrentSubscription>("/billing/current-subscription", token)
      .then((data) => {
        if (alive) setSubscription(data);
      })
      .catch(() => {
        if (alive) setSubscription(null);
      });

    return () => {
      alive = false;
    };
  }, [token]);

  useEffect(() => {
    let alive = true;
    apiRequest<{ plans?: BackendBillingPlan[] }>("/billing/plans")
      .then((data) => {
        if (!alive) return;
        const indexed = Object.fromEntries(
          (data.plans || []).map((plan) => [plan.id, plan])
        );
        setBackendPlans(indexed);
      })
      .catch(() => {
        if (alive) setBackendPlans({});
      });

    return () => {
      alive = false;
    };
  }, []);

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
        "Impossible d'ouvrir le paiement. RÃ©essaie dans quelques instants."
      );
    } finally {
      setLoadingPlan(null);
    }
  };

  const scheduleDowngrade = async (planId: string) => {
    if (!token) {
      window.location.assign(
        `/login?next=${encodeURIComponent(
          `/plans/${mode === "founder" ? "founder" : "standard"}`
        )}`
      );
      return;
    }

    setLoadingPlan(planId);
    setMessage("");

    try {
      const response = await apiRequest<ScheduleDowngradeResponse>(
        "/billing/schedule-downgrade",
        token,
        {
          method: "POST",
          body: JSON.stringify({
            plan: planId,
            interval,
          }),
        }
      );

      setSubscription((current) => ({
        ...(current || {
          plan: response.current_plan || currentPlan,
          status: "active",
        }),
        pending_plan: response.pending_plan || planId.toUpperCase(),
        pending_effective_at: response.pending_effective_at || null,
        pending_change_type: response.change_type || "downgrade",
      }));
      setMessage("Changement programme. Vos acces actuels restent actifs jusqu'a la prochaine echeance.");
    } catch (err) {
      console.error(err);
      setMessage("Impossible de programmer ce changement pour le moment.");
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
                    ? "Une fenÃªtre limitÃ©e pour entrer plus tÃ´t dans l'architecture White Rock, avec une perception de statut plus rare et plus fondatrice."
                    : "Chaque niveau inclut le prÃ©cÃ©dent et dÃ©bloque une couche plus sophistiquÃ©e de pilotage patrimonial."}
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
            Founder Access est pensÃ© comme une entrÃ©e rare : mÃªme parcours de paiement,
            mÃªme sÃ©curitÃ©, mais une prÃ©sentation plus exclusive pour les premiers membres.
          </div>
        )}

        {message && (
          <div className="mt-5 rounded-2xl border border-red-400/25 bg-red-500/10 p-4 text-sm text-red-100">
            {message}
          </div>
        )}

        {token && subscription && (
          <section className="mt-5 rounded-[1.75rem] border border-[#3fa9f5]/25 bg-[#3fa9f5]/10 p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-[#8bd0ff]">
                  Transition abonnement
                </p>
                <div className="mt-3 flex flex-wrap gap-2 text-sm font-black">
                  <span className="rounded-full border border-white/15 bg-black/25 px-3 py-1">
                    Plan actuel : {currentPlan}
                  </span>
                  {pendingPlan && (
                    <span className="rounded-full border border-amber-300/35 bg-amber-300/12 px-3 py-1 text-amber-100">
                      Plan futur : {pendingPlan}
                    </span>
                  )}
                </div>
                <p className="mt-3 text-sm leading-relaxed text-gray-300">
                  {pendingPlan
                    ? `Le changement prendra effet a la prochaine echeance${
                        formatDate(subscription.pending_effective_at)
                          ? ` : ${formatDate(subscription.pending_effective_at)}`
                          : ""
                      }.`
                    : "Vos droits actifs suivent votre abonnement actuel. Un downgrade planifie garde les acces jusqu'a l'echeance."}
                </p>
              </div>

              {planOrder[currentPlan] > 0 && pendingPlan !== "FREE" && (
                <button
                  onClick={() => scheduleDowngrade("free")}
                  disabled={loadingPlan !== null}
                  className="rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm font-black text-white transition hover:border-[#3fa9f5]/45 hover:bg-white/10 disabled:opacity-60"
                >
                  {loadingPlan === "free" ? "Programmation..." : "Revenir a Free a l'echeance"}
                </button>
              )}
            </div>
          </section>
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
                Analytics, Wealth OS, Freedom Engine puis Dynasty apparaissent comme des paliers de puissance.
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
            const targetPlan = plan.id.toUpperCase();
            const targetRank = planOrder[targetPlan] ?? 0;
            const currentRank = planOrder[currentPlan] ?? 0;
            const backendPlan = backendPlans[plan.id];
            const displayGroups =
              backendPlan?.entitlements?.pricing_groups?.length
                ? backendPlan.entitlements.pricing_groups
                : plan.capabilityGroups;
            const isCurrentPlan = targetPlan === currentPlan && !pendingPlan;
            const isPendingPlan = targetPlan === pendingPlan;
            const isDowngrade = targetRank < currentRank;
            const optionCount = displayGroups.reduce(
              (total, group) => total + group.items.length,
              0
            );
            const depth = planDepth[plan.id];
            const actionLabel = isCurrentPlan
              ? "Plan actuel"
              : isPendingPlan
                ? "Plan futur programme"
                : isDowngrade
                  ? `Programmer ${plan.name}`
                  : founder
                    ? `Rejoindre ${plan.name} Founder`
                    : plan.cta;
            const isActionDisabled =
              loadingPlan !== null || isCurrentPlan || isPendingPlan;

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
                      Ce que vous dÃ©bloquez
                    </p>
                    <p className="mt-2 text-sm font-black text-white">{plan.unlock}</p>
                  </div>

                  <div className="mt-4 grid grid-cols-3 gap-2">
                    <div className="rounded-2xl border border-white/10 bg-black/25 p-3">
                      <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">
                        Palier
                      </p>
                      <p className="mt-1 text-lg font-black text-white">
                        {targetRank}/4
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-black/25 p-3">
                      <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">
                        Options
                      </p>
                      <p className="mt-1 text-lg font-black text-white">
                        {optionCount}
                      </p>
                    </div>
                    <div className={`rounded-2xl border p-3 ${depth.tone}`}>
                      <p className="text-[10px] font-black uppercase tracking-widest opacity-75">
                        Lecture
                      </p>
                      <p className="mt-1 text-xs font-black leading-tight">
                        {depth.label}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <div className="flex items-center gap-1">
                      {Array.from({ length: 4 }).map((_, index) => (
                        <span
                          key={index}
                          className={`h-2 flex-1 rounded-full ${
                            index < targetRank
                              ? plan.id === "legacy"
                                ? "bg-[#ffe600] shadow-[0_0_14px_rgba(255,230,0,0.45)]"
                                : plan.id === "liberty"
                                  ? "bg-amber-300"
                                  : plan.id === "elite"
                                    ? "bg-emerald-300"
                                    : "bg-[#3fa9f5]"
                              : "bg-white/10"
                          }`}
                        />
                      ))}
                    </div>
                    <p className="mt-2 text-xs font-semibold text-gray-400">
                      {depth.detail}
                    </p>
                  </div>

                  <div className="mt-5 space-y-3">
                    {displayGroups.map((group) => (
                      <div key={group.label} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                        <p className="text-xs font-black uppercase tracking-widest text-gray-500">
                          {group.label}
                        </p>
                        <ul className="mt-3 space-y-2 text-sm text-gray-300">
                          {group.items.map((item) => (
                            <li key={item} className="flex gap-2">
                              <span className="text-emerald-300">â€¢</span>
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

                  {isDowngrade && !isPendingPlan && (
                    <p className="mt-5 rounded-2xl border border-amber-300/25 bg-amber-300/10 p-3 text-xs font-bold leading-relaxed text-amber-100">
                      Ce changement prendra effet a la prochaine echeance. Vos acces actuels restent ouverts jusque-la.
                    </p>
                  )}

                  <button
                    onClick={() => (isDowngrade ? scheduleDowngrade(plan.id) : startCheckout(plan))}
                    disabled={isActionDisabled}
                    className="mt-6 w-full rounded-2xl bg-gradient-to-r from-[#3fa9f5] to-emerald-400 px-4 py-3 text-sm font-black text-white shadow-lg shadow-emerald-400/20 transition hover:-translate-y-0.5 hover:shadow-emerald-300/30 disabled:opacity-60"
                  >
                    {loadingPlan === plan.id
                      ? isDowngrade
                        ? "Programmation..."
                        : "Ouverture du paiement..."
                      : actionLabel}
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


