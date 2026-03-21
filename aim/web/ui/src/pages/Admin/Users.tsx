import React, { useEffect, useState } from 'react';

import { getBasePath } from 'config/config';

import './Users.scss';

interface AdminUser {
  id: number;
  username: string;
  is_admin: boolean;
  created_at: string;
}

function AdminUsers(): React.FunctionComponentElement<React.ReactNode> {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [resetUserId, setResetUserId] = useState<number | null>(null);
  const [resetPassword, setResetPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const authHeader = localStorage.getItem('Auth') || '';

  const fetchUsers = async () => {
    const basePath = getBasePath();
    const resp = await fetch(`${basePath}/api/admin/users`, {
      headers: { Authorization: authHeader },
    });
    if (resp.ok) {
      setUsers(await resp.json());
    } else if (resp.status === 403) {
      setError('Admin access required');
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      const basePath = getBasePath();
      const resp = await fetch(`${basePath}/api/admin/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: authHeader,
        },
        body: JSON.stringify({
          username: newUsername.trim(),
          password: newPassword,
          is_admin: newIsAdmin,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.detail || 'Failed to create user');
        return;
      }
      setSuccess(`User "${data.username}" created`);
      setNewUsername('');
      setNewPassword('');
      setNewIsAdmin(false);
      await fetchUsers();
    } catch {
      setError('Failed to create user');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (resetUserId === null) return;
    setError('');
    setSuccess('');
    const basePath = getBasePath();
    const resp = await fetch(
      `${basePath}/api/admin/users/${resetUserId}/reset-password`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: authHeader,
        },
        body: JSON.stringify({ password: resetPassword }),
      },
    );
    if (resp.ok) {
      setSuccess('Password reset successfully');
      setResetUserId(null);
      setResetPassword('');
    } else {
      setError('Failed to reset password');
    }
  };

  return (
    <div className='AdminUsers'>
      <h1 className='AdminUsers__title'>User Management</h1>

      {error && <p className='AdminUsers__error'>{error}</p>}
      {success && <p className='AdminUsers__success'>{success}</p>}

      <section className='AdminUsers__section'>
        <h2>Users</h2>
        <table className='AdminUsers__table'>
          <thead>
            <tr>
              <th>Username</th>
              <th>Admin</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 && (
              <tr>
                <td colSpan={4} className='AdminUsers__table__empty'>
                  No users found.
                </td>
              </tr>
            )}
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.is_admin ? 'Yes' : 'No'}</td>
                <td>{u.created_at}</td>
                <td>
                  <button
                    className='AdminUsers__button AdminUsers__button--secondary'
                    onClick={() => {
                      setResetUserId(u.id);
                      setResetPassword('');
                    }}
                  >
                    Reset password
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {resetUserId !== null && (
        <section className='AdminUsers__section'>
          <h2>
            Reset password for user ID {resetUserId}
          </h2>
          <form onSubmit={handleResetPassword}>
            <div className='AdminUsers__form-row'>
              <input
                type='password'
                placeholder='New password'
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
                required
              />
              <button type='submit' className='AdminUsers__button'>
                Reset
              </button>
              <button
                type='button'
                className='AdminUsers__button AdminUsers__button--ghost'
                onClick={() => setResetUserId(null)}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <section className='AdminUsers__section'>
        <h2>Create new user</h2>
        <form onSubmit={handleCreate}>
          <div className='AdminUsers__form-row'>
            <input
              type='text'
              placeholder='Username'
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              required
            />
            <input
              type='password'
              placeholder='Password'
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
            <label className='AdminUsers__checkbox'>
              <input
                type='checkbox'
                checked={newIsAdmin}
                onChange={(e) => setNewIsAdmin(e.target.checked)}
              />
              Admin
            </label>
            <button
              type='submit'
              className='AdminUsers__button'
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default AdminUsers;
