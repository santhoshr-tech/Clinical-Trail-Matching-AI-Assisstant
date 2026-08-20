import React from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { UserCheck } from 'lucide-react';

export const InvestigatorReviewPage: React.FC = () => (
  <PageWrapper title="Principal Investigator Sign-off Workspace" subtitle="Final eligibility determination, override reasons, and investigator sign-off." moduleName="modules/review" icon={UserCheck} />
);
