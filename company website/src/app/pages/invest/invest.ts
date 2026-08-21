import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-invest',
  imports: [CommonModule, RouterLink],
  templateUrl: './invest.html',
  styleUrl: './invest.scss',
})
export class Invest {
  products = [
    {
      icon: 'fa-solid fa-vault',
      name: 'Fixed Deposits',
      desc: 'Lock away funds from 3 to 36 months and earn up to 12.5% p.a. with interest paid monthly or at maturity.',
    },
    {
      icon: 'fa-solid fa-chart-pie',
      name: 'Unit Trusts & Money Market',
      desc: 'Professionally managed low-risk funds starting from KSh 5,000 — ideal for growing your emergency buffer.',
    },
    {
      icon: 'fa-solid fa-bitcoin-sign',
      name: 'Shares & Crypto Desk',
      desc: 'Trade NSE listed shares and top cryptocurrencies directly from your Alexia wallet with live KES pricing.',
    },
    {
      icon: 'fa-solid fa-umbrella-beach',
      name: 'Retirement Plans',
      desc: 'Flexible pension savings with tax relief benefits so you keep living well long after your last payslip.',
    },
    {
      icon: 'fa-solid fa-earth-africa',
      name: 'Diaspora Investments',
      desc: 'Invest back home remotely — real estate co-ownership, fixed deposits and chama units managed for you.',
    },
    {
      icon: 'fa-solid fa-children',
      name: 'Junior Saver Plans',
      desc: 'Build an education fund for your children with automated monthly top-ups and bonus interest on milestones.',
    },
  ];

  highlights = [
    { value: '12.5%', label: 'Top fixed deposit rate p.a.' },
    { value: 'KSh 5,000', label: 'Minimum investment' },
    { value: 'Daily', label: 'Money market accrual' },
    { value: '0 fees', label: 'On deposits opened online' },
  ];
}
