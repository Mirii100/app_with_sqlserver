import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface SecurityItem {
  icon: string;
  title: string;
  desc: string;
}

@Component({
  selector: 'app-security',
  imports: [CommonModule, RouterLink],
  templateUrl: './security.html',
  styleUrl: './security.scss',
})
export class Security {
  protections: SecurityItem[] = [
    {
      icon: 'fa-solid fa-key',
      title: 'Two-factor authentication',
      desc: 'Every login and sensitive transaction requires an additional verification step — OTP, biometrics or both.',
    },
    {
      icon: 'fa-solid fa-lock',
      title: 'Banking-grade encryption',
      desc: 'All data is protected with 256-bit SSL encryption, both in transit and at rest.',
    },
    {
      icon: 'fa-solid fa-eye',
      title: '24/7 fraud monitoring',
      desc: 'Our systems continuously watch for suspicious activity and block fraudulent transactions in real time.',
    },
    {
      icon: 'fa-solid fa-id-card',
      title: 'Strict identity verification',
      desc: 'Every account is verified against national records to prevent impersonation and money laundering.',
    },
    {
      icon: 'fa-solid fa-shield-halved',
      title: 'KDIC deposit protection',
      desc: 'Your deposits are protected up to KSh 500,000 by the Kenya Deposit Insurance Corporation.',
    },
    {
      icon: 'fa-solid fa-user-shield',
      title: 'Dedicated security team',
      desc: 'A specialist team responds to threats, investigates reports and keeps our systems ahead of attackers.',
    },
  ];

  tips = [
    'Never share your PIN, password or OTP with anyone — even our staff.',
    'Only download the Alexia-Pesa app from official app stores.',
    'Verify the URL before entering credentials: always alexiafinancials.com.',
    'Avoid logging into your account on shared or public Wi-Fi networks.',
    'Report lost phones and stolen cards immediately to block your accounts.',
    'Be wary of unsolicited calls claiming to be from the bank — we never ask for OTPs.',
  ];
}
