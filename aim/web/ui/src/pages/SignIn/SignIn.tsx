import React, { useState } from 'react';

import { getBasePath } from 'config/config';

import ENDPOINTS from 'services/api/endpoints';
import { useI18n } from 'services/i18n';

import './SignIn.scss';

function SignIn(): React.FunctionComponentElement<React.ReactNode> {
  const { t } = useI18n();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const basePath = getBasePath();
      const response = await fetch(
        `${basePath}/api/${ENDPOINTS.AUTH.BASE}/${ENDPOINTS.AUTH.LOGIN}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password }),
        },
      );

      if (!response.ok) {
        setError(t('signIn.error'));
        setLoading(false);
        return;
      }

      const data = await response.json();
      localStorage.setItem('Auth', `${data.token_type} ${data.access_token}`);
      localStorage.setItem('token', data.refresh_token);

      window.location.assign(`${getBasePath() || ''}/`);
    } catch (err) {
      setError(t('signIn.failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className='SignIn'>
      <div className='SignIn__card'>
        <h2 className='SignIn__title'>{t('signIn.title')}</h2>
        <form onSubmit={handleSubmit}>
          <div className='SignIn__field'>
            <label htmlFor='username'>{t('signIn.username')}</label>
            <input
              id='username'
              type='text'
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className='SignIn__field'>
            <label htmlFor='password'>{t('signIn.password')}</label>
            <input
              id='password'
              type='password'
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className='SignIn__error'>{error}</p>}
          <button type='submit' className='SignIn__button' disabled={loading}>
            {loading ? t('signIn.loading') : t('signIn.button')}
          </button>
        </form>
      </div>
    </div>
  );
}

export default SignIn;
