import React, { useEffect, useState } from 'react';

import { getBasePath } from 'config/config';

import { useI18n } from 'services/i18n';

import './Users.scss';

interface AdminUser {
  id: number;
  username: string;
  is_admin: boolean;
  role: string;
  created_at: string;
}

function AdminUsers(): React.FunctionComponentElement<React.ReactNode> {
  const { t } = useI18n();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('editor');
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
      setError(t('admin.adminRequired'));
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
          is_admin: newRole === 'admin',
          role: newRole,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.detail || t('admin.createFailed'));
        return;
      }
      setSuccess(t('admin.userCreated', { username: data.username }));
      setNewUsername('');
      setNewPassword('');
      setNewRole('editor');
      await fetchUsers();
    } catch {
      setError(t('admin.createFailed'));
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
      setSuccess(t('admin.resetSuccess'));
      setResetUserId(null);
      setResetPassword('');
    } else {
      setError(t('admin.resetFailed'));
    }
  };

  const handleRoleChange = async (userId: number, role: string) => {
    setError('');
    setSuccess('');
    const basePath = getBasePath();
    const resp = await fetch(`${basePath}/api/admin/users/${userId}/role`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader,
      },
      body: JSON.stringify({ role }),
    });
    if (resp.ok) {
      const data = await resp.json();
      setSuccess(t('admin.roleUpdated', { username: data.username }));
      await fetchUsers();
    } else {
      const data = await resp.json().catch(() => ({}));
      setError(data.detail || t('admin.roleFailed'));
    }
  };

  const handleDelete = async (user: AdminUser) => {
    if (
      !window.confirm(t('admin.confirmDelete', { username: user.username }))
    ) {
      return;
    }
    setError('');
    setSuccess('');
    const basePath = getBasePath();
    const resp = await fetch(`${basePath}/api/admin/users/${user.id}`, {
      method: 'DELETE',
      headers: { Authorization: authHeader },
    });
    if (resp.ok) {
      setSuccess(t('admin.deleteSuccess', { username: user.username }));
      await fetchUsers();
    } else {
      const data = await resp.json().catch(() => ({}));
      setError(data.detail || t('admin.deleteFailed'));
    }
  };

  const roleLabel = (role: string) => {
    switch (role) {
      case 'viewer':
        return t('admin.viewer');
      case 'editor':
        return t('admin.editor');
      case 'admin':
        return t('admin.admin');
      default:
        return role;
    }
  };

  return (
    <div className='AdminUsers'>
      <h1 className='AdminUsers__title'>{t('admin.title')}</h1>

      {error && <p className='AdminUsers__error'>{error}</p>}
      {success && <p className='AdminUsers__success'>{success}</p>}

      <section className='AdminUsers__section'>
        <h2>{t('admin.users')}</h2>
        <table className='AdminUsers__table'>
          <thead>
            <tr>
              <th>{t('admin.username')}</th>
              <th>{t('admin.role')}</th>
              <th>{t('admin.created')}</th>
              <th>{t('admin.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 && (
              <tr>
                <td colSpan={4} className='AdminUsers__table__empty'>
                  {t('admin.noUsers')}
                </td>
              </tr>
            )}
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>
                  <select
                    className='AdminUsers__role-select'
                    value={u.role || 'editor'}
                    onChange={(e) => handleRoleChange(u.id, e.target.value)}
                  >
                    <option value='viewer'>{roleLabel('viewer')}</option>
                    <option value='editor'>{roleLabel('editor')}</option>
                    <option value='admin'>{roleLabel('admin')}</option>
                  </select>
                </td>
                <td>{u.created_at}</td>
                <td className='AdminUsers__actions-cell'>
                  <button
                    className='AdminUsers__button AdminUsers__button--secondary'
                    onClick={() => {
                      setResetUserId(u.id);
                      setResetPassword('');
                    }}
                  >
                    {t('admin.resetPassword')}
                  </button>
                  <button
                    className='AdminUsers__button AdminUsers__button--danger'
                    onClick={() => handleDelete(u)}
                  >
                    {t('admin.deleteUser')}
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
            {t('admin.resetPasswordFor')} {resetUserId}
          </h2>
          <form onSubmit={handleResetPassword}>
            <div className='AdminUsers__form-row'>
              <input
                type='password'
                placeholder={t('admin.newPassword')}
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
                required
              />
              <button type='submit' className='AdminUsers__button'>
                {t('admin.reset')}
              </button>
              <button
                type='button'
                className='AdminUsers__button AdminUsers__button--ghost'
                onClick={() => setResetUserId(null)}
              >
                {t('admin.cancel')}
              </button>
            </div>
          </form>
        </section>
      )}

      <section className='AdminUsers__section'>
        <h2>{t('admin.createUser')}</h2>
        <form onSubmit={handleCreate}>
          <div className='AdminUsers__form-row'>
            <input
              type='text'
              placeholder={t('admin.username')}
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              required
            />
            <input
              type='password'
              placeholder={t('admin.passwordPlaceholder')}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
            <select
              className='AdminUsers__role-select'
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
            >
              <option value='viewer'>{roleLabel('viewer')}</option>
              <option value='editor'>{roleLabel('editor')}</option>
              <option value='admin'>{roleLabel('admin')}</option>
            </select>
            <button
              type='submit'
              className='AdminUsers__button'
              disabled={loading}
            >
              {loading ? t('settings.creating') : t('settings.create')}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default AdminUsers;
