import React, { useEffect, useState } from 'react';

import { getBasePath } from 'config/config';

import './Settings.scss';

interface ApiToken {
  id: number;
  name: string;
  created_at: string;
}

function Settings(): React.FunctionComponentElement<React.ReactNode> {
  const [tokens, setTokens] = useState<ApiToken[]>([]);
  const [newTokenName, setNewTokenName] = useState('');
  const [createdToken, setCreatedToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
        setError('Failed to create token');
        return;
      }
      const data = await resp.json();
      setCreatedToken(data.token);
      setNewTokenName('');
      await fetchTokens();
    } catch {
      setError('Failed to create token');
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

  return (
    <div className='Settings'>
      <h1 className='Settings__title'>Settings</h1>

      <section className='Settings__section'>
        <h2 className='Settings__section__title'>API Tokens</h2>

        {createdToken && (
          <div className='Settings__token-reveal'>
            <p>
              Your new token (copy it now — it won&apos;t be shown again):
            </p>
            <code className='Settings__token-reveal__value'>{createdToken}</code>
            <button
              className='Settings__button Settings__button--secondary'
              onClick={() => navigator.clipboard.writeText(createdToken)}
            >
              Copy
            </button>
            <button
              className='Settings__button Settings__button--ghost'
              onClick={() => setCreatedToken('')}
            >
              Dismiss
            </button>
          </div>
        )}

        <table className='Settings__table'>
          <thead>
            <tr>
              <th>Name</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tokens.length === 0 && (
              <tr>
                <td colSpan={3} className='Settings__table__empty'>
                  No API tokens yet.
                </td>
              </tr>
            )}
            {tokens.map((t) => (
              <tr key={t.id}>
                <td>{t.name}</td>
                <td>{t.created_at}</td>
                <td>
                  <button
                    className='Settings__button Settings__button--danger'
                    onClick={() => handleDelete(t.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <form className='Settings__create-form' onSubmit={handleCreate}>
          <h3>Create new token</h3>
          <div className='Settings__create-form__row'>
            <input
              type='text'
              placeholder='Token name'
              value={newTokenName}
              onChange={(e) => setNewTokenName(e.target.value)}
              required
            />
            <button
              type='submit'
              className='Settings__button'
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create'}
            </button>
          </div>
          {error && <p className='Settings__error'>{error}</p>}
        </form>
      </section>
    </div>
  );
}

export default Settings;
