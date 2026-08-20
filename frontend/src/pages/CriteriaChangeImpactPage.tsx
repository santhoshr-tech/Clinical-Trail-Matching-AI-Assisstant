import React from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { GitCompare } from 'lucide-react';

export const CriteriaChangeImpactPage: React.FC = () => (
  <PageWrapper title="Protocol Criteria Change Impact Analysis" subtitle="Analyze affected patient rosters when a trial protocol or criteria version is updated." moduleName="modules/impact_analysis" icon={GitCompare} />
);
