import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-digital-banking',
  imports: [CommonModule, RouterLink],
  templateUrl: './digital-banking.html',
  styleUrl: './digital-banking.scss',
})
export class DigitalBanking {
  channels = [
    {
      icon: 'fa-solid fa-mobile-screen-button',
      name: 'Alexia-Pesa App',
      desc: 'Send money, pay bills, save, trade crypto and manage cards from one beautifully simple app.',
      tag: 'iOS & Android',
    },
    {
      icon: 'fa-solid fa-qrcode',
      name: 'QR Payments',
      desc: 'Scan, pay and get paid instantly at shops, events or between friends — no till numbers to memorise.',
      tag: 'Live in app',
    },
    {
      icon: 'fa-solid fa-money-check',
      name: 'Digital Cheques',
      desc: 'Issue a cheque to anyone in seconds and let them deposit it straight from their phone.',
      tag: 'New',
    },
    {
      icon: 'fa-solid fa-money-bill-transfer',
      name: 'Cardless ATM Withdrawals',
      desc: 'Withdraw cash at any Alexia ATM with a secure one-time QR code — no card required.',
      tag: 'New',
    },
    {
      icon: 'fa-solid fa-globe',
      name: 'Internet Banking',
      desc: 'Full account control from your browser — statements, beneficiaries, limits and more.',
      tag: 'Web',
    },
    {
      icon: 'fa-solid fa-store',
      name: 'Agents & Branches',
      desc: 'Deposit or withdraw cash at 1,200+ branches and agent points across all 47 counties.',
      tag: 'Nationwide',
    },
  ];

  steps = [
    { num: '1', title: 'Open your account', text: 'Sign up online in under 5 minutes with just your ID.' },
    { num: '2', title: 'Download Alexia-Pesa', text: 'Log in with your member credentials and set your PIN.' },
    { num: '3', title: 'Bank anywhere', text: 'Pay, save, invest and withdraw — all from your phone.' },
  ];
}
