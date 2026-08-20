import React from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { CheckSquare } from 'lucide-react';

export const CoordinatorReviewQueuePage: React.FC = () => (
  <PageWrapper title="Clinical Research Coordinator Review Queue" subtitle="Pre-screening decision review queue for qualified clinical research coordinators." moduleName="modules/review" icon={CheckSquare} />
);
