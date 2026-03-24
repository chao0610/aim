import React from 'react';

import { Text } from 'components/kit';

import { useI18n } from 'services/i18n';

import ReleaseNotes from './ReleaseNotes/ReleaseNotes';

import './DashboardRight.scss';

function DashboardRight(): React.FunctionComponentElement<React.ReactNode> {
  const { t } = useI18n();
  return (
    <aside className='DashboardRight'>
      <Text
        className='DashboardRight__title'
        component='h3'
        tint={100}
        size={18}
        weight={600}
      >
        {t('dashboard.whatsNew')}
      </Text>
      <ReleaseNotes />
    </aside>
  );
}

export default React.memo(DashboardRight);
