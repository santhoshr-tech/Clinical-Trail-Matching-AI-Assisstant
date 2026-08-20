import React from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { RefreshCw } from 'lucide-react';

export const RescreeningQueuePage: React.FC = () => (
  <PageWrapper title="Automated Re-screening Queue" subtitle="Monitor non-blocking background re-screening jobs triggered by clinical data updates." moduleName="modules/rescreening" icon={RefreshCw} />
);
