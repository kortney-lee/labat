"use client";

import Link from "next/link";

import { trackEvent } from "@/lib/analytics";

interface CTAButtonProps {
  href: string;
  label: string;
  eventLabel: string;
}

export function CTAButton({ href, label, eventLabel }: CTAButtonProps) {
  return (
    <Link
      href={href}
      onClick={() => trackEvent({ name: "cta_click", params: { label: eventLabel } })}
      className="inline-flex items-center rounded-full bg-brand px-5 py-3 text-sm font-bold uppercase tracking-[0.12em] text-white transition hover:-translate-y-0.5 hover:bg-black"
    >
      {label}
    </Link>
  );
}
