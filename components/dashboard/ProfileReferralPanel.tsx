"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import type { WealthProfile } from "@/lib/types";

type ReferralData = {
  referral_code?: string;
  referral_url?: string;
  stats?: {
    invites?: number;
    converted?: number;
    reward_xp?: number;
  };
};

type ProfileReferralPanelProps = {
  level?: string | null;
  mode?: "both" | "identity" | "referral";
};

type IdentityPanelProps = {
  level?: string | null;
  profile: WealthProfile;
  saving: boolean;
  onSubmit: (event: FormEvent) => void;
  onAvatarFile: (file?: File) => void;
  onUpdate: (key: keyof WealthProfile, value: string) => void;
};

export function IdentityPanel({
  profile,
  saving,
  onSubmit,
  onAvatarFile,
  onUpdate,
}: IdentityPanelProps) {
  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-white/10 bg-zinc-950 p-4 sm:p-5"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div
          className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] bg-cover bg-center"
          style={
            profile.avatar_url
              ? { backgroundImage: `url(${profile.avatar_url})` }
              : undefined
          }
        >
          {profile.avatar_url ? (
            <span className="sr-only">Photo de profil</span>
          ) : (
            <span className="text-2xl font-black text-[#3fa9f5]">
              {(profile.first_name || "W").slice(0, 1).toUpperCase()}
            </span>
          )}
        </div>
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            Informations personnelles
          </p>
          <h2 className="mt-1 text-2xl font-bold">Identite et preferences</h2>
          <p className="mt-1 text-sm text-gray-400">
            Prenom, bio courte, photo et devise de reference.
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="space-y-1">
          <span className="text-xs font-semibold uppercase tracking-widest text-gray-500">
            Prenom
          </span>
          <input
            value={profile.first_name || ""}
            onChange={(event) => onUpdate("first_name", event.target.value)}
            placeholder="Prenom"
            className="w-full rounded-xl border border-white/10 bg-black px-4 py-3 text-white outline-none focus:border-[#3fa9f5]"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs font-semibold uppercase tracking-widest text-gray-500">
            Photo de profil
          </span>
          <input
            type="file"
            accept="image/*"
            onChange={(event) => onAvatarFile(event.target.files?.[0])}
            className="w-full rounded-xl border border-white/10 bg-black px-4 py-2.5 text-sm text-gray-300 file:mr-3 file:rounded-lg file:border-0 file:bg-white/10 file:px-3 file:py-1.5 file:text-white"
          />
        </label>
        <textarea
          value={profile.bio || ""}
          onChange={(event) => onUpdate("bio", event.target.value)}
          placeholder="Bio courte"
          rows={3}
          className="rounded-xl border border-white/10 bg-black px-4 py-3 text-white outline-none focus:border-[#3fa9f5] sm:col-span-2"
        />
        <label className="space-y-1">
          <span className="text-xs font-semibold uppercase tracking-widest text-gray-500">
            Devise du compte
          </span>
          <select
            value={profile.main_currency || "EUR"}
            onChange={(event) => onUpdate("main_currency", event.target.value)}
            className="w-full rounded-xl border border-white/10 bg-black px-4 py-3 text-white outline-none focus:border-[#3fa9f5]"
          >
            <option value="EUR">EUR</option>
            <option value="USD">USD</option>
            <option value="CAD">CAD</option>
            <option value="CHF">CHF</option>
            <option value="GBP">GBP</option>
          </select>
        </label>
      </div>

      <button
        disabled={saving}
        className="mt-5 rounded-xl bg-[#3fa9f5] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
      >
        {saving ? "Enregistrement..." : "Enregistrer"}
      </button>
    </form>
  );
}

export function ReferralPanel({ referral }: { referral: ReferralData | null }) {
  const [copied, setCopied] = useState(false);
  const copyReferralUrl = async () => {
    if (!referral?.referral_url || typeof navigator === "undefined") return;

    await navigator.clipboard.writeText(referral.referral_url);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-950 p-4 sm:p-5">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1.1fr] lg:items-center">
        <div>
          <h2 className="text-2xl font-bold">Parrainage et recompenses</h2>
          <p className="mt-2 text-sm text-gray-400">
            Chaque invitation active peut debloquer des XP, credits ou avantages White Rock selon les regles en vigueur.
          </p>
        </div>

        <div className="rounded-xl border border-white/10 bg-black/40 p-4">
          <p className="text-xs uppercase tracking-widest text-gray-500">
            Lien personnel
          </p>
          <button
            type="button"
            onClick={copyReferralUrl}
            disabled={!referral?.referral_url}
            className="mt-3 rounded-xl bg-[#3fa9f5] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {copied ? "Lien copie" : "Copier mon lien"}
          </button>
          <p className="mt-2 text-xs text-gray-500">
            Code: {referral?.referral_code || "en preparation"}
          </p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-xl bg-white/[0.04] p-3">
          <p className="text-xs text-gray-500">Invites</p>
          <p className="font-bold">{referral?.stats?.invites || 0}</p>
        </div>
        <div className="rounded-xl bg-white/[0.04] p-3">
          <p className="text-xs text-gray-500">Actifs</p>
          <p className="font-bold">{referral?.stats?.converted || 0}</p>
        </div>
        <div className="rounded-xl bg-white/[0.04] p-3">
          <p className="text-xs text-gray-500">XP</p>
          <p className="font-bold">{referral?.stats?.reward_xp || 0}</p>
        </div>
      </div>
    </section>
  );
}

export default function ProfileReferralPanel({
  level,
  mode = "both",
}: ProfileReferralPanelProps) {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const [profile, setProfile] = useState<WealthProfile>({});
  const [referral, setReferral] = useState<ReferralData | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      if (mode !== "referral") {
        try {
          const profileData = await apiRequest<{ profile?: WealthProfile }>(
            "/profile/me",
            token
          );
          setProfile(profileData.profile || {});
        } catch {
          setProfile({});
        }
      }

      if (mode !== "identity") {
        try {
          const referralData = await apiRequest<ReferralData>("/referrals/me", token);
          setReferral(referralData);
        } catch {
          setReferral(null);
        }
      }
    };

    if (token) load();
  }, [mode, token]);

  const updateProfile = (key: keyof WealthProfile, value: string) => {
    setProfile((current) => ({ ...current, [key]: value }));
  };

  const handleAvatarFile = (file?: File) => {
    if (!file || !file.type.startsWith("image/")) return;

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        updateProfile("avatar_url", reader.result);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);

    try {
      await apiRequest("/profile/me", token, {
        method: "PUT",
        body: JSON.stringify({
          ...profile,
          goals: profile.goals || [profile.motivation].filter(Boolean),
        }),
      });
    } finally {
      setSaving(false);
    }
  };

  const identityPanel = (
      <IdentityPanel
        level={level}
        profile={profile}
        saving={saving}
        onSubmit={handleSubmit}
        onAvatarFile={handleAvatarFile}
        onUpdate={updateProfile}
      />
  );
  const referralPanel = <ReferralPanel referral={referral} />;

  if (mode === "identity") return identityPanel;
  if (mode === "referral") return referralPanel;

  return (
    <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.2fr_0.8fr]">
      {identityPanel}
      {referralPanel}
    </section>
  );
}
