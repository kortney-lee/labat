/**
 * promptLibrary.ts — Pre-built prompt templates for common graphic types.
 */

export interface PromptTemplate {
  id: string;
  name: string;
  prompt: string;
  suggestedTemplate: string;
}

export const PROMPT_LIBRARY: PromptTemplate[] = [
  {
    id: "daily_hook",
    name: "Daily Health Hook",
    prompt:
      "Create a bold, scroll-stopping health fact that makes people rethink their daily food choices. Focus on hidden ingredients, misleading labels, or surprising nutrition facts.",
    suggestedTemplate: "editorial_signal",
  },
  {
    id: "ingredient_expose",
    name: "Ingredient Exposé",
    prompt:
      "Create content exposing a common processed food ingredient. Show what it really is and why consumers should care. Be factual, not fear-mongering.",
    suggestedTemplate: "wihy_signal_clean",
  },
  {
    id: "swap_comparison",
    name: "Food Swap Comparison",
    prompt:
      "Create a side-by-side comparison of a common unhealthy food choice vs a healthier alternative. Include 4-5 items on each side.",
    suggestedTemplate: "wihy_signal_clean",
  },
  {
    id: "nutrition_myth",
    name: "Nutrition Myth Buster",
    prompt:
      "Bust a common nutrition myth. Create a quote-style graphic with a surprising truth that challenges conventional wisdom.",
    suggestedTemplate: "editorial_signal",
  },
  {
    id: "app_download",
    name: "App Download CTA",
    prompt:
      "Create a compelling call-to-action for downloading the WIHY app. Focus on the benefit of scanning food products to know what you're really eating.",
    suggestedTemplate: "app_showcase",
  },
  {
    id: "label_reading",
    name: "Label Reading Tip",
    prompt:
      "Create educational content about how to read food labels better. One specific, actionable tip.",
    suggestedTemplate: "stat_pulse",
  },
];

/** Look up a prompt by ID. */
export function getPromptById(id: string): PromptTemplate | undefined {
  return PROMPT_LIBRARY.find((p) => p.id === id);
}
