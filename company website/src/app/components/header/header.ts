import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth/auth.service';

@Component({
  selector: 'app-header',
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header implements OnInit, OnDestroy {
  private authService = inject(AuthService);

  menuOpen = false;
  activeDropdown: string | null = null;

  isAuthenticated = this.authService.isAuthenticated;

  ngOnInit() {
    this.onResize();
    window.addEventListener('resize', this.onResize);
  }

  ngOnDestroy() {
    window.removeEventListener('resize', this.onResize);
    this.setBodyLock(false);
  }

  onResize = () => {
    if (window.innerWidth > 920) {
      this.closeMenu();
    }
  };

  toggleMenu() {
    this.menuOpen = !this.menuOpen;
    this.activeDropdown = null;
    this.setBodyLock(this.menuOpen);
  }

  toggleDropdown(id: string) {
    // Desktop dropdowns open on hover; the tap/click toggle is for the mobile drawer only.
    if (typeof window !== 'undefined' && window.innerWidth > 920) {
      this.activeDropdown = null;
      return;
    }
    this.activeDropdown = this.activeDropdown === id ? null : id;
  }

  closeMenu() {
    this.menuOpen = false;
    this.activeDropdown = null;
    this.setBodyLock(false);
  }

  private setBodyLock(locked: boolean) {
    document.body.style.overflow = locked ? 'hidden' : '';
  }
}
