"use client";

import { useState } from "react";
import type { GamificationData } from "@/lib/types";

type GamificationProps = {
  gamification?: GamificationData;
  score?: number;
  userLevel?: string;
  plan?: string;
  onUpgrade?: (plan: string) => void;
};

type MissionAction = {
  title: string;
  description: string;
  xp?: number;
};

const badgeCollection = [
  { key: "Wealth Guardian", label: "Wealth Guardian", rarity: "Core", tone: "border-[#3fa9f5]/45 bg-[#3fa9f5]/10 text-[#bfe8ff]" },
  { key: "Income Builder", label: "Income Builder", rarity: "Core", tone: "border-emerald-300/45 bg-emerald-300/10 text-emerald-100" },
  { key: "Capital Strategist", label: "Capital Strategist", rarity: "Rare", tone: "border-cyan-300/45 bg-cyan-300/10 text-cyan-100" },
  { key: "Risk Sentinel", label: "Risk Sentinel", rarity: "Rare", tone: "border-blue-300/45 bg-blue-300/10 text-blue-100" },
  { key: "Strategic Operator", label: "Strategic Operator", rarity: "Epic", tone: "border-orange-300/45 bg-orange-300/10 text-orange-100" },
  { key: "Family Protector", label: "Family Protector", rarity: "Epic", tone: "border-amber-200/45 bg-amber-200/10 text-amber-100" },
  { key: "Dynasty Builder", label: "Dynasty Builder", rarity: "Legend", tone: "border-amber-300/55 bg-amber-300/10 text-amber-100" },
];

function BadgeMedal({
  badge,
  unlocked,
}: {
  badge: (typeof badgeCollection)[number];
  unlocked: boolean;
}) {
  const initials = badge.label
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 3)
    .toUpperCase();

  return (
    <div
      className={`relative min-h-32 overflow-hidden rounded-xl border p-4 transition ${
        unlocked
          ? badge.tone
          : "border-white/10 bg-black/30 text-gray-600"
      }`}
    >
      <div className="absolute inset-x-6 top-0 h-px bg-white/35" />
      <div className="flex items-start gap-3">
        <div
          className={`relative grid h-14 w-14 shrink-0 place-items-center rounded-full border shadow-inner ${
            unlocked
              ? "border-current bg-gradient-to-br from-white/30 via-current/10 to-black/30 shadow-black/40"
              : "border-white/10 bg-gradient-to-br from-white/10 to-black"
          }`}
        >
          <div className="h-8 w-8 rotate-45 rounded-md border border-current/50" />
          <span className="absolute text-[10px] font-black tracking-widest">
            {initials}
          </span>
        </div>
        <div>
          <p className="text-xs font-black uppercase tracking-widest">
            {badge.label}
          </p>
          <p className="mt-1 text-[11px] font-semibold opacity-75">
            {unlocked ? badge.rarity : "A debloquer"}
          </p>
        </div>
      </div>
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-black/30">
        <div
          className={`h-full rounded-full ${
            unlocked ? "w-full bg-current" : "w-1/3 bg-white/15"
          }`}
        />
      </div>
    </div>
  );
}

