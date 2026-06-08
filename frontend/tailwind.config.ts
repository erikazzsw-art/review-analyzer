import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "var(--canvas)",
        card: "var(--card)",
        ink: "var(--ink)",
        soft: "var(--soft)",
        line: "var(--line)",
        rose: "var(--rose)",
        roseSoft: "var(--rose-soft)",
        lavender: "var(--lavender)",
        mint: "var(--mint)",
      },
      fontFamily: {
        body: ["var(--font-body)"],
        heading: ["var(--font-heading)"],
      },
      boxShadow: {
        card: "var(--shadow-card)",
        glow: "var(--shadow-glow)",
      },
      borderRadius: {
        shell: "var(--radius-shell)",
        card: "var(--radius-card)",
        pill: "999px",
      },
      backgroundImage: {
        "hero-wash":
          "radial-gradient(circle at top left, rgba(243,111,143,0.18), transparent 32%), radial-gradient(circle at bottom right, rgba(141,123,232,0.18), transparent 28%), linear-gradient(180deg, #fffaf8 0%, #fff6f7 54%, #f8f4ff 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
