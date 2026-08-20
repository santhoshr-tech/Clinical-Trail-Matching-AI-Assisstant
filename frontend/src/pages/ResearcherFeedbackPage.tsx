import React from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { MessageSquare } from 'lucide-react';

export const ResearcherFeedbackPage: React.FC = () => (
  <PageWrapper title="Researcher Feedback Loop" subtitle="Submit reviewer feedback on extractions, normalizations, and evidence citations." moduleName="modules/feedback" icon={MessageSquare} />
);
