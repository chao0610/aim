import React, { useState } from 'react';

import { getBasePath } from 'config/config';

import ENDPOINTS from 'services/api/endpoints';

import './SignIn.scss';

function SignIn(): React.FunctionComponentElement<React.ReactNode> {
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
        setError('Invalid username or password');
        setLoading(false);
        return;
      }

      const data = await response.json();
      localStorage.setItem('Auth', `${data.token_type} ${data.access_token}`);

      // Store refresh token in localStorage (not cookie — per design spec)
      localStorage.setItem('token', data.refresh_token);

      window.location.assign(getBasePath() || '/');
    } catch (err) {
      setError('Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className='SignIn'>
      <div className='SignIn__card'>
        <h2 className='SignIn__title'>Sign in to Aim</h2>
        <form onSubmit={handleSubmit}>
          <div className='SignIn__field'>
            <label htmlFor='username'>Username</label>
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
            <label htmlFor='password'>Password</label>
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
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default SignIn;
