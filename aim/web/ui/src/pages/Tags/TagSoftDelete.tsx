import React, { memo, useRef } from 'react';

import ConfirmModal from 'components/ConfirmModal/ConfirmModal';
import { Icon } from 'components/kit';
import ErrorBoundary from 'components/ErrorBoundary/ErrorBoundary';

import tagsAppModel from 'services/models/tags/tagsAppModel';
import { useI18n } from 'services/i18n';

import { ITagSoftDeleteProps } from 'types/pages/tags/Tags';

import './Tags.scss';

function TagSoftDelete({
  tagInfo,
  tagHash,
  onSoftDeleteModalToggle,
  onTagDetailOverlayToggle,
  isTagDetailOverLayOpened,
  modalIsOpen,
}: ITagSoftDeleteProps): React.FunctionComponentElement<React.ReactNode> {
  const { t } = useI18n();
  const archivedRef = useRef({ archived: tagInfo?.archived });

  function onTagHide() {
    tagsAppModel.archiveTag(tagHash, !tagInfo?.archived).then(() => {
      tagsAppModel.getTagsData().call();
      onSoftDeleteModalToggle();
      isTagDetailOverLayOpened && onTagDetailOverlayToggle();
    });
  }

  function onTagShow() {
    tagsAppModel.archiveTag(tagHash, !tagInfo?.archived).then(() => {
      tagsAppModel.getTagsData().call();
      onSoftDeleteModalToggle();
      isTagDetailOverLayOpened && onTagDetailOverlayToggle();
    });
  }

  return (
    <ErrorBoundary>
      <ConfirmModal
        open={modalIsOpen}
        onCancel={onSoftDeleteModalToggle}
        onSubmit={archivedRef.current?.archived ? onTagShow : onTagHide}
        text={t('tags.confirmHide', {
          action: archivedRef.current?.archived
            ? t('tags.bringBack').toLowerCase()
            : t('tags.hide').toLowerCase(),
        })}
        icon={
          <Icon
            name={
              archivedRef.current?.archived
                ? 'eye-show-outline'
                : 'eye-outline-hide'
            }
          />
        }
        title={t('tags.hideTag')}
        confirmBtnText={
          archivedRef.current?.archived ? t('tags.bringBack') : t('tags.hide')
        }
      />
    </ErrorBoundary>
  );
}

export default memo(TagSoftDelete);
