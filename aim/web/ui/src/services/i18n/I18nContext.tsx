import React, { createContext, useContext, useState, useCallback } from 'react';

import en from './en';
import zh from './zh';

type Locale = 'en' | 'zh';
type Translations = typeof en;

const translations: Record<Locale, Translations> = { en, zh };

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string>) => string;
}

const I18nContext = createContext<I18nContextValue>({
  locale: 'zh',
  setLocale: () => {},
  t: (key: string) => key,
});

const LOCALE_KEY = 'aim_locale';

export function I18nProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const saved = localStorage.getItem(LOCALE_KEY);
    return saved === 'en' || saved === 'zh' ? saved : 'zh';
  });

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    localStorage.setItem(LOCALE_KEY, newLocale);
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string>) => {
      let text = (translations[locale] as Record<string, string>)[key] || key;
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          text = text.replace(`{${k}}`, v);
        });
      }
      return text;
    },
    [locale],
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}

export default I18nContext;
