"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type AdvisorResponse = {
  analysis: string;
  metadata: {
    cache_version: string;
    text_origin: string;
  };
};

const initialMessages: ChatMessage[] = [];

const CACHE_TTL_MS = 24 * 60 * 60 * 1000;
const MAX_CACHED_MESSAGES = 40;
const CONVERSATION_CACHE_VERSION = "v22-llm-diagnostics";
const LEGACY_RESPONSE_PATTERNS = [
  "ton score est",
  "score 39/100",
  "pour le cashflow",
  "action simple",
  "action prioritaire",
  "priorite:",
  "clarifier la capacite",
  "capacite mensuelle disponible",
  "ethan vient d'ecarter",
];

type CachedConversation = {
  version?: string;
  updatedAt: number;
  messages: ChatMessage[];
};

function normalizeConversationText(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function getUserCacheKey() {
  if (typeof window === "undefined") {
    return `ethanConversation:${CONVERSATION_CACHE_VERSION}:anonymous`;
  }

  const token = localStorage.getItem("token");
  if (!token) return `ethanConversation:${CONVERSATION_CACHE_VERSION}:anonymous`;

  try {
    const tokenPayload = token.split(".")[1];
    const paddedPayload = tokenPayload.padEnd(
      tokenPayload.length + ((4 - (tokenPayload.length % 4)) % 4),
      "="
    );
    const payload = JSON.parse(
      atob(paddedPayload.replace(/-/g, "+").replace(/_/g, "/"))
    );
    return `ethanConversation:${CONVERSATION_CACHE_VERSION}:${
      payload.sub || payload.email || payload.user_id || "user"
    }`;
  } catch {
    return `ethanConversation:${CONVERSATION_CACHE_VERSION}:user`;
  }
}

function hasLegacyResponse(messages: ChatMessage[]) {
  const normalizedMessages = messages.map((message) =>
    normalizeConversationText(message.content)
  );

  return normalizedMessages.some((content) =>
    LEGACY_RESPONSE_PATTERNS.some((pattern) =>
      content.includes(normalizeConversationText(pattern))
    )
  );
}

function isLegacyAssistantText(content?: string) {
  if (!content) return false;
  return hasLegacyResponse([{ role: "assistant", content }]);
}

function clearConversationCache() {
  if (typeof window === "undefined") return;

  Object.keys(localStorage)
    .filter((key) => key.startsWith("ethanConversation:"))
    .forEach((key) => localStorage.removeItem(key));
}

function trimMessages(messages: ChatMessage[]) {
  if (messages.length <= MAX_CACHED_MESSAGES) return messages;

  return messages.slice(-MAX_CACHED_MESSAGES);
}

function readCachedMessages() {
  if (typeof window === "undefined") return initialMessages;

  try {
    const raw = localStorage.getItem(getUserCacheKey());
    if (!raw) return initialMessages;

    const cached = JSON.parse(raw) as CachedConversation;
    if (
      cached.version !== CONVERSATION_CACHE_VERSION ||
      !cached.updatedAt ||
      Date.now() - cached.updatedAt > CACHE_TTL_MS ||
      !Array.isArray(cached.messages) ||
      hasLegacyResponse(cached.messages)
    ) {
      clearConversationCache();
      return initialMessages;
    }

    return cached.messages.length > 0
      ? trimMessages(cached.messages)
      : initialMessages;
  } catch {
    return initialMessages;
  }
}

function writeCachedMessages(messages: ChatMessage[]) {
  if (typeof window === "undefined") return;

  const payload: CachedConversation = {
    version: CONVERSATION_CACHE_VERSION,
    updatedAt: Date.now(),
    messages: trimMessages(messages),
  };

  localStorage.setItem(getUserCacheKey(), JSON.stringify(payload));
}

async function requestAdvisorResponse(
  token: string | null,
  question: string,
  bypassCache = false
) {
  return apiRequest<AdvisorResponse>("/advisor/core", token, {
    method: "POST",
    headers: {
      "Cache-Control": "no-store",
      "X-Ethan-Client-Version": CONVERSATION_CACHE_VERSION,
    },
    body: JSON.stringify({ message: question, bypass_cache: bypassCache }),
  });
}

export default function AdvisorChat({ compact = false }: { compact?: boolean }) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [cacheReady, setCacheReady] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setMessages(readCachedMessages());
      setCacheReady(true);
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!cacheReady) return;
    if (hasLegacyResponse(messages)) {
      clearConversationCache();
      return;
    }
    writeCachedMessages(messages);
  }, [cacheReady, messages]);

  const clearConversation = () => {
    clearConversationCache();
    setMessages(initialMessages);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();

    const question = input.trim();
    if (!question || loading) return;

    setErrorMessage("");
    setMessages((current) => [...current, { role: "user", content: question }]);
    setInput("");
    setLoading(true);

    try {
      const data = await requestAdvisorResponse(token, question);
      let analysis = data.analysis || "";

      if (isLegacyAssistantText(analysis)) {
        clearConversationCache();
        const refreshed = await requestAdvisorResponse(token, question, true);
        analysis = refreshed.analysis || "";
      }

      if (!analysis || isLegacyAssistantText(analysis)) {
        throw new Error("Contrat Ethan invalide");
      }

      setMessages((current) => [
        ...current,
        { role: "assistant", content: analysis },
      ]);
    } catch (err) {
      console.error(err);
      setErrorMessage("Connexion au moteur indisponible pour le moment.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-zinc-950 border border-white/10 rounded-2xl p-4 shadow-2xl shadow-black/20 transition sm:p-6">
      <div className="mb-4">
        <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
          Conseiller Patrimonial
        </p>
        <div className="mt-1 flex items-center justify-between gap-3">
          <h2 className="text-2xl font-black">Ethan</h2>
          {messages.length > 0 && (
            <button
              type="button"
              onClick={clearConversation}
              className="rounded-full border border-white/10 px-3 py-1 text-xs text-gray-400 transition hover:border-red-400/40 hover:text-red-200"
            >
              Effacer
            </button>
          )}
        </div>
        <p className="text-sm text-gray-400">
          Un regard calme pour transformer ton contexte en decisions simples.
        </p>
      </div>

      <div
        className={`overflow-y-auto rounded-2xl border border-white/10 bg-black/40 p-3 space-y-3 sm:p-4 ${
          compact ? "h-72 sm:h-80" : "h-[58vh] min-h-[460px]"
        }`}
      >
        {messages.length === 0 && (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-gray-400">
            Pose une question sur ton patrimoine, tes risques, tes opportunites ou ta prochaine action utile.
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`flex ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                message.role === "user"
                  ? "bg-[#3fa9f5] text-white"
                  : "bg-white/10 text-gray-200"
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="text-sm text-gray-400">Ethan reflechit...</div>
        )}

        {errorMessage && (
          <div className="rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {errorMessage}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ex: ou suis-je trop expose ?"
          className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black px-4 py-3 text-white placeholder:text-gray-500 focus:outline-none focus:border-[#3fa9f5]"
        />

        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-xl bg-[#3fa9f5] px-5 py-3 font-semibold text-white disabled:opacity-50"
        >
          Demander
        </button>
      </form>
    </section>
  );
}
