import React from 'react';

import { Button, Spinner, Text } from 'components/kit';
import ReleaseNoteItem from 'components/ReleaseNoteItem/ReleaseNoteItem';

import { AIM_VERSION } from 'config/config';

import { useI18n } from 'services/i18n';

import GuideLinks from '../GuideDocs/GuideDocs';

import useReleaseNotes from './useReleaseNotes';

import './ReleaseNotes.scss';

function ReleaseNotes(): React.FunctionComponentElement<React.ReactNode> {
  const { t } = useI18n();
  const {
    changelogData,
    LatestReleaseData,
    currentReleaseData,
    isLoading,
    releaseNoteRef,
    scrollShadow,
  } = useReleaseNotes();

  return (
    <div className='ReleaseNotes'>
      {isLoading ? (
        <div className='ReleaseNotes__Spinner'>
          <Spinner />
        </div>
      ) : (
        <>
          <div className='ReleaseNotes__latest'>
            <div className='ReleaseNotes__latest__title'>
              <Text component='h4' tint={100} weight={700} size={14}>
                Aim {LatestReleaseData?.tagName}
              </Text>
              {`v${AIM_VERSION}` === LatestReleaseData?.tagName ? null : (
                <span>{t('dashboard.latest')}</span>
              )}
            </div>
            <div className='ReleaseNotes__latest__content'>
              {LatestReleaseData?.info?.map((title: string, index: number) => (
                <div
                  className='ReleaseNotes__latest__content__item'
                  key={index}
                >
                  <Text size={12}>{title.replace(/-/g, ' ')}</Text>
                </div>
              ))}
              <a href={LatestReleaseData?.url} target='_blank' rel='noreferrer'>
                <Button fullWidth variant='outlined' size='xSmall'>
                  {t('dashboard.releaseNotes')}
                </Button>
              </a>
            </div>
          </div>
          {`v${AIM_VERSION}` === LatestReleaseData?.tagName ? null : (
            <div className='ReleaseNotes__changelog'>
              <Text
                className='ReleaseNotes__changelog__title'
                component='h4'
                tint={100}
                weight={700}
                size={14}
              >
                {t('dashboard.changelog')}
              </Text>
              <div
                ref={releaseNoteRef}
                className='ReleaseNotes__changelog__content'
              >
                {changelogData.map((item) => (
                  <ReleaseNoteItem
                    key={item.tagName}
                    tagName={item.tagName}
                    info={item.info}
                    href={item.url}
                  />
                ))}
              </div>
              {currentReleaseData ? (
                <div
                  className={`ReleaseNotes__changelog__currentRelease ${
                    scrollShadow
                      ? 'ReleaseNotes__changelog__currentRelease__scroll'
                      : ''
                  }`}
                >
                  <ReleaseNoteItem
                    tagName={`${currentReleaseData!.tagName} [${t(
                      'dashboard.current',
                    )}]`}
                    info={currentReleaseData!.info}
                    href={currentReleaseData!.url}
                  />
                </div>
              ) : null}
            </div>
          )}
          <GuideLinks />
        </>
      )}
    </div>
  );
}

export default React.memo(ReleaseNotes);
