import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#070b16",
          900: "#0b1224",
          850: "#101a31",
          800: "#16233d"
        },
        ow: {
          orange: "#f99e1a",
          amber: "#ffd27a",
          cyan: "#61d8ff",
          steel: "#8ca3c7"
        }
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(249,158,26,.18), 0 18px 60px rgba(0,0,0,.35)"
      }
    }
  },
  plugins: []
};

export default config;
