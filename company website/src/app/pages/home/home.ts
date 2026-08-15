import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { HeroSection } from '../../components/hero-section/hero-section';

interface FaqItem {
  question: string;
  answer: string;
  open: boolean;
}

@Component({
  selector: 'app-home',
  imports: [CommonModule, FormsModule, RouterLink, HeroSection],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home {
  // Loan Calculator State
  loanAmount: number = 500000;
  loanTerm: number = 12;
  interestRate: number = 13.5;
  monthlyRepayment: number = 0;

  // Currency Converter State
  amountToConvert: number = 1;
  baseCurrency: string = 'USD';
  targetCurrency: string = 'KES';
  convertedAmount: number = 0;

  exchangeRates: { [key: string]: number } = {
    'USD': 129.50,
    'GBP': 165.20,
    'EUR': 140.80,
    'UGX': 0.035,
    'TZS': 0.052,
    'KES': 1.00,
  };

  // Home page data
  testimonials = [
    {
      name: 'Wanjiru M.',
      role: 'Chama Chairlady, Nakuru',
      quote: 'Managing our group savings and loans has never been easier. The chama dashboard is intuitive and our returns have grown steadily.',
    },
    {
      name: 'Brian Otieno',
      role: 'Small Business Owner, Kisumu',
      quote: 'I financed my shop expansion through Alexia in just three days. The relationship managers genuinely care about your growth.',
    },
    {
      name: 'Esther Kamau',
      role: 'Diaspora Member, UK',
      quote: 'Opening a diaspora account was seamless. I send money home instantly and my family can access it at competitive rates.',
    },
  ];

  faqs: FaqItem[] = [
    {
      question: 'How do I open an account?',
      answer: 'Open an account in minutes online or visit any of our branches. You will need a valid national ID or passport, a passport-size photo, and a phone number. You can start the process on this website or via the Alexia-Pesa app.',
      open: true,
    },
    {
      question: 'What are your loan requirements?',
      answer: 'You need to be an account holder for at least 3 months with regular deposits, provide a valid ID, proof of income, and meet the minimum savings threshold. Loan limits grow with your savings and repayment history.',
      open: false,
    },
    {
      question: 'Can I bank with you from abroad?',
      answer: 'Yes. Our diaspora banking package lets you open and manage accounts remotely, save in multiple currencies, and send money home at competitive rates through the Alexia-Pesa app.',
      open: false,
    },
    {
      question: 'How secure is my money?',
      answer: 'Deposits are protected up to KSh 500,000 by the Kenya Deposit Insurance Corporation (KDIC). We use banking-grade encryption, two-factor authentication, and 24/7 fraud monitoring to safeguard every transaction.',
      open: false,
    },
  ];

  constructor() {
    this.calculateLoan();
    this.convertCurrency();
  }

  calculateLoan() {
    const monthlyRate = (this.interestRate / 100) / 12;
    const numerator = monthlyRate * Math.pow(1 + monthlyRate, this.loanTerm);
    const denominator = Math.pow(1 + monthlyRate, this.loanTerm) - 1;
    this.monthlyRepayment = this.loanAmount * (numerator / denominator);
  }

  convertCurrency() {
    const amountInKes = this.amountToConvert * this.exchangeRates[this.baseCurrency];
    this.convertedAmount = amountInKes / this.exchangeRates[this.targetCurrency];
  }

  get currencies() {
    return Object.keys(this.exchangeRates);
  }

  toggleFaq(index: number) {
    this.faqs[index].open = !this.faqs[index].open;
  }
}