export default function GamificationPanel({
  gamification,
  score = 0,
  userLevel,
  plan,
  onUpgrade,
}: GamificationProps) {
  const [selectedAction, setSelectedAction] = useState<MissionAction | null>(null);

  if (!gamification) return null;

  const xp = Number(gamification.xp || 0);
  const xpToNextLevel = Number(gamification.xp_to_next_level || 1000);
  const level =
    gamification.level ?? Math.max(1, Math.floor(xp / xpToNextLevel) + 1);
  const streak = gamification.streak || 0;
  const badges = Array.isArray(gamification.badges) ? gamification.badges : [];
  const unlockedBadges = new Set(badges.map((badge) => String(badge).toLowerCase()));
  const normalizedBadges = badgeCollection.map((badge) => ({
    ...badge,
    unlocked:
      unlockedBadges.has(badge.key.toLowerCase()) ||
      unlockedBadges.has(badge.label.toLowerCase()),
  }));
  const collectionKeys = new Set(
    badgeCollection.flatMap((badge) => [
      badge.key.toLowerCase(),
      badge.label.toLowerCase(),
    ])
  );
  const earnedBadges = [
    ...normalizedBadges.filter((badge) => badge.unlocked),
    ...badges
      .filter((badge) => !collectionKeys.has(String(badge).toLowerCase()))
      .map((badge) => ({
        key: String(badge),
        label: String(badge),
        rarity: "Earned",
        tone: "border-[#3fa9f5]/45 bg-[#3fa9f5]/10 text-[#bfe8ff]",
        unlocked: true,
      })),
  ];
  const lockedBadges = normalizedBadges.filter((badge) => !badge.unlocked);
  const progress =
    gamification.progress_xp !== undefined
      ? Number(gamification.progress_xp || 0)
      : xp % xpToNextLevel;
  const progressPercent =
    gamification.progress_percent !== undefined
      ? Number(gamification.progress_percent || 0)
      : Math.min(100, (progress / xpToNextLevel) * 100);
  const normalizedLevel = String(userLevel || "").toUpperCase();
  const advanced = score >= 70 || normalizedLevel === "ADVANCED";
  const legacyMode =
    normalizedLevel === "LEGACY" ||
    normalizedLevel === "DYNASTY ARCHITECT";
  const recommendedPlan =
    gamification.upgrade?.recommended_plan?.toLowerCase() || null;
  const canUpgrade = Boolean(recommendedPlan);
  const actions: MissionAction[] =
    gamification.actions && gamification.actions.length > 0
      ? gamification.actions.map((action) => ({
          title: action.title || "Mission",
          description:
            action.description ||
            "Clarifie une action utile pour faire progresser ton cockpit.",
          xp: action.xp,
        }))
      : advanced
        ? legacyMode
          ? [
              {
                title: "Transmission",
                description:
                  "Identifier un document, une regle ou une personne cle a securiser cette semaine.",
                xp: 80,
              },
              {
                title: "Protection",
                description:
                  "Verifier la concentration du risque et ce qui doit etre protege en priorite.",
                xp: 70,
              },
            ]
          : [
              {
                title: "Mission Advanced",
                description:
                  "Choisir une opportunite prioritaire et definir une action executable en 7 jours.",
                xp: 150,
              },
              {
                title: "Optimisation portefeuille",
                description:
                  "Verifier la plus forte exposition et reduire le risque si elle depasse ton seuil.",
                xp: 120,
              },
            ]
        : [];

  return (
    <div className="rounded-2xl border border-gray-800 bg-gradient-to-br from-gray-900 to-black p-4 shadow-xl sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-emerald-300">
            Progression
          </p>
          <h2 className="mt-1 text-2xl font-bold text-white">
            Trajectoire personnelle
          </h2>
        </div>
        <div className="text-sm font-semibold text-orange-400">
          {streak} jours
        </div>
      </div>

      {actions.length > 0 && (
        <section className="mb-4 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <div className="shrink-0 lg:w-44">
              <h3 className="text-lg font-semibold text-emerald-300">
                Missions du jour
              </h3>
              <p className="mt-1 text-xs text-gray-400">
                Ligne d&apos;actions courtes.
              </p>
            </div>
            <div className="no-scrollbar flex flex-1 gap-3 overflow-x-auto pb-1">
              {actions.map((action, index) => (
                <button
                  type="button"
                  key={`${action.title}-${index}`}
                  onClick={() => setSelectedAction(action)}
                  className="min-w-[240px] flex-1 rounded-xl border border-white/10 bg-black/30 p-3 text-left transition hover:border-emerald-300/40 hover:bg-white/[0.04]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{action.title}</p>
                      <p className="mt-1 text-xs text-gray-400">
                        {action.description}
                      </p>
                    </div>
                    {action.xp && (
                      <span className="shrink-0 text-xs font-bold text-emerald-300">
                        +{action.xp} XP
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
          {selectedAction && (
            <div className="mt-4 rounded-xl border border-emerald-300/20 bg-black/40 p-3">
              <p className="text-xs uppercase tracking-widest text-emerald-300">
                Detail mission
              </p>
              <p className="mt-2 font-semibold text-white">
                {selectedAction.title}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-gray-400">
                {selectedAction.description}
              </p>
              {selectedAction.xp ? (
                <p className="mt-2 text-xs font-bold text-emerald-300">
                  Recompense: +{selectedAction.xp} XP
                </p>
              ) : null}
            </div>
          )}
        </section>
      )}

      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold text-white">Level {level}</h3>
          <span className="font-bold text-[#3fa9f5]">{xp} XP</span>
        </div>
        <div className="mt-3 h-3 w-full overflow-hidden rounded-full bg-gray-800">
          <div
            className="h-3 rounded-full bg-gradient-to-r from-[#3fa9f5] to-[#8bd0ff] transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-gray-400">
          {progress} / {xpToNextLevel} XP avant le prochain level
        </p>
      </section>

      <section className="mt-4 rounded-2xl border border-[#3fa9f5]/30 bg-[#3fa9f5]/10 p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-[#3fa9f5]">
              Prochain niveau
            </h3>
            <p className="mt-1 text-sm font-semibold text-white">
              {gamification.upgrade?.title ||
                (recommendedPlan === "legacy"
                  ? "Passer en DYNASTY - Family Office"
                  : recommendedPlan === "liberty"
                    ? "Debloquer LIBERTY - Sovereign Wealth"
                    : recommendedPlan === "elite"
                      ? "Debloquer ELITE - Wealth OS"
                      : "Debloquer GOLD - Growth")}
            </p>
            <p className="mt-2 text-xs text-gray-400">
              {gamification.upgrade?.description ||
                (legacyMode
                  ? "Tu es dans une phase de preservation, de gouvernance et de transmission."
                  : "Ton niveau actuel justifie un espace plus avance pour accelerer, proteger et transmettre ton capital.")}
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <span className="text-xs text-gray-500">
              Plan actuel: {plan || "FREE"}
            </span>
            {onUpgrade && canUpgrade && (
              <button
                onClick={() => recommendedPlan && onUpgrade(recommendedPlan)}
                className="rounded-xl bg-[#3fa9f5] px-4 py-2 text-sm font-semibold text-white"
              >
                Explorer
              </button>
            )}
          </div>
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
        <h3 className="text-lg font-semibold text-white">Badges obtenus</h3>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {earnedBadges.length > 0 ? (
            earnedBadges.map((badge) => (
              <div key={badge.key}>
                <BadgeMedal badge={badge} unlocked />
              </div>
            ))
          ) : (
            <p className="rounded-xl border border-white/10 bg-black/30 p-4 text-sm text-gray-400">
              Aucun badge obtenu pour le moment.
            </p>
          )}
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
        <h3 className="text-lg font-semibold text-white">Badges a debloquer</h3>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {lockedBadges.map((badge) => (
            <div key={badge.key}>
              <BadgeMedal badge={badge} unlocked={false} />
            </div>
          ))}
        </div>
      </section>

      {gamification.reward?.title && (
        <section className="mt-4 rounded-2xl border border-yellow-500/30 bg-yellow-500/10 p-4">
          <h3 className="mb-2 text-lg font-semibold text-yellow-400">
            Reward Unlocked
          </h3>
          <p className="text-sm text-white">{gamification.reward.title}</p>
          {gamification.reward.description && (
            <p className="mt-1 text-xs text-gray-400">
              {gamification.reward.description}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
