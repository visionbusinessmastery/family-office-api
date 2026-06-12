"use client";

import Script from "next/script";
import { useEffect, useState } from "react";
import CockpitBackLink from "@/components/CockpitBackLink";
import { apiFetch } from "@/lib/api-client";

type PricingPlansProps = {
  mode: "standard" | "founder";
};

type PricingTableSession = {
  client_secret: string;
  client_reference_id: string;
  stripe_customer_id: string;
};

const STRIPE_PRICING_TABLE_ID = "prctbl_1TgqeoPdcZID0JqGaIVYRhTV";
const STRIPE_PUBLISHABLE_KEY =
  "pk_test_51TPCCgPdcZID0JqGN8sni4FjrDo9oEwJVq0Cbv1CFfjYrSmY02doRmAZq329Rv5iNTi536G4iLFXq10joSg8grPv00e1uRCd3q";

export default function PricingPlans({ mode }: PricingPlansProps) {
  const [session, setSession] = useState<PricingTableSession | null>(null);
  const [message, setMessage] = useState("");
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  useEffect(() => {
    if (!token) return;

    let alive = true;
    apiFetch<PricingTableSession>("/billing/pricing-table-session", token, {
      method: "POST",
    })
      .then((data) => {
        if (alive) setSession(data);
      })
      .catch((err) => {
        console.error(err);
        if (alive) {
          setMessage(
            "Impossible de preparer la grille Stripe. Verifie ta session puis reessaie."
          );
        }
      });

    return () => {
      alive = false;
    };
  }, [token]);

  const redirectToLogin = () => {
    window.location.assign(
      `/login?next=${encodeURIComponent(
        `/plans/${mode === "founder" ? "founder" : "standard"}`
      )}`
    );
  };

  return (
    <main className="min-h-screen overflow-hidden bg-black px-4 py-8 text-white">
      <Script async src="https://js.stripe.com/v3/pricing-table.js" />

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
            <h1 className="mt-4 max-w-4xl text-3xl font-black leading-tight sm:text-5xl">
              {mode === "founder" ? "Founder Access" : "Choisis ton niveau White Rock"}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-relaxed text-gray-300 sm:text-base">
              Les abonnements sont geres par Stripe. White Rock synchronise ensuite ton plan
              via webhook pour mettre a jour la DB, le dashboard et tes acces.
            </p>
          </div>
        </div>

        {message && (
          <div className="mt-5 rounded-2xl border border-red-400/25 bg-red-500/10 p-4 text-sm text-red-100">
            {message}
          </div>
        )}

        {!token && (
          <section className="mt-6 rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-6">
            <p className="text-lg font-black">Connexion requise</p>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-gray-300">
              Connecte-toi avant de choisir un plan. Cela permet a Stripe de reutiliser
              ton customer existant et evite la creation de doublons.
            </p>
            <button
              onClick={redirectToLogin}
              className="mt-5 rounded-2xl bg-[#3fa9f5] px-5 py-3 text-sm font-black text-white shadow-lg shadow-[#3fa9f5]/20 transition hover:bg-[#2588d2]"
            >
              Se connecter
            </button>
          </section>
        )}

        {token && !session && !message && (
          <section className="mt-6 rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-6 text-sm text-gray-300">
            Preparation securisee de la grille Stripe...
          </section>
        )}

        {session?.client_secret && (
          <section className="mt-6 overflow-hidden rounded-[1.75rem] border border-white/10 bg-white p-1 text-black shadow-2xl">
            {/*
              Stripe Pricing Table receives a server-generated Customer Session.
              This keeps Stripe tied to the existing customer instead of creating duplicates.
            */}
            {/*
              @ts-expect-error Stripe registers this custom element from js.stripe.com.
            */}
            <stripe-pricing-table
              pricing-table-id={STRIPE_PRICING_TABLE_ID}
              publishable-key={STRIPE_PUBLISHABLE_KEY}
              customer-session-client-secret={session.client_secret}
              client-reference-id={session.client_reference_id}
            />
          </section>
        )}
      </section>
    </main>
  );
}
