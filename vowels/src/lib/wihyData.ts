export interface DataInsight {
  label: string;
  value: string;
  note: string;
}

export const weeklyInsights: DataInsight[] = [
  {
    label: "Ultra-processed exposure",
    value: "+28%",
    note: "Higher exposure in low-cost carts this week.",
  },
  {
    label: "Label confusion",
    value: "41%",
    note: "Readers misread at least one front-label claim.",
  },
  {
    label: "Evidence explainer lift",
    value: "3.7x",
    note: "Data-backed stories outperform opinion-only posts.",
  },
];
