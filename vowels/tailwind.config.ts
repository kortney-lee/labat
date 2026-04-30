import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f5f1e8",
        brand: "#ff6a00",
        newsroom: "#ff6a00",
        ink: "#131313",
        coal: "#111319",
        sand: "#ece6da",
        sage: "#edf4ef",
        mist: "#f2f5f7",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["var(--font-display)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        news: "0 10px 40px rgba(17, 19, 25, 0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
