import { Component, OnInit, inject } from '@angular/core';
import { ApiService } from '../../services/api';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface ServiceCategory {
  id: string;
  name: string;
  icon: string;
  description: string;
  features: string[];
  details: { name: string; desc: string }[];
}

@Component({
  selector: 'app-services',
  imports: [CommonModule, RouterLink],
  templateUrl: './services.html',
  styleUrl: './services.scss',
})
export class Services implements OnInit {
  private apiService = inject(ApiService);

  categories: ServiceCategory[] = [
    {
      id: 'personal',
      name: 'Personal Banking',
      icon: 'fa-solid fa-user',
      description: 'Flexible solutions for your everyday financial needs.',
      features: ['Salary Accounts', 'Savings Plans', 'Personal Loans', 'Debit Cards', 'Goal Savings', 'Insurance Cover'],
      details: [
        { name: 'Everyday Savings', desc: 'No ledger fees, competitive interest and free mobile transfers.' },
        { name: 'Fixed Deposits', desc: 'Lock higher rates from 11.5% p.a. with flexible tenures.' },
        { name: 'Personal Loans', desc: 'Up to KSh 3,000,000 approved within 48 hours.' },
        { name: 'Salary Advance', desc: 'Access up to KSh 100,000 before payday — instant and automatic.' },
      ],
    },
    {
      id: 'business',
      name: 'Business Banking',
      icon: 'fa-solid fa-briefcase',
      description: 'Scaling your enterprise with specialized financing.',
      features: ['Working Capital', 'Asset Finance', 'Trade Finance', 'Business Current Account', 'SME Advisory', 'Payroll Services'],
      details: [
        { name: 'Working Capital', desc: 'Short-term credit to smooth cash flow and seize opportunities.' },
        { name: 'Asset Finance', desc: 'Vehicles and equipment financed up to 90% with insurance included.' },
        { name: 'Trade Finance', desc: 'Letters of credit, guarantees and invoice discounting.' },
        { name: 'Business Accounts', desc: 'Multi-signatory accounts with a dedicated relationship manager.' },
      ],
    },
    {
      id: 'chama',
      name: 'Chama Solutions',
      icon: 'fa-solid fa-people-group',
      description: 'Group investment accounts with competitive returns.',
      features: ['Group Savings', 'Chama Loans', 'Investment Advisory', 'Financial Literacy', 'Group Goal Tracking', 'Digital Group Tools'],
      details: [
        { name: 'Collective Accounts', desc: 'Grow your group savings with up to 12% p.a. interest.' },
        { name: 'Group Loans', desc: 'Borrow up to 3x group savings at preferential rates.' },
        { name: 'Digital Chama', desc: 'Mobile and USSD tools to track contributions and meetings.' },
        { name: 'Literacy & Coaching', desc: 'Workshops on investing, budgeting and growing as a group.' },
      ],
    },
    {
      id: 'diaspora',
      name: 'Diaspora Banking',
      icon: 'fa-solid fa-earth-africa',
      description: 'Banking beyond borders for Kenyans abroad.',
      features: ['Remote Account Opening', 'Multi-currency Accounts', 'Home Loans', 'Investment Management', 'Remittance Services', 'Video Verification'],
      details: [
        { name: 'Open from anywhere', desc: 'Start an account online with video verification, no travel needed.' },
        { name: 'Remittances', desc: 'Send money home with a flat 1.5% fee — credited in minutes.' },
        { name: 'Home & Asset Loans', desc: 'Financing for property and assets back home from abroad.' },
        { name: 'Family Management', desc: 'Joint accounts and cards for family members in Kenya.' },
      ],
    },
  ];

  activeCategoryId: string = 'personal';
  services: any[] = [];
  loading = true;

  ngOnInit() {
    this.apiService.getServices().subscribe({
      next: (data) => {
        this.services = data;
        this.loading = false;
      },
      error: (err) => {
        console.warn('Backend API unavailable, using professional fallback data.', err);
        this.loading = false;
      }
    });
  }

  get activeCategory() {
    return this.categories.find(c => c.id === this.activeCategoryId);
  }

  setActiveCategory(id: string) {
    this.activeCategoryId = id;
  }
}
