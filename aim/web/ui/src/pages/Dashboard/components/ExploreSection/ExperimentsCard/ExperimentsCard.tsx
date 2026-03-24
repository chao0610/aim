import React from 'react';
import _ from 'lodash-es';

import DataList from 'components/kit/DataList';
import { Text } from 'components/kit';

import CompareSelectedRunsPopover from 'pages/Metrics/components/Table/CompareSelectedRunsPopover';

import { useI18n } from 'services/i18n';
import { AppNameEnum } from 'services/models/explorer';

import useExperimentsCard from './useExperimentsCard';

import './ExperimentsCard.scss';

function ExperimentsCard(): React.FunctionComponentElement<React.ReactNode> | null {
  const { t } = useI18n();
  const {
    tableRef,
    tableColumns,
    tableData,
    experimentsStore,
    selectedRows,
    experimentsQuery,
  } = useExperimentsCard();
  return experimentsStore.data?.length ? (
    <div className='ExperimentsCard'>
      <Text
        className='ExperimentsCard__title'
        component='h3'
        size={14}
        weight={700}
        tint={100}
      >
        {t('dashboard.experiments')} ({experimentsStore.data.length})
      </Text>
      <DataList
        tableRef={tableRef}
        tableColumns={tableColumns}
        tableData={tableData}
        isLoading={experimentsStore.loading}
        height={Math.min(238, tableData.length * 24 + 56) + 'px'}
        searchableKeys={['name', 'run_count']}
        rowHeight={24}
        illustrationConfig={{
          size: 'small',
          title: t('dashboard.noResults'),
          showImage: false,
        }}
        toolbarItems={[
          <CompareSelectedRunsPopover
            key='compareSelectedRunsPopover'
            appName={'dashboard' as AppNameEnum}
            query={experimentsQuery}
            disabled={_.isEmpty(selectedRows)}
          />,
        ]}
        disableMatchBar={true}
      />
    </div>
  ) : null;
}

ExperimentsCard.displayName = 'ExperimentsCard';

export default React.memo(ExperimentsCard);
