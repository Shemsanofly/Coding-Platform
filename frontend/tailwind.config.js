/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["selector", ".student-theme-root:not(.student-theme-light)"],
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Space Grotesk"', '"Segoe UI"', "sans-serif"],
      },
      colors: {
        ocean: {
          200: "#bfe0ec",
          600: "#15608d",
          700: "#13658f",
          800: "#0f4c75",
          900: "#14384c",
          950: "#102c3d",
        },
        coral: "#ff6f61",
        spice: "#d9a441",
        sand: "#f7efe6",
        reef: "#d8eef6",
        ink: "#10212f",
        muted: "#5d6b78",
        line: "#d6e2ea",
        cream: "#fffdf9",
      },
      boxShadow: {
        panel: "0 16px 34px rgba(16, 33, 47, 0.08)",
        card: "0 22px 44px rgba(16, 33, 47, 0.1)",
        primary: "0 12px 24px rgba(21, 96, 141, 0.24)",
      },
      borderRadius: {
        "4xl": "1.75rem",
      },
      backgroundImage: {
        "lc-page":
          "radial-gradient(circle at 10% 12%, rgba(21, 96, 141, 0.14), transparent 40%), radial-gradient(circle at 85% 12%, rgba(255, 111, 97, 0.13), transparent 45%), linear-gradient(135deg, #fdf8ef, #ffffff 55%, #f3e6db)",
        "lc-page-dark":
          "radial-gradient(circle at 12% 10%, rgba(21, 96, 141, 0.18), transparent 34%), radial-gradient(circle at 88% 0%, rgba(217, 164, 65, 0.10), transparent 32%), linear-gradient(135deg, #101923, #142230 52%, #172a36)",
        "lc-auth":
          "radial-gradient(circle at top left, rgba(21, 96, 141, 0.22), transparent 42%), radial-gradient(circle at 80% 20%, rgba(255, 111, 97, 0.18), transparent 48%), linear-gradient(120deg, #fdf8ef, #ffffff 55%, #f4ddd6)",
        "lc-primary": "linear-gradient(120deg, #ff6f61, #15608d)",
        "lc-progress": "linear-gradient(90deg, #ff6f61, #15608d)",
        "lc-sidebar":
          "linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(247, 239, 230, 0.92) 100%)",
      },
    },
  },
  plugins: [],
};
