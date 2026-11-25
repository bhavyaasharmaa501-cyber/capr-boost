export type UserRole = 'Admin' | 'Analyst' | 'Viewer';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserSummary {
  userId: number;
  email: string;
  displayName: string;
  role: UserRole;
}

export interface LoginResponse {
  token: string;
  expiresAtUtc: string;
  user: UserSummary;
}

export interface UserDto {
  userId: number;
  email: string;
  displayName: string;
  role: UserRole;
  isActive: boolean;
  createdAtUtc: string;
  lastLoginUtc: string | null;
}

export interface CreateUserRequest {
  email: string;
  displayName: string;
  password: string;
  role: UserRole;
}

export interface ForgotPasswordResponse {
  message: string;
  emailSent: boolean;
  demoCode: string | null;
  expiresInMinutes: number;
}

export interface ResetPasswordRequest {
  email: string;
  code: string;
  newPassword: string;
}

export interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
}

export interface MessageResponse {
  message: string;
}
