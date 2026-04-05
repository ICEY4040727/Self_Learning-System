import { createBrowserRouter, Outlet } from 'react-router';
import { LoginPage } from './pages/LoginPage';
import { MainMenuPage } from './pages/MainMenuPage';
import { LearningPage } from './pages/LearningPage';
import { ArchivesPage } from './pages/ArchivesPage';
import { SettingsPage } from './pages/SettingsPage';

function Root() {
  return <Outlet />;
}

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Root,
    children: [
      { index: true, Component: LoginPage },
      { path: 'menu', Component: MainMenuPage },
      { path: 'learn', Component: LearningPage },
      { path: 'archives', Component: ArchivesPage },
      { path: 'settings', Component: SettingsPage },
    ],
  },
]);
