import React from 'react';

import projectsModel from 'services/models/projects/projectsModel';

function ProjectWrapper() {
  React.useEffect(() => {
    const projectDataRequestRef = projectsModel.getProjectsData();
    projectDataRequestRef.call();
    const pinnedSequencesRequestRef = projectsModel.getPinnedSequences();
    pinnedSequencesRequestRef.call();

    return () => {
      projectDataRequestRef.abort();
      pinnedSequencesRequestRef.abort();
    };
  }, []);

  return null;
}

export default ProjectWrapper;
