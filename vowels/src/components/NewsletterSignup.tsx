"use client";

import { FormEvent, useState } from "react";

import { trackEvent } from "@/lib/analytics";

export function NewsletterSignup() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    trackEvent({ name: "newsletter_signup", params: { location: "homepage" } });
    setSent(true);
    setEmail("");
  };

  return (
    <section className="news-card p-5">
      <h3 className="font-serif text-2xl text-slate-900">Get the weekly data briefing</h3>
      <p className="mt-2 text-sm text-slate-600">Evidence-backed headlines and practical nutrition actions.</p>
      <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          placeholder="you@example.com"
          className="w-full rounded-xl border border-sky-200 px-3 py-2 text-sm outline-none focus:border-newsroom"
        />
        <button className="rounded-xl bg-newsroom px-4 py-2 text-sm font-semibold text-white" type="submit">
          Subscribe
        </button>
      </form>
      {sent ? <p className="mt-3 text-xs text-emerald-700">Thanks. You are subscribed.</p> : null}
    </section>
  );
}
