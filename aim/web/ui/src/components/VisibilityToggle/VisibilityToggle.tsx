import React, { useState, useCallback } from 'react';

import API from 'services/api/api';
import ENDPOINTS from 'services/api/endpoints';

import './VisibilityToggle.scss';

export interface VisibilityToggleProps {
  entityType: 'runs' | 'experiments';
  entityId: string;
  isPublic: boolean;
  isOwner: boolean;
  onVisibilityChange?: (isPublic: boolean) => void;
}

function VisibilityToggle({
  entityType,
  entityId,
  isPublic,
  isOwner,
  onVisibilityChange,
}: VisibilityToggleProps): React.FunctionComponentElement<VisibilityToggleProps> | null {
  const [currentIsPublic, setCurrentIsPublic] = useState(isPublic);
  const [loading, setLoading] = useState(false);

  const endpointSection =
    entityType === 'runs' ? ENDPOINTS.RUNS : ENDPOINTS.EXPERIMENTS;

  const handleToggle = useCallback(async () => {
    if (loading) return;

    const newValue = !currentIsPublic;
    setLoading(true);

    try {
      const url = `${endpointSection.BASE}/${entityId}/${endpointSection.VISIBILITY}`;
      await API.put(url, { is_public: newValue }).call();
      setCurrentIsPublic(newValue);
      onVisibilityChange?.(newValue);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to update visibility:', error);
    } finally {
      setLoading(false);
    }
  }, [currentIsPublic, loading, entityId, endpointSection, onVisibilityChange]);

  if (!isOwner) {
    return (
      <span className='VisibilityToggle__label'>
        {currentIsPublic ? 'Public' : 'Private'}
      </span>
    );
  }

  return (
    <div className='VisibilityToggle'>
      <label className='VisibilityToggle__switch'>
        <input
          type='checkbox'
          checked={currentIsPublic}
          onChange={handleToggle}
          disabled={loading}
          className='VisibilityToggle__input'
        />
        <span className='VisibilityToggle__slider' />
      </label>
      <span className='VisibilityToggle__label'>
        {currentIsPublic ? 'Public' : 'Private'}
      </span>
    </div>
  );
}

export default VisibilityToggle;
