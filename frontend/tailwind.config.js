/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        void: {
          DEFAULT: "#0A0C12",
          soft: "#0F131C",
          surface: "#141924",
          raised: "#1A2130",
          line: "#232B3D",
        },
        ink: {
          DEFAULT: "#E9ECF4",
          dim: "#9AA4BC",
          faint: "#5C6680",
        },
        signal: {
          DEFAULT: "#FF5A36",
          soft: "#FF7A56",
          dim: "#7A2E1C",
        },
        verified: {
          DEFAULT: "#2FD9C4",
          soft: "#5EE8D8",
          dim: "#12564D",
        },
        gold: {
          DEFAULT: "#C9A227",
          soft: "#E3C158",
          dim: "#4A3C13",
        },
        amber: {
          DEFAULT: "#F0B429",
        },
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      backgroundImage: {
        hexgrid: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='56' height='100' viewBox='0 0 56 100'%3E%3Cg fill='none' stroke='%23232B3D' stroke-width='1'%3E%3Cpath d='M28 0 L56 14.5 L56 43.5 L28 58 L0 43.5 L0 14.5 Z'/%3E%3Cpath d='M28 58 L56 72.5 L56 100'/%3E%3Cpath d='M28 58 L0 72.5 L0 100'/%3E%3C/g%3E%3C/svg%3E\")",
      },
      keyframes: {
        radar: {
          "0%": { transform: "rotate(0deg)", opacity: 0.9 },
          "100%": { transform: "rotate(360deg)", opacity: 0.9 },
        },
        ping2: {
          "0%": { transform: "scale(0.6)", opacity: 0.8 },
          "80%": { transform: "scale(2.6)", opacity: 0 },
          "100%": { transform: "scale(2.6)", opacity: 0 },
        },
        rise: {
          "0%": { transform: "translateY(14px)", opacity: 0 },
          "100%": { transform: "translateY(0)", opacity: 1 },
        },
        scanline: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        flicker: {
          "0%,100%": { opacity: 1 },
          "50%": { opacity: 0.55 },
        },
      },
      animation: {
        radar: "radar 4s linear infinite",
        ping2: "ping2 2.2s cubic-bezier(0,0,0.2,1) infinite",
        rise: "rise 0.5s cubic-bezier(0.16,1,0.3,1) both",
        scanline: "scanline 3s linear infinite",
        flicker: "flicker 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
