import React from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { CheckCircle2 } from 'lucide-react';

export const ScreeningResultPage: React.FC = () => (
  <PageWrapper title="Matching Screening Card" subtitle="Deterministic 4-state criterion decision breakdown (PASS, FAIL, UNKNOWN, CONFLICT)." moduleName="modules/matching" icon={CheckCircle2} />
);
