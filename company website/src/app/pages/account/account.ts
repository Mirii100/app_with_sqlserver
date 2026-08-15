import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../services/auth/auth.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-account',
  imports: [CommonModule, RouterLink],
  templateUrl: './account.html',
  styleUrl: './account.scss',
})
export class Account implements OnInit {
  private http = inject(HttpClient);
  private authService = inject(AuthService);
  private router = inject(Router);

  user: any = null;
  loading = true;
  loadError: string | null = null;

  ngOnInit() {
    const stored = this.authService.getUser();
    if (!this.authService.isAuthenticated()) {
      this.router.navigate(['/login']);
      return;
    }
    if (stored) {
      this.user = stored;
    }
    this.fetchProfile(stored?.user_id);
  }

  fetchProfile(userId?: number) {
    if (!userId) {
      this.loading = false;
      return;
    }
    this.http.get(`${environment.apiUrl}/users/${userId}/`).subscribe({
      next: (data: any) => {
        this.user = { ...this.user, ...data };
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        if (err.status === 401) {
          this.authService.logout();
          this.router.navigate(['/login']);
        } else {
          this.loadError = 'Unable to load your account details. Please try again later.';
        }
      }
    });
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/']);
  }

  formatMoney(value: any): string {
    const num = Number(value) || 0;
    return 'KES ' + num.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
}
