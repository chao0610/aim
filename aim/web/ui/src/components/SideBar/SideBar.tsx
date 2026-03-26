import React from 'react';
import { NavLink } from 'react-router-dom';

import { Drawer, Tooltip } from '@material-ui/core';

import logoImg from 'assets/logo.svg';

import { Icon, Text } from 'components/kit';
import { IconName } from 'components/kit/Icon';
import ErrorBoundary from 'components/ErrorBoundary/ErrorBoundary';

import { AIM_VERSION, getBasePath } from 'config/config';
import { PathEnum } from 'config/enums/routesEnum';
import { DOCUMENTATIONS } from 'config/references';

import routes, { IRoute } from 'routes/routes';

import { useI18n } from 'services/i18n';

import { getItem } from 'utils/storage';

import './Sidebar.scss';

const sidebarDisplayNameMap: Record<string, string> = {
  Runs: 'sidebar.runs',
  Metrics: 'sidebar.metrics',
  Params: 'sidebar.params',
  Text: 'sidebar.text',
  Images: 'sidebar.images',
  Figures: 'sidebar.figures',
  Audios: 'sidebar.audios',
  Scatters: 'sidebar.scatters',
  Bookmarks: 'sidebar.bookmarks',
  Tags: 'sidebar.tags',
  Reports: 'sidebar.reports',
};

function getTokenPayload(): { username: string; role: string } {
  const auth = localStorage.getItem('Auth') || '';
  const token = auth.replace(/^Bearer\s+/i, '');
  if (!token) return { username: '', role: '' };
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return { username: payload.username || '', role: payload.role || '' };
  } catch {
    return { username: '', role: '' };
  }
}

function SideBar(): React.FunctionComponentElement<React.ReactNode> {
  const { t, locale, setLocale } = useI18n();
  const [userMenuOpen, setUserMenuOpen] = React.useState(false);
  const [menuPos, setMenuPos] = React.useState({ left: 0, bottom: 0 });
  const menuRef = React.useRef<HTMLDivElement>(null);
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const { username, role } = getTokenPayload();
  const isAdmin = role === 'admin';

  React.useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function getPathFromStorage(route: PathEnum): PathEnum | string {
    const path = getItem(`${route.slice(1)}Url`) ?? '';
    if (path !== '' && path.startsWith(route)) {
      return path;
    }
    return route;
  }

  function handleLogout() {
    localStorage.removeItem('Auth');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('refreshing');
    window.location.assign(`${getBasePath() || ''}/sign-in`);
  }

  function toggleLocale() {
    setLocale(locale === 'zh' ? 'en' : 'zh');
  }

  return (
    <ErrorBoundary>
      <div className='Sidebar'>
        <Drawer
          PaperProps={{ className: 'Sidebar__Paper' }}
          variant='permanent'
          anchor='left'
        >
          <ul className='Sidebar__List'>
            <NavLink
              exact={true}
              className='Sidebar__NavLink'
              to={routes.DASHBOARD.path}
            >
              <li className='Sidebar__List__item'>
                <img src={logoImg} alt='logo' />
              </li>
            </NavLink>
            <div className='Sidebar__List__container ScrollBar__hidden'>
              {Object.values(routes).map((route: IRoute, index: number) => {
                const { showInSidebar, path, displayName, icon } = route;
                const i18nKey =
                  displayName && sidebarDisplayNameMap[displayName];
                return (
                  showInSidebar && (
                    <NavLink
                      key={index}
                      to={() => getPathFromStorage(path)}
                      exact={true}
                      isActive={(m, location) =>
                        location.pathname.split('/')[1] === path.split('/')[1]
                      }
                      activeClassName='Sidebar__NavLink--active'
                      className='Sidebar__NavLink'
                    >
                      <li className='Sidebar__List__item'>
                        <Icon
                          className='Sidebar__List__item--icon'
                          fontSize={24}
                          name={icon as IconName}
                        />
                        <span className='Sidebar__List__item--text'>
                          {i18nKey ? t(i18nKey) : displayName}
                        </span>
                      </li>
                    </NavLink>
                  )
                );
              })}
            </div>
          </ul>
          <div className='Sidebar__bottom'>
            <Tooltip
              title={locale === 'zh' ? 'English' : '中文'}
              placement='right'
            >
              <button
                className='Sidebar__bottom__anchor Sidebar__bottom__lang'
                onClick={toggleLocale}
              >
                {locale === 'zh' ? 'EN' : '中'}
              </button>
            </Tooltip>
            <Tooltip title={t('sidebar.docs')} placement='right'>
              <a
                target='_blank'
                href={DOCUMENTATIONS.MAIN_PAGE}
                rel='noreferrer'
                className='Sidebar__bottom__anchor'
              >
                <Icon name='full-docs' />
              </a>
            </Tooltip>
            <div className='Sidebar__user' ref={menuRef}>
              <button
                ref={triggerRef}
                className='Sidebar__user__trigger'
                onClick={() => {
                  if (!userMenuOpen && triggerRef.current) {
                    const rect = triggerRef.current.getBoundingClientRect();
                    setMenuPos({
                      left: rect.right + 8,
                      bottom: window.innerHeight - rect.bottom,
                    });
                  }
                  setUserMenuOpen(!userMenuOpen);
                }}
              >
                <span className='Sidebar__user__avatar'>
                  {(username || '?')[0].toUpperCase()}
                </span>
              </button>
              {userMenuOpen && (
                <div
                  className='Sidebar__user__menu'
                  style={{ left: menuPos.left, bottom: menuPos.bottom }}
                >
                  <div className='Sidebar__user__menu__header'>
                    {username || 'User'}
                  </div>
                  <NavLink
                    to={routes.SETTINGS.path}
                    className='Sidebar__user__menu__item'
                    onClick={() => setUserMenuOpen(false)}
                  >
                    <Icon name='box-settings' fontSize={16} />
                    {t('sidebar.settings')}
                  </NavLink>
                  {isAdmin && (
                    <NavLink
                      to={routes.ADMIN_USERS.path}
                      className='Sidebar__user__menu__item'
                      onClick={() => setUserMenuOpen(false)}
                    >
                      <Icon name='manage-column' fontSize={16} />
                      {t('sidebar.adminUsers')}
                    </NavLink>
                  )}
                  <button
                    className='Sidebar__user__menu__item Sidebar__user__menu__item--danger'
                    onClick={handleLogout}
                  >
                    <Icon name='back-right' fontSize={16} />
                    {t('sidebar.logout')}
                  </button>
                </div>
              )}
            </div>
            <Text tint={30}>v{AIM_VERSION}</Text>
          </div>
        </Drawer>
      </div>
    </ErrorBoundary>
  );
}

export default React.memo(SideBar);
