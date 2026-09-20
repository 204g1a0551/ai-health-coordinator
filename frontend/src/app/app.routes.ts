import { Routes } from '@angular/router';
import { LoginComponent } from './components/login/login.component';
import { RegisterComponent } from './components/register/register.component';
import { DashboardLayoutComponent } from './components/dashboard-layout/dashboard-layout.component';
import { authGuard, guestGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent,
    canActivate: [guestGuard],
  },
  {
    path: 'register',
    component: RegisterComponent,
    canActivate: [guestGuard],
  },
  {
    path: 'dashboard',
    component: DashboardLayoutComponent,
    canActivate: [authGuard],
  },
  {
    path: 'documents',
    component: DashboardLayoutComponent,
    canActivate: [authGuard],
  },
  {
    path: 'insurance',
    component: DashboardLayoutComponent,
    canActivate: [authGuard],
  },
  {
    path: 'appointments',
    component: DashboardLayoutComponent,
    canActivate: [authGuard],
  },
  {
    path: 'profile',
    component: DashboardLayoutComponent,
    canActivate: [authGuard],
  },
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full',
  },
  {
    path: '**',
    redirectTo: 'dashboard',
  },
];
