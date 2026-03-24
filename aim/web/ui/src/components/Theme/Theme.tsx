import React from 'react';

import {
  unstable_createMuiStrictModeTheme as createMuiTheme,
  ThemeOptions,
  ThemeProvider,
  StylesProvider,
} from '@material-ui/core';

import { IThemeProps } from 'types/components/Theme/Theme';

export const ThemeContext = React.createContext({});
const { Provider } = ThemeContext;

const light: ThemeOptions = {
  typography: {
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', 'Helvetica Neue', Arial, sans-serif",
  },
  overrides: {
    MuiDivider: {
      root: {
        backgroundColor: '#E5E5EA',
      },
    },
    MuiButton: {
      root: {
        height: 32,
        boxShadow: 'unset',
        borderRadius: 8,
        textTransform: 'none',
      },
      contained: {
        boxShadow: 'unset',
      },
    },
    MuiTooltip: {
      tooltip: {
        borderRadius: 8,
        fontSize: '0.8125rem',
      },
    },
  },
  props: {
    MuiButtonBase: {
      disableRipple: true,
    },
  },
  palette: {
    type: 'light',
    primary: {
      main: '#007AFF',
    },
    secondary: {
      main: '#1D1D1F',
    },
    text: {
      primary: '#1D1D1F',
    },
    background: {
      default: '#FFFFFF',
      paper: '#FFFFFF',
    },
  },
  spacing: (factor: number) => `${factor}em`,
};

const darkTheme: ThemeOptions = {
  palette: {
    type: 'dark',
    primary: {
      main: '#0A84FF',
    },
  },
};

function Theme(
  props: IThemeProps,
): React.FunctionComponentElement<React.ReactNode> {
  const [dark, setDark] = React.useState<boolean>(false);

  const handleTheme = React.useCallback((): void => {
    setDark(!dark);
  }, [dark]);

  const theme = createMuiTheme(dark ? darkTheme : light);
  return (
    <Provider value={{ dark, handleTheme }}>
      <ThemeProvider theme={theme}>
        <StylesProvider injectFirst={true}>{props.children}</StylesProvider>
      </ThemeProvider>
    </Provider>
  );
}

export default Theme;
