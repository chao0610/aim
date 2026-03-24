import React, { useEffect, useState } from 'react';

import { getBasePath } from 'config/config';

import { useI18n } from 'services/i18n';

import './Settings.scss';

interface ApiToken {
  id: number;
  name: string;
  created_at: string;
}

function Settings(): React.FunctionComponentElement<React.ReactNode> {
  const { t } = useI18n();
  const [tokens, setTokens] = useState<ApiToken[]>([]);
  const [newTokenName, setNewTokenName] = useState('');
  const [createdToken, setCreatedToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState('');
  const [pwLoading, setPwLoading] = useState(false);

  const authHeader = localStorage.getItem('Auth') || '';

  const fetchTokens = async () => {
    const basePath = getBasePath();
    const resp = await fetch(`${basePath}/api/settings/tokens`, {
      headers: { Authorization: authHeader },
    });
    if (resp.ok) {
      setTokens(await resp.json());
    }
  };

  useEffect(() => {
    fetchTokens();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setCreatedToken('');
    if (!newTokenName.trim()) return;
    setLoading(true);
    try {
      const basePath = getBasePath();
      const resp = await fetch(`${basePath}/api/settings/tokens`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: authHeader,
        },
        body: JSON.stringify({ name: newTokenName.trim() }),
      });
      if (!resp.ok) {
        setError(t('settings.createFailed'));
        return;
      }
      const data = await resp.json();
      setCreatedToken(data.token);
      setNewTokenName('');
      await fetchTokens();
    } catch {
      setError(t('settings.createFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (tokenId: number) => {
    const basePath = getBasePath();
    const resp = await fetch(`${basePath}/api/settings/tokens/${tokenId}`, {
      method: 'DELETE',
      headers: { Authorization: authHeader },
    });
    if (resp.ok || resp.status === 204) {
      await fetchTokens();
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError('');
    setPwSuccess('');
    if (newPassword.length < 8) {
      setPwError(t('settings.passwordMinLength'));
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwError(t('settings.passwordMismatch'));
      return;
    }
    setPwLoading(true);
    try {
      const basePath = getBasePath();
      const resp = await fetch(`${basePath}/api/settings/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: authHeader,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        setPwError(data.detail || t('settings.passwordFailed'));
        return;
      }
      setPwSuccess(t('settings.passwordChanged'));
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch {
      setPwError(t('settings.passwordFailed'));
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <div className='Settings'>
      <h1 className='Settings__title'>{t('settings.title')}</h1>

      <section className='Settings__section'>
        <h2 className='Settings__section__title'>{t('settings.apiTokens')}</h2>

        {createdToken && (
          <div className='Settings__token-reveal'>
            <p>{t('settings.tokenReveal')}</p>
            <code className='Settings__token-reveal__value'>
              {createdToken}
            </code>
            <button
              className='Settings__button Settings__button--secondary'
              onClick={() => navigator.clipboard.writeText(createdToken)}
            >
              {t('settings.copy')}
            </button>
            <button
              className='Settings__button Settings__button--ghost'
              onClick={() => setCreatedToken('')}
            >
              {t('settings.dismiss')}
            </button>
          </div>
        )}

        <table className='Settings__table'>
          <thead>
            <tr>
              <th>{t('settings.tokenName')}</th>
              <th>{t('settings.tokenCreated')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tokens.length === 0 && (
              <tr>
                <td colSpan={3} className='Settings__table__empty'>
                  {t('settings.noTokens')}
                </td>
              </tr>
            )}
            {tokens.map((tk) => (
              <tr key={tk.id}>
                <td>{tk.name}</td>
                <td>{tk.created_at}</td>
                <td>
                  <button
                    className='Settings__button Settings__button--danger'
                    onClick={() => handleDelete(tk.id)}
                  >
                    {t('settings.delete')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <form className='Settings__create-form' onSubmit={handleCreate}>
          <h3>{t('settings.createToken')}</h3>
          <div className='Settings__create-form__row'>
            <input
              type='text'
              placeholder={t('settings.tokenPlaceholder')}
              value={newTokenName}
              onChange={(e) => setNewTokenName(e.target.value)}
              required
            />
            <button
              type='submit'
              className='Settings__button'
              disabled={loading}
            >
              {loading ? t('settings.creating') : t('settings.create')}
            </button>
          </div>
          {error && <p className='Settings__error'>{error}</p>}
        </form>
      </section>

      <section className='Settings__section'>
        <h2 className='Settings__section__title'>
          {t('settings.changePassword')}
        </h2>
        <form className='Settings__create-form' onSubmit={handleChangePassword}>
          <div className='Settings__field'>
            <label htmlFor='currentPassword'>
              {t('settings.currentPassword')}
            </label>
            <input
              id='currentPassword'
              type='password'
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className='Settings__field'>
            <label htmlFor='newPassword'>{t('settings.newPassword')}</label>
            <input
              id='newPassword'
              type='password'
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <div className='Settings__field'>
            <label htmlFor='confirmPassword'>
              {t('settings.confirmPassword')}
            </label>
            <input
              id='confirmPassword'
              type='password'
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          {pwError && <p className='Settings__error'>{pwError}</p>}
          {pwSuccess && <p className='Settings__success'>{pwSuccess}</p>}
          <button
            type='submit'
            className='Settings__button'
            disabled={pwLoading}
          >
            {pwLoading ? t('settings.changing') : t('settings.changePassword')}
          </button>
        </form>
      </section>
    </div>
  );
}

export default Settings;
