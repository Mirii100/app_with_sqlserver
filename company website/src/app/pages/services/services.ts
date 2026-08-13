import { Component, OnInit, inject } from '@angular/core';
import { ApiService } from '../../services/api';
import { CommonModule } from '@angular/common';
import { SkeletonLoader } from '../../components/skeleton-loader/skeleton-loader';

@Component({
  selector: 'app-services',
  imports: [CommonModule, SkeletonLoader],
  templateUrl: './services.html',
  styleUrl: './services.scss',
})
export class Services implements OnInit {
  private apiService = inject(ApiService);
  services: any[] = [];
  loading = true;

  ngOnInit() {
    this.apiService.getServices().subscribe({
      next: (data) => {
        this.services = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error fetching services', err);
        this.loading = false;
        alert('Failed to load services. Please try again later.'); // User feedback
      }
    });
  }
}
