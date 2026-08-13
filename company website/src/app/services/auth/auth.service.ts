import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private tokenKey = 'auth_token';
  // Use a signal for reactive state
  isAuthenticated = signal<boolean>(!!localStorage.getItem(this.tokenKey));

  login(token: string) {
    localStorage.setItem(this.tokenKey, token);
    this.isAuthenticated.set(true);
  }

  logout() {
    localStorage.removeItem(this.tokenKey);
    this.isAuthenticated.set(false);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }
}
