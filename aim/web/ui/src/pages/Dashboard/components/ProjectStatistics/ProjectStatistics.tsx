import * as React from 'react';

import { Text } from 'components/kit';
import StatisticsCard from 'components/StatisticsCard';
import StatisticsBar from 'components/StatisticsBar';

import routes from 'routes/routes';

import { useI18n } from 'services/i18n';

import { SequenceTypesEnum } from 'types/core/enums';

import { encode } from 'utils/encoder/encoder';

import { IProjectStatistic, useProjectStatistics } from '.';

import './ProjectStatistics.scss';

function ProjectStatistics() {
  const { t } = useI18n();
  const [hoveredState, setHoveredState] = React.useState({
    source: '',
    id: '',
  });
  const { projectParamsStore, projectContributionsStore } =
    useProjectStatistics();

  const statisticsInitialMap: Record<string, IProjectStatistic> = React.useMemo(
    () => ({
      [SequenceTypesEnum.Metric]: {
        label: t('sidebar.metrics'),
        count: 0,
        icon: 'metrics',
        iconBgColor: '#7A4CE0',
        navLink: routes.METRICS.path,
      },
      systemMetrics: {
        label: t('dashboard.sysMetrics'),
        count: 0,
        icon: 'metrics',
        iconBgColor: '#AF4EAB',
        navLink: `${routes.METRICS.path}?select=${encode({
          advancedQuery: "metric.name.startswith('__system__') == True",
          advancedMode: true,
        })}`,
      },
      [SequenceTypesEnum.Figures]: {
        label: t('sidebar.figures'),
        icon: 'figures',
        count: 0,
        iconBgColor: '#18AB6D',
        navLink: routes.FIGURES_EXPLORER.path,
      },
      [SequenceTypesEnum.Images]: {
        label: t('sidebar.images'),
        icon: 'images',
        count: 0,
        iconBgColor: '#F17922',
        navLink: routes.IMAGE_EXPLORE.path,
      },
      [SequenceTypesEnum.Audios]: {
        label: t('sidebar.audios'),
        icon: 'audios',
        count: 0,
        iconBgColor: '#FCB500',
        navLink: routes.AUDIOS_EXPLORER.path,
        badge: {
          value: t('dashboard.new'),
          style: { backgroundColor: '#1473e6', color: '#fff' },
        },
      },
      [SequenceTypesEnum.Texts]: {
        label: t('sidebar.text'),
        icon: 'text',
        count: 0,
        iconBgColor: '#E149A0',
        navLink: routes.TEXT_EXPLORER.path,
        badge: {
          value: t('dashboard.new'),
          style: { backgroundColor: '#1473e6', color: '#fff' },
        },
      },
      [SequenceTypesEnum.Distributions]: {
        label: t('dashboard.distributions'),
        icon: 'distributions',
        count: 0,
        iconBgColor: '#0394B4',
        navLink: '',
        badge: {
          value: t('dashboard.explorerComingSoon'),
        },
      },
    }),
    [t],
  );

  const runsCountingInitialMap: Record<'archived' | 'runs', IProjectStatistic> =
    React.useMemo(
      () => ({
        runs: {
          label: t('dashboard.runs'),
          icon: 'runs',
          count: 0,
          iconBgColor: '#1473E6',
          navLink: routes.RUNS.path,
        },
        archived: {
          label: t('dashboard.archived'),
          icon: 'archive',
          count: 0,
          iconBgColor: '#606986',
          navLink: `/runs?select=${encode({ query: 'run.archived == True' })}`,
        },
      }),
      [t],
    );

  const { statisticsMap, totalTrackedSequencesCount } = React.useMemo(() => {
    const statistics = { ...statisticsInitialMap };
    let totalTrackedSequencesCount = 0;

    for (let [seqName, seqData] of Object.entries(
      projectParamsStore.data || {},
    )) {
      let systemMetricsCount = 0;
      let sequenceItemsCount = 0;
      for (let [itemKey, itemData] of Object.entries(seqData)) {
        if (itemKey.startsWith('__system__')) {
          systemMetricsCount += itemData.length;
        } else {
          sequenceItemsCount += itemData.length;
        }
      }
      totalTrackedSequencesCount += sequenceItemsCount;
      statistics[seqName].count = sequenceItemsCount;
      if (systemMetricsCount) {
        totalTrackedSequencesCount += systemMetricsCount;
        statistics.systemMetrics.count = systemMetricsCount;
      }
    }
    return { statisticsMap: statistics, totalTrackedSequencesCount };
  }, [projectParamsStore, statisticsInitialMap]);

  const { totalRunsCount, archivedRuns } = React.useMemo(
    () => ({
      totalRunsCount: projectContributionsStore.data?.num_runs || 0,
      archivedRuns: projectContributionsStore.data?.num_archived_runs || 0,
    }),
    [projectContributionsStore],
  );
  const statisticsBarData = React.useMemo(
    () =>
      Object.values(statisticsMap).map(
        ({ label, iconBgColor = '#000', count }) => ({
          highlighted: hoveredState.id === label,
          label,
          color: iconBgColor,
          percent:
            totalTrackedSequencesCount === 0
              ? 0
              : (count / totalTrackedSequencesCount) * 100,
        }),
      ),
    [statisticsMap, totalTrackedSequencesCount, hoveredState],
  );
  const runsCountingMap = React.useMemo(
    () => ({
      runs: {
        ...runsCountingInitialMap.runs,
        count: totalRunsCount - archivedRuns,
      },
      archived: {
        ...runsCountingInitialMap.archived,
        count: archivedRuns,
      },
    }),
    [archivedRuns, totalRunsCount],
  );
  const onMouseOver = React.useCallback((id = '', source = '') => {
    setHoveredState({ source, id });
  }, []);
  const onMouseLeave = React.useCallback(() => {
    setHoveredState({ source: '', id: '' });
  }, []);
  return (
    <div className='ProjectStatistics'>
      <Text
        className='ProjectStatistics__totalRuns'
        component='p'
        tint={100}
        weight={700}
        size={14}
      >
        {t('dashboard.totalRuns')} {totalRunsCount}
      </Text>
      <div className='ProjectStatistics__cards'>
        {Object.values(runsCountingMap).map(
          ({ label, icon, count, iconBgColor, navLink }) => (
            <StatisticsCard
              key={label}
              label={label}
              icon={icon}
              count={count}
              navLink={navLink}
              iconBgColor={iconBgColor}
              onMouseOver={onMouseOver}
              onMouseLeave={onMouseLeave}
              highlighted={!!navLink && hoveredState.id === label}
              isLoading={projectContributionsStore.loading}
            />
          ),
        )}
      </div>
      <Text
        className='ProjectStatistics__trackedSequences'
        component='p'
        tint={100}
        weight={700}
        size={14}
      >
        {t('dashboard.trackedSequences')}
      </Text>
      <div className='ProjectStatistics__cards'>
        {Object.values(statisticsMap).map(
          ({ label, icon, count, iconBgColor, navLink, badge }) => (
            <StatisticsCard
              key={label}
              badge={badge}
              label={label}
              icon={icon}
              count={count}
              navLink={navLink}
              iconBgColor={iconBgColor}
              onMouseOver={onMouseOver}
              onMouseLeave={onMouseLeave}
              highlighted={
                !!navLink &&
                hoveredState.source === 'card' &&
                hoveredState.id === label
              }
              outlined={hoveredState.id === label}
              isLoading={projectParamsStore.loading}
            />
          ),
        )}
      </div>
      <div className='ProjectStatistics__bar'>
        <StatisticsBar
          data={statisticsBarData}
          onMouseOver={onMouseOver}
          onMouseLeave={onMouseLeave}
        />
      </div>
    </div>
  );
}

ProjectStatistics.displayName = 'ProjectStatistics';

export default React.memo(ProjectStatistics);
