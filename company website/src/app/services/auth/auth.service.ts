import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface SignupPayload {
  username: string;
  email: string;
  password: string;
  phone_number: string;
  full_name?: string;
  national_id?: string;
  county?: string;
  town?: string;
  postal_code?: string;
  employment_type?: string;
  monthly_income?: number;
  referral_code?: string;
}

export interface LoginResponse {
  token: string;
  user_id: number;
  email: string;
  full_name: string;
  phone: string;
  account_number: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private tokenKey = 'auth_token';
  private userKey = 'auth_user';
  private baseUrl = environment.apiUrl;

  isAuthenticated = signal<boolean>(!!localStorage.getItem(this.tokenKey));

  constructor(private http: HttpClient) {}

  signup(payload: SignupPayload): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/signup/`, payload);
  }

  loginWithCredentials(identifier: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.baseUrl}/auth/login/`, {
      email: identifier,
      password: password,
    }).pipe(
      tap((res) => {
        localStorage.setItem(this.tokenKey, res.token);
        localStorage.setItem(this.userKey, JSON.stringify({
          user_id: res.user_id,
          email: res.email,
          full_name: res.full_name,
          phone: res.phone,
          account_number: res.account_number,
        }));
        this.isAuthenticated.set(true);
      })
    );
  }

  login(token: string) {
    localStorage.setItem(this.tokenKey, token);
    this.isAuthenticated.set(true);
  }

  logout() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    this.isAuthenticated.set(false);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  getUser(): { user_id: number; email: string; full_name: string; phone: string; account_number: string } | null {
    const raw = localStorage.getItem(this.userKey);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
}
