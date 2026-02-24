module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  safelist: [
    'bg-blue-500',
    'bg-purple-500',
    'bg-green-500',
    'bg-orange-500',
    'bg-red-500',
    'bg-slate-700',
    'bg-slate-800',
    'bg-red-600',
    'border-blue-700',
    'border-purple-700',
    'border-green-700',
    'border-orange-700',
    'border-red-700',
    'border-red-800',
    'border-slate-800',
    'border-transparent',
    'text-white',
    'ring-2',
    'ring-white/80',
    'ring-offset-2',
    'ring-offset-slate-950',
    'rounded-xl',
    'shadow-md'
  ],
  theme: {
    extend: {
      animation: {
        fadeIn: 'fadeIn 0.5s ease-in-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateX(-10px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
}
