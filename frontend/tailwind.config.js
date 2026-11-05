/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sanrafael: {
          50: '#f2f8f5',
          100: '#e2f0ea',
          200: '#c5e0d5',
          300: '#9bc9b7',
          400: '#6aab94',
          500: '#458d76',
          600: '#2f715d',
          700: '#225a4a',
          800: '#146a59',
          900: '#103f35',
          950: '#0a2a23',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
      boxShadow: {
        tarjeta: '0 18px 40px -28px rgba(16, 63, 53, 0.55)',
      },
    },
  },
  plugins: [],
};
