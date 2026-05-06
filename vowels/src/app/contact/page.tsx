"use client";

import { FormEvent, useState } from "react";

const CONTACT_TYPES = [
  { value: "", label: "Select a topic…" },
  { value: "editorial", label: "Editorial" },
  { value: "sponsorships", label: "Sponsorships" },
  { value: "general", label: "General" },
];

export default function ContactPage() {
  const [form, setForm] = useState({ name: "", email: "", type: "", message: "" });
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const set = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (sending || !form.type) return;
    setSending(true);
    setError("");

    try {
      const resp = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.email.trim(),
          first_name: form.name.trim().split(" ")[0] ?? "",
          last_name: form.name.trim().split(" ").slice(1).join(" ") ?? "",
          source: `vowels-contact-${form.type}`,
          utm_content: form.message.trim().slice(0, 500),
        }),
      });

      if (!resp.ok) throw new Error(`${resp.status}`);
      setSent(true);
      setForm({ name: "", email: "", type: "", message: "" });
    } catch {
      setError("Something went wrong. Please try again or email us at info@vowels.org");
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="font-serif text-4xl text-slate-900">Contact Us</h1>
      <p className="mt-3 text-slate-600">
        Have a question, pitch, or partnership inquiry? Fill out the form below and we will get back to you.
      </p>

      {sent ? (
        <div className="mt-8 rounded-2xl border border-emerald-200 bg-emerald-50 px-6 py-8 text-center">
          <p className="text-lg font-semibold text-emerald-800">Message received!</p>
          <p className="mt-2 text-sm text-emerald-700">We will be in touch soon.</p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold uppercase tracking-widest text-slate-500">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              required
              placeholder="Your name"
              className="rounded-full border border-black/15 bg-white px-4 py-3 text-sm text-black outline-none focus:border-brand"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold uppercase tracking-widest text-slate-500">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              required
              placeholder="you@example.com"
              className="rounded-full border border-black/15 bg-white px-4 py-3 text-sm text-black outline-none focus:border-brand"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold uppercase tracking-widest text-slate-500">Topic</label>
            <select
              value={form.type}
              onChange={(e) => set("type", e.target.value)}
              required
              className="rounded-full border border-black/15 bg-white px-4 py-3 text-sm text-black outline-none focus:border-brand"
            >
              {CONTACT_TYPES.map((t) => (
                <option key={t.value} value={t.value} disabled={t.value === ""}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold uppercase tracking-widest text-slate-500">Message</label>
            <textarea
              value={form.message}
              onChange={(e) => set("message", e.target.value)}
              required
              rows={5}
              placeholder="Tell us more…"
              className="rounded-2xl border border-black/15 bg-white px-4 py-3 text-sm text-black outline-none focus:border-brand resize-none"
            />
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={sending || !form.type}
            className="self-start rounded-full bg-brand px-8 py-3 text-sm font-bold uppercase tracking-[0.12em] text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60"
          >
            {sending ? "Sending…" : "Send Message"}
          </button>
        </form>
      )}
    </section>
  );
}
