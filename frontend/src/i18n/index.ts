import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation files
import enCommon from './locales/en/common.json';
import enNav from './locales/en/nav.json';
import enStrategy from './locales/en/strategy.json';
import enBacktest from './locales/en/backtest.json';
import enDashboard from './locales/en/dashboard.json';

import guCommon from './locales/gu/common.json';
import guNav from './locales/gu/nav.json';
import guStrategy from './locales/gu/strategy.json';
import guBacktest from './locales/gu/backtest.json';
import guDashboard from './locales/gu/dashboard.json';

// Define available languages
export const languages = [
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸' },
  { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી', flag: '🇮🇳' },
] as const;

export type LanguageCode = typeof languages[number]['code'];

// Combine namespaces for each language
const resources = {
  en: {
    common: enCommon,
    nav: enNav,
    strategy: enStrategy,
    backtest: enBacktest,
    dashboard: enDashboard,
  },
  gu: {
    common: guCommon,
    nav: guNav,
    strategy: guStrategy,
    backtest: guBacktest,
    dashboard: guDashboard,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    defaultNS: 'common',
    ns: ['common', 'nav', 'strategy', 'backtest', 'dashboard'],
    
    interpolation: {
      escapeValue: false, // React already escapes
    },
    
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'pathvest_language',
    },
  });

export default i18n;

