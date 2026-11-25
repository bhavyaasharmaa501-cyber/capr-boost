import { Routes } from '@angular/router';
import { authGuard, roleGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'forgot-password',
    loadComponent: () =>
      import('./features/forgot-password/forgot-password.component').then((m) => m.ForgotPasswordComponent),
  },
  {
    path: '',
    loadComponent: () => import('./features/shell/shell.component').then((m) => m.ShellComponent),
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'uploads',
        loadComponent: () => import('./features/uploads/uploads.component').then((m) => m.UploadsComponent),
      },
      {
        path: 'uploads/:id',
        loadComponent: () =>
          import('./features/uploads/upload-detail.component').then((m) => m.UploadDetailComponent),
      },
      {
        path: 'alerts',
        loadComponent: () => import('./features/alerts/alerts.component').then((m) => m.AlertsComponent),
      },
      {
        path: 'models',
        loadComponent: () => import('./features/models/models.component').then((m) => m.ModelsComponent),
      },
      {
        path: 'experiments',
        loadComponent: () =>
          import('./features/experiments/experiments.component').then((m) => m.ExperimentsComponent),
      },
      {
        path: 'users',
        loadComponent: () => import('./features/users/users.component').then((m) => m.UsersComponent),
        canActivate: [roleGuard('Admin')],
      },
      { path: '**', redirectTo: 'dashboard' },
    ],
  },
  { path: '**', redirectTo: 'login' },
];
