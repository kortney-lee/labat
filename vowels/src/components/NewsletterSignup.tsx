"use client";

import { FormEvent, useState } from "react";

import { trackEvent } from "@/lib/analytics";

export function NewsletterSignup() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const value = email.trim();
    if (!value || sending) return;

    setSending(true);
    setError("");

    try {
      const resp = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: value,
          source: "vowels-newsletter",
          referral_url: typeof window !== "undefined" ? window.location.href : "",
        }),
      });

      if (!resp.ok) {
        throw new Error(`Signup failed: ${resp.status}`);
      }

      trackEvent({ name: "newsletter_signup", params: { location: "homepage" } });
      setSent(true);
      setEmail("");
    } catch {
      setError("We could not subscribe you right now. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="news-card p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Newsletter</p>
      <h3 className="mt-3 font-serif text-3xl leading-tight text-slate-950">Get the weekly data briefing</h3>
      <p className="mt-3 text-sm text-slate-700">Evidence-backed headlines and practical nutrition actions.</p>
      <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          placeholder="you@example.com"
          className="w-full rounded-full border border-black/15 bg-mist px-4 py-3 text-sm text-black outline-none focus:border-brand"
        />
        <button
          className="rounded-full bg-brand px-5 py-3 text-sm font-bold uppercase tracking-[0.12em] text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60"
          type="submit"
          disabled={sending}
        >
          {sending ? "Sending..." : "Subscribe"}
        </button>
      </form>
      {sent ? <p className="mt-3 text-xs text-emerald-700">Thanks. You are subscribed.</p> : null}
      {error ? <p className="mt-3 text-xs text-red-600">{error}</p> : null}
    </section>
  );
}
