"use client";

import { useState } from "react";
import { apiRequest } from "@/lib/api";
import type { ProductContext, ProductModule } from "@/lib/types";

type ProductProgressPanelProps = {
  product?: ProductContext | null;
  onUpgrade?: (plan: string) => void;
};

const stageLabels: Record<number, string> = {
  1: "Foundation",
  2: "Diversification",
  3: "Assets",
  4: "Business",
  5: "Pilotage",
  6: "Wealth OS",
  7: "Live Sync",
  8: "Liberty",
};

function ModulePill({ module }: { module: ProductModule }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2">
      <p className="text-sm font-semibold text-white">{module.label}</p>
      <p className="text-xs text-gray-500">{stageLabels[module.stage] || "Module"}</p>
    </div>
  );
}

export default function ProductProgressPanel({
  product,
  onUpgrade,
}: ProductProgressPanelProps) {
  const [verifyingKey, setVerifyingKey] = useState<string | null>(null);
  const [verificationMessage, setVerificationMessage] = useState("");

  if (!product) return null;

  const progression = product.progression || {};
  const entitlements = product.entitlements || {};
  const visible = product.modules?.visible || [];
  const locked = product.modules?.locked || [];
  const missions = product.missions || [];
  const brief = product.strategic_brief;
  const completion = product.data_profile?.completion_percent || 0;
  const plan = product.plan || entitlements.plan || "charge";
  const verifyMission = async (missionKey: string) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    setVerifyingKey(missionKey);
    setVerificationMessage("");
    try {
      const result = await apiRequest<{
        completed?: boolean;
        status?: string;
        xp_awarded?: number;
        validation?: string;
      }>(`/product/missions/${missionKey}/verify`, token, { method: "POST" });
      setVerificationMessage(
        result.completed
          ? result.xp_awarded
            ? `Mission validee: +${result.xp_awarded} XP.`
            : "Mission deja validee."
          : `Condition non remplie: ${result.validation || "action requise"}.`
      );
    } finally {
      setVerifyingKey(null);
    }
  };

  return (
    <section className="space-y-5">
      <div className="rounded-2xl border border-[#3fa9f5]/20 bg-zinc-950 p-5 transition duration-300 hover:border-[#3fa9f5]/35">
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            Progression patrimoniale
          </p>
          <h2 className="mt-2 text-2xl font-black text-white">
            {progression.level || "Builder"}
          </h2>
          <p className="mt-1 text-sm text-gray-400">
            {entitlements.copy?.promise || "Construis une progression patrimoniale claire."}
          </p>

          <div className="mt-5 grid grid-cols-3 gap-2">
            <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
              <p className="text-xs text-gray-500">Plan</p>
              <p className="font-bold text-white">{plan}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
              <p className="text-xs text-gray-500">Statut</p>
              <p className="font-bold text-white">{progression.status || "Foundation"}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
              <p className="text-xs text-gray-500">Completion</p>
              <p className="font-bold text-white">{completion}%</p>
            </div>
          </div>

          <div className="mt-4">
            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-[#3fa9f5]"
                style={{ width: `${progression.progress_percent || 0}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-gray-500">
              {progression.xp || 0} XP / {progression.next_level_xp || 1000} XP
            </p>
          </div>
      </div>

      {brief && (
        <div className="rounded-2xl border border-[#3fa9f5]/20 bg-zinc-950 p-5 transition duration-300 hover:border-[#3fa9f5]/35">
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            Signaux de contexte
          </p>
          <h3 className="mt-2 text-xl font-black text-white">
            {brief.priority || "Priorite du moment"}
          </h3>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            {[
              ["Levier", brief.main_lever],
              ["Vigilance", brief.main_risk],
              ["Signal", brief.opportunity],
              ["Donnee", brief.next_action],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-white/10 bg-black/30 p-3">
                <p className="text-xs font-black uppercase tracking-widest text-gray-500">{label}</p>
                <p className="mt-1 text-sm leading-relaxed text-gray-300">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {missions.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5 transition duration-300 hover:border-white/20">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="font-bold text-white">Missions de progression</h3>
                <span className="text-xs text-gray-500">Validation backend</span>
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                {missions.map((mission) => {
                  const missionStatus =
                    mission.status || (mission.completed ? "completed" : "pending");
                  const isVerified = missionStatus === "verified";
                  const isCompleted = isVerified || missionStatus === "completed";

                  return (
                    <article
                      key={mission.key}
                      className="rounded-xl border border-white/10 bg-black/30 p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-white">
                          {mission.title}
                        </p>
                        <span className="rounded-full border border-white/10 px-2 py-1 text-[10px] uppercase text-gray-400">
                          {isVerified
                            ? "Verified"
                            : isCompleted
                              ? "Completed"
                              : "Pending"}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-gray-400">{mission.description}</p>
                      {(mission.context_reason || mission.ethan_reason) && (
                        <p className="mt-2 text-xs leading-relaxed text-[#8bd0ff]">
                          Contexte: {mission.context_reason || mission.ethan_reason}
                        </p>
                      )}
                      <div className="mt-3 flex items-center justify-between gap-2">
                        {mission.xp ? (
                          <span className="text-xs font-bold text-emerald-300">
                            +{mission.xp} XP
                          </span>
                        ) : (
                          <span className="text-xs text-gray-500">Niveau</span>
                        )}
                        {mission.recommended_plan && onUpgrade && (
                          <button
                            onClick={() => onUpgrade(mission.recommended_plan || "gold")}
                            className="rounded-lg bg-[#3fa9f5] px-3 py-1 text-xs font-semibold text-white"
                          >
                            Voir
                          </button>
                        )}
                        {!mission.recommended_plan && (
                          <button
                            onClick={() => verifyMission(mission.key)}
                            disabled={verifyingKey === mission.key || isVerified}
                            className="rounded-lg border border-white/10 px-3 py-1 text-xs font-semibold text-white disabled:opacity-50"
                          >
                            {isVerified ? "Validee" : "Verifier"}
                          </button>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
              {verificationMessage && (
                <p className="mt-3 rounded-xl border border-white/10 bg-black/30 p-3 text-xs text-gray-300">
                  {verificationMessage}
                </p>
              )}
        </div>
      )}

      <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5 transition duration-300 hover:border-white/20">
              <h3 className="mb-2 font-bold text-white">Espaces ouverts</h3>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {visible.slice(0, 6).map((module) => (
                  <ModulePill key={module.key} module={module} />
                ))}
              </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5 transition duration-300 hover:border-white/20">
              <h3 className="mb-2 font-bold text-white">Prochaines etapes</h3>
              <div className="space-y-2">
                {locked.slice(0, 3).map((module) => (
                  <div
                    key={module.key}
                    className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-gray-200">{module.label}</p>
                      <span className="text-xs text-[#3fa9f5]">{module.required_plan}</span>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">{module.reason}</p>
                  </div>
                ))}
                {locked.length === 0 && (
                  <p className="text-sm text-gray-400">
                    Tous les espaces essentiels sont ouverts. Continue a consolider ton pilotage.
                  </p>
                )}
              </div>
      </div>
    </section>
  );
}
