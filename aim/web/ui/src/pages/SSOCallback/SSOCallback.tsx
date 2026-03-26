import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

import { getBasePath } from 'config/config';

/**
 * SSO Callback page: receives access_token & refresh_token from URL params,
 * stores them in localStorage, then redirects to dashboard.
 */
function SSOCallback(): React.FunctionComponentElement<React.ReactNode> {
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');
    const tokenType = params.get('token_type') || 'Bearer';

    if (accessToken) {
      localStorage.setItem('Auth', `${tokenType} ${accessToken}`);
    }
    if (refreshToken) {
      localStorage.setItem('RefreshToken', refreshToken);
    }

    // Redirect to dashboard
    window.location.assign(`${getBasePath() || ''}/`);
  }, []);

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '1rem',
        color: '#636366',
      }}
    >
      SSO login...
    </div>
  );
}

export default SSOCallback;
