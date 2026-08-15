import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-hero-section',
  imports: [RouterLink],
  template: `
    <section class="hero-wrapper">
      <div class="hero-overlay"></div>
      <div class="container hero-container">
        <div class="hero-content">
          <span class="badge"><i class="fa-solid fa-shield-halved"></i> Trusted Financial Partner</span>
          <h1>{{ title }}</h1>
          <p class="subtitle">{{ subtitle }}</p>
          <div class="hero-actions">
            <a routerLink="/signup" class="btn btn-secondary">Open Account</a>
            <a routerLink="/loans" class="btn btn-outline-white">Explore Loans</a>
          </div>
          <div class="hero-trust">
            <span><i class="fa-solid fa-circle-check"></i> CBK Licensed</span>
            <span><i class="fa-solid fa-circle-check"></i> KDIC Protected</span>
            <span><i class="fa-solid fa-circle-check"></i> 24/7 Support</span>
          </div>
        </div>
        <div class="hero-segments">
          <div class="segment-card">
            <div class="segment-icon"><i class="fa-solid fa-user"></i></div>
            <h3>Personal</h3>
            <p>Banking tailored for your life's journey.</p>
          </div>
          <div class="segment-card">
            <div class="segment-icon"><i class="fa-solid fa-briefcase"></i></div>
            <h3>Business</h3>
            <p>Empowering enterprises to reach new heights.</p>
          </div>
          <div class="segment-card active">
            <div class="segment-icon"><i class="fa-solid fa-people-group"></i></div>
            <h3>Chama</h3>
            <p>Growing together with collective investment.</p>
          </div>
          <div class="segment-card">
            <div class="segment-icon"><i class="fa-solid fa-earth-africa"></i></div>
            <h3>Diaspora</h3>
            <p>Secure solutions for Kenyans abroad.</p>
          </div>
        </div>
      </div>
    </section>
  `,
  styles: [`
    .hero-wrapper {
      position: relative;
      padding: var(--spacing-xxl) 0;
      background: linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-primary) 100%);
      color: white;
      overflow: hidden;
      min-height: 600px;
      display: flex;
      align-items: center;
    }

    .hero-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: url('https://www.transparenttextures.com/patterns/cubes.png');
      opacity: 0.1;
    }

    .hero-container {
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: var(--spacing-xl);
      align-items: center;
    }

    .hero-content h1 {
      color: white;
      font-size: 3.5rem;
      margin-bottom: var(--spacing-md);
      line-height: 1.1;
      font-family: var(--font-display);
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 0.5rem 1rem;
      background: rgba(218, 165, 32, 0.2);
      color: var(--color-secondary);
      border: 1px solid var(--color-secondary);
      border-radius: 50px;
      font-weight: 700;
      font-size: 0.8rem;
      text-transform: uppercase;
      margin-bottom: var(--spacing-md);
    }

    .subtitle {
      font-size: 1.25rem;
      color: rgba(255, 255, 255, 0.8);
      margin-bottom: var(--spacing-lg);
    }

    .hero-actions {
      display: flex;
      gap: var(--spacing-md);
      flex-wrap: wrap;
    }

    .hero-trust {
      display: flex;
      gap: var(--spacing-lg);
      margin-top: var(--spacing-lg);
      flex-wrap: wrap;
    }

    .hero-trust span {
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.85);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .hero-trust i {
      color: var(--color-secondary);
    }

    .hero-segments {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: var(--spacing-md);
    }

    .segment-card {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(5px);
      padding: var(--spacing-lg);
      border-radius: var(--border-radius);
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: var(--transition);
      cursor: pointer;
    }

    .segment-card:hover {
      background: rgba(255, 255, 255, 0.1);
      transform: translateY(-5px);
    }

    .segment-card.active {
      background: var(--color-white);
      border-color: var(--color-secondary);
    }

    .segment-card.active h3, .segment-card.active p {
      color: var(--color-navy);
    }

    .segment-icon {
      font-size: 1.8rem;
      margin-bottom: var(--spacing-sm);
      color: var(--color-secondary);
    }

    .segment-card.active .segment-icon {
      color: var(--color-primary);
    }

    .segment-card h3 {
      color: white;
      font-size: 1.25rem;
      margin-bottom: var(--spacing-xs);
    }

    .segment-card p {
      color: rgba(255, 255, 255, 0.7);
      font-size: 0.9rem;
      margin: 0;
    }

    @media (max-width: 992px) {
      .hero-container {
        grid-template-columns: 1fr;
        text-align: center;
      }
      .hero-actions, .hero-trust {
        justify-content: center;
      }
      .hero-content h1 {
        font-size: 2.5rem;
      }
      .hero-segments {
        max-width: 520px;
        margin: 0 auto;
      }
    }

    @media (max-width: 600px) {
      .hero-wrapper {
        min-height: 0;
        padding: var(--spacing-xl) 0;
      }
      .hero-content h1 {
        font-size: 2.1rem;
      }
      .hero-segments {
        grid-template-columns: 1fr 1fr;
        gap: var(--spacing-sm);
        margin-top: var(--spacing-lg);
      }
      .segment-card {
        padding: var(--spacing-md);
      }
      .hero-trust {
        gap: var(--spacing-md);
        justify-content: center;
      }
    }
  `]
})
export class HeroSection {
  @Input() title: string = '';
  @Input() subtitle: string = '';
}
