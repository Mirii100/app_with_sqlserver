import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-hero-section',
  imports: [],
  template: `
    <section class="hero">
      <div class="container">
        <h1>{{ title }}</h1>
        <p>{{ subtitle }}</p>
      </div>
    </section>
  `,
  styles: [`
    .hero {
      padding: 4rem 0;
      text-align: center;
      background-color: var(--primary-color);
      color: white;
    }
  `]
})
export class HeroSection {
  @Input() title: string = '';
  @Input() subtitle: string = '';
}
