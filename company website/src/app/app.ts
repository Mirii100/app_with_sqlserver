import { Component, inject, OnInit } from '@angular/core';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { Header } from './components/header/header';
import { Footer } from './components/footer/footer';

const PAGE_TITLES: Record<string, string> = {
  '': 'Alexia Financials | Banking & Sacco Solutions in Kenya',
  'about': 'Our Story | Alexia Financials',
  'services': 'Banking & Services | Alexia Financials',
  'loans': 'Loans & Credit | Alexia Financials',
  'rates': 'Rates & Fees | Alexia Financials',
  'security': 'Security Center | Alexia Financials',
  'careers': 'Careers | Alexia Financials',
  'branches': 'Branches & Agents | Alexia Financials',
  'faq': 'Frequently Asked Questions | Alexia Financials',
  'news': 'News & Insights | Alexia Financials',
  'contact': 'Get in Touch | Alexia Financials',
  'signup': 'Open an Account | Alexia Financials',
  'login': 'Member Login | Alexia Financials',
  'account': 'My Account | Alexia Financials',
};

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Header, Footer],
  templateUrl: './app.html',
})
export class App implements OnInit {
  title = 'Alexia Financials';

  private router = inject(Router);
  private titleService = inject(Title);

  ngOnInit() {
    this.router.events.subscribe((event) => {
      if (event instanceof NavigationEnd) {
        const key = event.urlAfterRedirects.split('?')[0].replace(/^\//, '');
        this.titleService.setTitle(PAGE_TITLES[key] ?? PAGE_TITLES['']);
        window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
      }
    });
  }
}
