import React from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { Eye } from 'lucide-react';

export const EvidenceVerificationPage: React.FC = () => (
  <PageWrapper title="Side-by-Side Evidence Grounding" subtitle="Verify source document text spans and page numbers for criterion decisions." moduleName="modules/evidence" icon={Eye} />
);
