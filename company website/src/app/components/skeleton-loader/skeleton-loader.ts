import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-skeleton-loader',
  imports: [],
  template: `
    <div class="skeleton" [style.height.px]="height"></div>
  `,
  styles: [`
    .skeleton {
      background-color: #e0e0e0;
      border-radius: 4px;
      animation: pulse 1.5s infinite ease-in-out;
      width: 100%;
      margin-bottom: 0.5rem;
    }
    @keyframes pulse {
      0% { opacity: 0.6; }
      50% { opacity: 1; }
      100% { opacity: 0.6; }
    }
  `]
})
export class SkeletonLoader {
  @Input() height: number = 20;
}
