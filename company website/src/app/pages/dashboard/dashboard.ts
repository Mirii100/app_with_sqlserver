import { Component, OnInit, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../services/auth/auth.service';
import { environment } from '../../../environments/environment';

interface Txn {
  id: number;
  amount: string | number;
  type: string;
  category: string;
  description: string;
  reference: string;
  date: string;
}

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, RouterLink, DatePipe],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  private http = inject(HttpClient);
  private authService = inject(AuthService);
  private router = inject(Router);

  user: any = null;
  transactions: Txn[] = [];
  loading = true;
  txnsLoading = true;
  loadError: string | null = null;
  hideBalances = false;
  today = new Date();

  ngOnInit() {
    if (!this.authService.isAuthenticated()) {
      this.router.navigate(['/login']);
      return;
    }
    const stored = this.authService.getUser();
    if (stored) {
      this.user = stored;
    }
    this.fetchProfile(stored?.user_id);
    this.fetchTransactions(stored?.user_id);
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
          this.loadError = 'Unable to load your dashboard. Please try again later.';
        }
      },
    });
  }

  fetchTransactions(userId?: number) {
    if (!userId) {
      this.txnsLoading = false;
      return;
    }
    this.http
      .get(`${environment.apiUrl}/transactions/?user=${userId}`)
      .subscribe({
        next: (data: any) => {
          const list: Txn[] = Array.isArray(data) ? data : data.results || [];
          this.transactions = list
            .slice()
            .sort(
              (a, b) =>
                new Date(b.date).getTime() - new Date(a.date).getTime()
            )
            .slice(0, 8);
          this.txnsLoading = false;
        },
        error: () => {
          this.txnsLoading = false;
        },
      });
  }

  toggleBalances() {
    this.hideBalances = !this.hideBalances;
  }

  maskedAccount(): string {
    const acc = String(this.user?.account_number ?? '');
    if (!acc) return '—';
    return '•••• ' + acc.slice(-4);
  }

  firstName(): string {
    const name = String(this.user?.full_name || '').trim();
    if (name) return name.split(' ')[0];
    return String(this.user?.username || 'Member');
  }

  greeting(): string {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  }

  formatMoney(value: any): string {
    const num = Number(value) || 0;
    return (
      'KES ' +
      num.toLocaleString('en-KE', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    );
  }

  txnAmount(t: Txn): string {
    const num = Number(t.amount) || 0;
    const sign = t.type === 'withdrawal' ? '-' : '+';
    return sign + 'KES ' + num.toLocaleString('en-KE', { minimumFractionDigits: 2 });
  }

  txnIcon(t: Txn): string {
    switch ((t.category || '').toLowerCase()) {
      case 'deposit':
      case 'transfer_in':
        return 'fa-arrow-down';
      case 'withdrawal':
      case 'transfer_out':
        return 'fa-arrow-up';
      case 'loan':
        return 'fa-hand-holding-dollar';
      case 'savings':
        return 'fa-piggy-bank';
      case 'bill_payment':
        return 'fa-file-invoice-dollar';
      case 'airtime':
        return 'fa-mobile-screen';
      default:
        return 'fa-exchange';
    }
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/']);
  }
}
