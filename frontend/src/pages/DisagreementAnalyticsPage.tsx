import React from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { BarChart3 } from 'lucide-react';

export const DisagreementAnalyticsPage: React.FC = () => (
  <PageWrapper title="AI-vs-Human Disagreement Analytics" subtitle="Track agreement rates, false pass/fail review cases, and disputed criterion types." moduleName="modules/feedback" icon={BarChart3} />
);
