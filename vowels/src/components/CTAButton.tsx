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
      className="inline-flex items-center rounded-xl bg-gradient-to-r from-newsroom to-sky-500 px-4 py-2 text-sm font-semibold text-white"
    >
      {label}
    </Link>
  );
}
