import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface LoanProduct {
  icon: string;
  name: string;
  description: string;
  rate: string;
  amount: string;
  tenure: string;
  features: string[];
  featured?: boolean;
}

@Component({
  selector: 'app-loans',
  imports: [CommonModule, RouterLink],
  templateUrl: './loans.html',
  styleUrl: './loans.scss',
})
export class Loans {
  loans: LoanProduct[] = [
    {
      icon: 'fa-solid fa-wallet',
      name: 'Salary Advance',
      description: 'Access a portion of your salary before payday. Repay automatically on your salary date.',
      rate: '10% p.a.',
      amount: 'Up to KSh 100,000',
      tenure: 'Up to 30 days',
      features: ['Instant approval', 'Automatic repayment', 'No collateral required'],
    },
    {
      icon: 'fa-solid fa-sack-dollar',
      name: 'Personal Loan',
      description: 'Flexible financing for school fees, medical bills, weddings and more.',
      rate: '13.5% p.a.',
      amount: 'Up to KSh 3,000,000',
      tenure: 'Up to 36 months',
      features: ['Rates as low as 13.5% p.a.', 'Fast 48-hour disbursement', 'Flexible repayment options'],
      featured: true,
    },
    {
      icon: 'fa-solid fa-people-group',
      name: 'Chama Group Loan',
      description: 'Borrow as a group and grow together with shared responsibility.',
      rate: '12.5% p.a.',
      amount: 'Up to 3x group savings',
      tenure: 'Up to 24 months',
      features: ['Group guarantee structure', 'Competitive group rates', 'Joint financial coaching'],
    },
    {
      icon: 'fa-solid fa-building',
      name: 'Business Loan',
      description: 'Working capital and expansion financing to scale your enterprise.',
      rate: '14% p.a.',
      amount: 'Up to KSh 10,000,000',
      tenure: 'Up to 48 months',
      features: ['Tailored business assessment', 'Grace period available', 'Dedicated relationship manager'],
    },
    {
      icon: 'fa-solid fa-truck',
      name: 'Asset Finance',
      description: 'Finance vehicles, machinery and equipment with flexible terms.',
      rate: '13% p.a.',
      amount: 'Up to 90% of asset value',
      tenure: 'Up to 60 months',
      features: ['Finance up to 90%', 'Asset insurance included', 'Quick asset inspection'],
    },
    {
      icon: 'fa-solid fa-house-chimney',
      name: 'Mortgage',
      description: 'Make home ownership a reality with long-term property financing.',
      rate: '12.5% p.a.',
      amount: 'Up to 90% of property value',
      tenure: 'Up to 20 years',
      features: ['Land & building finance', 'Construction & completion', 'Re-financing available'],
    },
  ];

  eligibility = [
    'Active Alexia Financials member for at least 3 months',
    'Regular deposits in the last 3 statements',
    'Valid national ID or passport',
    'Proof of income (payslip, business records or diaspora remittances)',
    'Savings equal to at least 10% of requested loan',
  ];

  steps = [
    {
      title: 'Apply',
      desc: 'Submit your application online, via the app, or at any branch with the required documents.',
    },
    {
      title: 'Assessment',
      desc: 'Our credit team reviews your history and eligibility — most decisions are made within 24–48 hours.',
    },
    {
      title: 'Approval & signing',
      desc: 'Review your offer, sign the agreement digitally, and select your preferred repayment plan.',
    },
    {
      title: 'Disbursement',
      desc: 'Funds are sent to your account or M-Pesa immediately after approval.',
    },
  ];
}
