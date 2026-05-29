"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import type { ScoreDetails } from "@/lib/types";

type UserIntelligenceResponse = {
  score?: {
    score?: number;
    details?: ScoreDetails;
  };
  level?: string;
};

type ScoreData = {
  score: number;
  details: ScoreDetails;
  level: string;
};

export default function FamilyOfficeScore() {
  const [data, setData] = useState<ScoreData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchScore = async () => {
      const token = localStorage.getItem("token");

      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const json = await apiRequest<UserIntelligenceResponse>(
          "/intelligence/user-intelligence",
          token
        );

        setData({
          score: json.score?.score || 0,
          details: json.score?.details || {},
          level: json.level || "N/A",
        });
      } catch (err) {
        console.error("SCORE ERROR:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchScore();
  }, []);

  if (loading) {
    return <p className="text-white">Chargement...</p>;
  }

  if (!data) {
    return <p className="text-red-400">Erreur chargement score</p>;
  }

  const details = data.details;

  return (
    <div className="bg-white/5 backdrop-blur-lg p-6 rounded-2xl w-full max-w-xl text-white">
      <div className="flex flex-col items-center mb-6">
        <div className="text-5xl font-bold text-[#1DA2CF]">{data.score}</div>
        <p className="mt-2 text-white/70">{data.level}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm mb-6">
        <ScoreItem label="Richesse" value={details.wealth || 0} />
        <ScoreItem
          label="Diversification"
          value={details.diversification || 0}
        />
        <ScoreItem
          label="Risque dette"
          value={details.debt_risk_score ?? details.debt ?? 0}
        />
        <ScoreItem label="Activite" value={details.activity || 0} />
      </div>

      <p className="text-sm text-white/50">
        Le score reste un indicateur de lecture. Les decisions et priorites
        passent par le moteur central.
      </p>
    </div>
  );
}

function ScoreItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white/10 p-3 rounded-xl">
      <p className="text-xs opacity-70">{label}</p>
      <p className="text-lg font-bold">{Number(value || 0)}/100</p>
    </div>
  );
}
