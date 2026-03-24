import React from 'react';
import { BrowserRouter, Switch, Route, Redirect } from 'react-router-dom';
import { useModel } from 'hooks';

import { loader } from '@monaco-editor/react';

import AlertBanner from 'components/kit/AlertBanner';
import SideBar from 'components/SideBar/SideBar';
import ProjectWrapper from 'components/ProjectWrapper/ProjectWrapper';
import Theme from 'components/Theme/Theme';
import BusyLoaderWrapper from 'components/BusyLoaderWrapper/BusyLoaderWrapper';
import ErrorBoundary from 'components/ErrorBoundary/ErrorBoundary';

import { getBasePath } from 'config/config';
import { PathEnum } from 'config/enums/routesEnum';

import PageWrapper from 'pages/PageWrapper';

import routes from 'routes/routes';

import { I18nProvider } from 'services/i18n';
import projectsModel from 'services/models/projects/projectsModel';

import { IProjectsModelState } from './types/services/models/projects/projectsModel';
import usePyodide from './services/pyodide/usePyodide';

import './App.scss';

const SignIn = React.lazy(
  () => import(/* webpackChunkName: "signin" */ 'pages/SignIn/SignIn'),
);
const SSOCallback = React.lazy(
  () =>
    import(
      /* webpackChunkName: "sso-callback" */ 'pages/SSOCallback/SSOCallback'
    ),
);

const basePath = getBasePath(false);

// loading monaco from node modules instead of CDN
loader.config({
  paths: {
    vs: `${getBasePath()}/static-files/vs`,
  },
});

function App(): React.FunctionComponentElement<React.ReactNode> {
  const projectsData = useModel<Partial<IProjectsModelState>>(projectsModel);
  const { loadPyodide } = usePyodide();

  const authToken = localStorage.getItem('Auth');
  const pathname = window.location.pathname;
  const isSignInPage = pathname.endsWith('/sign-in');
  const isSSOCallback = pathname.endsWith('/sso/callback');
  const isAuthPage = isSignInPage || isSSOCallback;

  React.useEffect(() => {
    if (!authToken && !isAuthPage) {
      // Redirect to Django SSO entry point for automatic login.
      // Falls back to local sign-in if SSO is not available.
      window.location.assign('/aim-sso/');
    }
  }, []);

  React.useEffect(() => {
    let timeoutId: number;
    const preloader = document.getElementById('preload-spinner');
    if (preloader) {
      preloader.classList.add('preloader-fade-out');
      timeoutId = window.setTimeout(() => {
        preloader.remove();
      }, 500);
    }

    loadPyodide();

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, []);

  return (
    <I18nProvider>
      <BrowserRouter basename={basePath}>
        <Theme>
          {!authToken && isAuthPage ? (
            <React.Suspense
              fallback={<BusyLoaderWrapper height='100vh' isLoading />}
            >
              <Switch>
                <Route path={PathEnum.Sign_In} exact>
                  <SignIn />
                </Route>
                <Route path={PathEnum.SSO_Callback} exact>
                  <SSOCallback />
                </Route>
              </Switch>
            </React.Suspense>
          ) : (
            <>
              <ProjectWrapper />
              {projectsData?.project?.warn_index && (
                <AlertBanner type='warning'>
                  Index db was corrupted and deleted. Please run
                  <b>`aim storage reindex`</b> command to restore optimal
                  performance.
                </AlertBanner>
              )}
              {projectsData?.project?.warn_runs && (
                <AlertBanner type='warning'>
                  Corrupted runs were detected. Please run
                  <b>`aim runs rm --corrupted`</b> command to remove corrupted
                  runs.
                </AlertBanner>
              )}
              <div className='pageContainer'>
                <ErrorBoundary>
                  <SideBar />
                </ErrorBoundary>
                <div className='mainContainer'>
                  <React.Suspense
                    fallback={<BusyLoaderWrapper height='100vh' isLoading />}
                  >
                    <Switch>
                      {Object.values(routes).map((route, index) => {
                        const {
                          component: Component,
                          path,
                          isExact,
                          title,
                        } = route;
                        return (
                          <Route path={path} key={index} exact={isExact}>
                            <ErrorBoundary>
                              <PageWrapper path={path} title={title}>
                                <Component />
                              </PageWrapper>
                            </ErrorBoundary>
                          </Route>
                        );
                      })}
                      <Redirect to='/' />
                    </Switch>
                  </React.Suspense>
                </div>
              </div>
            </>
          )}
        </Theme>
      </BrowserRouter>
    </I18nProvider>
  );
}

export default App;
