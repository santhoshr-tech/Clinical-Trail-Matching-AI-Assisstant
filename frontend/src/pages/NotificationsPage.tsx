import React from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { Bell } from 'lucide-react';

export const NotificationsPage: React.FC = () => (
  <PageWrapper title="Coordinator Alert Center" subtitle="Notifications for pending reviews, re-screening alerts, and protocol changes." moduleName="modules/notifications" icon={Bell} />
);
