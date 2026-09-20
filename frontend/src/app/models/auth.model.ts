export interface UserProfile {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  dob?: string;
  created_at?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterRequest {
  full_name: string;
  email: string;
  phone: string;
  password: string;
  dob?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: UserProfile | null;
  token: string | null;
  loading: boolean;
}
