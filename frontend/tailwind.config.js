/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Tatvic Brand Colors
        tatvic: {
          blue: '#1A3B5D',
          orange: '#F29100',
          'orange-dark': '#D97F00',
          background: '#FFFFFF',
          'background-alt': '#F8F9FA',
          'text-heading': '#111111',
          'text-body': '#444444',
        },
      },
      fontFamily: {
        // Tatvic Brand Typography
        poppins: ['Poppins', 'sans-serif'],
        roboto: ['Roboto', 'sans-serif'],
      },
      boxShadow: {
        'tatvic-card': '0 2px 8px rgba(0, 0, 0, 0.08)',
        'tatvic-card-hover': '0 4px 16px rgba(0, 0, 0, 0.12)',
      },
    },
  },
  plugins: [],
}
